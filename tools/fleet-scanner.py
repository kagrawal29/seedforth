#!/usr/bin/env python3
"""Fleet scanner — the graph's SENSES. Pure I/O boundary.

Writes raw signal nodes to the graph. NO logic, NO scoring, NO decisions.
All reasoning happens graph-side as Cypher protocols.

Outputs per project:
  (:CommitSignal {entity, sha, message, timestamp})
  (:OutboxSignal {entity, text_preview, has_file, has_embed, has_numbers, length, timestamp})
  (:ArtifactSignal {entity, path, mtime})

The graph's progress-score protocol reads these and decides.

Usage: python3 fleet-scanner.py [--all | <project>...]
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from neo4j_helper import q

REGISTRY_PATH = "/opt/delta/delta-registry.json"
LOOKBACK_DAYS = float(os.environ.get("SCAN_LOOKBACK_DAYS", "7"))


def write_signal(label, params):
    """Write one signal node (MERGE by deterministic id)."""
    q(
        f"MERGE (s:{label} {{node_id:$nid}}) "
        f"SET s += $props, s.created_at=datetime({{epochMillis:$ts}}), s.project=$ent",
        {"nid": params.pop("_id"), "props": params, "ts": params.pop("_ts"), "ent": params["entity"]},
    )


def scan_commits(entity, project_dir, since_ts):
    git_dir = Path(project_dir) / ".git"
    if not git_dir.exists():
        return
    r = subprocess.run(["git", "-C", project_dir, "log", "--format=%H|%s|%ct", "-100"],
                       capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        return
    for line in r.stdout.strip().split("\n"):
        if "|" not in line:
            continue
        sha, msg, ct = line.split("|", 2)
        ct = int(ct)
        if ct < since_ts:
            continue
        write_signal("CommitSignal", {
            "_id": f"cs-{entity}-{sha}", "entity": entity, "sha": sha,
            "message": msg, "_ts": ct * 1000,
        })


def scan_outbox(entity, project_dir, since_ts):
    outbox = Path(project_dir) / "delta-config" / "outbox"
    if not outbox.exists():
        return
    for f in sorted(outbox.glob("*.json"))[-50:]:
        mtime = f.stat().st_mtime
        if mtime < since_ts:
            continue
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        text = data.get("text", "") or ""
        write_signal("OutboxSignal", {
            "_id": f"os-{entity}-{f.stem}", "entity": entity,
            "text_preview": text[:200],
            "has_file": bool(data.get("file") or data.get("files")),
            "has_embed": "embed" in data,
            "has_numbers": bool(re.search(r"\d{2,}", text)),
            "length": len(text),
            "_ts": int(mtime * 1000),
        })


def scan_artifacts(entity, project_dir, since_ts):
    project = Path(project_dir)
    if not project.exists():
        return
    for root, dirs, files in os.walk(project):
        rel = Path(root).relative_to(project)
        parts = str(rel)
        if any(x in parts for x in [".git", "delta-config", ".opencode", "node_modules", ".vercel", "memory"]):
            dirs[:] = []
            continue
        for f in files:
            if f.endswith((".py", ".js", ".ts", ".html", ".md", ".json", ".csv")):
                fpath = Path(root) / f
                mtime = fpath.stat().st_mtime
                if mtime < since_ts:
                    continue
                write_signal("ArtifactSignal", {
                    "_id": f"as-{entity}-{fpath.stat().st_ino}", "entity": entity,
                    "path": str(rel / f), "_ts": int(mtime * 1000),
                })
                break  # one per dir is enough


def main():
    since_ts = time.time() - LOOKBACK_DAYS * 86400
    registry = json.load(open(REGISTRY_PATH))
    projects = registry.get("projects", {})

    args = sys.argv[1:]
    if args and "--all" not in args:
        targets = [(n, p) for n, p in projects.items() if n in args]
    else:
        targets = projects.items()

    print(f"=== FLEET SCANNER ({time.strftime('%Y-%m-%d %H:%M')}) ===")
    for name, proj in sorted(targets):
        project_dir = proj.get("project_dir", f"/home/proj-{name}/{name}")
        scan_commits(name, project_dir, since_ts)
        scan_outbox(name, project_dir, since_ts)
        scan_artifacts(name, project_dir, since_ts)
        print(f"  scanned: {name}")
    print("=== COMPLETE ===")


if __name__ == "__main__":
    main()
