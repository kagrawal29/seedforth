#!/usr/bin/env python3
"""Progress markers — detect REAL work and write ProgressEvent nodes.

Scores signals (commits, outbox responses, artifacts, deployments) and writes
weighted :ProgressEvent nodes. A project is "producing" only when it
accumulates >= 1.0 weight per stall-window from real markers.

Marker weights (from master-spec Part 5):
  Real commit (classified, not "auto:")    1.0
  Deployment URL returns 200              1.2
  Outbox with artifact attached           0.8
  Outbox embed with "Shipped" + numbers   0.7
  New artifact file (non-config)          0.4
  Auto-commit / empty ack                 0.0

Usage: python3 progress-markers.py [--all | --project <name>]
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from neo4j_helper import q, ql

REGISTRY_PATH = "/opt/delta/delta-registry.json"

# "Real work" commit prefixes vs noise
REAL_PREFIX = re.compile(r'^(feat|fix|build|design|learn|memory|report|deploy|docs|refactor)[:\-]', re.I)
NOISE_PREFIX = re.compile(r'^(auto|sync|ci|chore|wip|update|minor)\s*[:\-]?', re.I)


def classify_commit(message):
    """Return (is_real, weight)."""
    msg = (message or "").strip()
    if NOISE_PREFIX.match(msg) or len(msg) < 15:
        return False, 0.0
    if REAL_PREFIX.match(msg) and len(msg) > 25:
        return True, 1.0
    # Ambiguous — mark for review, low weight
    return True, 0.3


def scan_commits(project_name, project_dir, since_epoch=None):
    """Scan recent git commits, return list of real progress signals."""
    signals = []
    git_dir = Path(project_dir) / ".git"
    if not git_dir.exists():
        return signals

    # Get last 50 commits
    r = subprocess.run(
        ["git", "-C", project_dir, "log", "--format=%H|%s|%ct", "-50"],
        capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        return signals

    for line in r.stdout.strip().split("\n"):
        if not line or "|" not in line:
            continue
        sha, msg, ct = line.split("|", 2)
        ct = int(ct)
        if since_epoch and ct < since_epoch:
            continue
        is_real, weight = classify_commit(msg)
        signals.append({
            "marker": "commit", "sha": sha, "message": msg,
            "weight": weight, "is_real": is_real, "timestamp": ct,
        })
    return signals


def scan_outbox(project_name, project_dir, since_epoch=None):
    """Scan outbox responses for substance (artifacts, numbers, length)."""
    signals = []
    outbox = Path(project_dir) / "delta-config" / "outbox"
    if not outbox.exists():
        return signals

    for f in sorted(outbox.glob("*.json"))[-30:]:
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        text = data.get("text", "") or ""
        mtime = f.stat().st_mtime
        if since_epoch and mtime < since_epoch:
            continue

        # Substance heuristics
        has_file = bool(data.get("file") or data.get("files"))
        has_embed = "embed" in data
        has_numbers = bool(re.search(r'\d{2,}', text))
        length = len(text)

        if has_file:
            weight = 0.8
        elif has_embed and has_numbers:
            weight = 0.7
        elif length > 80 and has_numbers:
            weight = 0.5
        else:
            weight = 0.0
        signals.append({
            "marker": "outbox", "msg_id": data.get("id", f.name),
            "weight": weight, "is_real": weight > 0, "timestamp": mtime,
        })
    return signals


def scan_artifacts(project_name, project_dir, since_epoch=None):
    """Detect non-config artifact files modified recently."""
    signals = []
    project = Path(project_dir)
    if not project.exists():
        return signals
    # Check for recent file changes outside config dirs
    for root, dirs, files in os.walk(project):
        rel = Path(root).relative_to(project)
        # Skip config/system dirs
        parts = str(rel)
        if any(x in parts for x in [".git", "delta-config", ".opencode", "node_modules", ".vercel", "memory"]):
            dirs[:] = []
            continue
        for f in files:
            if f.endswith((".py", ".js", ".ts", ".html", ".md", ".json", ".csv")):
                fpath = Path(root) / f
                mtime = fpath.stat().st_mtime
                if since_epoch and mtime < since_epoch:
                    continue
                if time.time() - mtime < 48 * 3600:  # modified in last 48h
                    signals.append({
                        "marker": "artifact", "path": str(rel / f),
                        "weight": 0.4, "is_real": True, "timestamp": mtime,
                    })
                    break  # one artifact per dir scan pass
    return signals


def write_progress_event(entity, signal):
    """Write a ProgressEvent node."""
    node_id = f"pe-{entity}-{signal['marker']}-{int(signal['timestamp'])}"
    q(
        "MERGE (pe:ProgressEvent {node_id:$nid}) "
        "SET pe.entity=$ent, pe.marker=$marker, pe.evidence=$evidence, "
        "pe.weight=$weight, pe.created_at=datetime({epochMillis:$ts}), "
        "pe.project=$ent",
        {
            "nid": node_id, "ent": entity,
            "marker": signal["marker"],
            "evidence": signal.get("message") or signal.get("path") or signal.get("msg_id", ""),
            "weight": signal["weight"], "ts": int(signal["timestamp"]) * 1000,
        },
    )


def process_project(name, project_dir, since_epoch):
    """Score all signals for a project, write ProgressEvents, report."""
    all_signals = []
    all_signals += scan_commits(name, project_dir, since_epoch)
    all_signals += scan_outbox(name, project_dir, since_epoch)
    all_signals += scan_artifacts(name, project_dir, since_epoch)

    total_weight = sum(s["weight"] for s in all_signals)
    real_signals = [s for s in all_signals if s["is_real"]]

    for s in all_signals:
        if s["weight"] > 0:
            write_progress_event(name, s)

    return {
        "project": name,
        "signals": len(all_signals),
        "real": len(real_signals),
        "total_weight": round(total_weight, 1),
        "producing": total_weight >= 1.0,
    }


def main():
    args = sys.argv[1:]
    since_epoch = time.time() - 7 * 24 * 3600  # last 7 days default

    registry = json.load(open(REGISTRY_PATH))
    projects = registry.get("projects", {})

    results = []
    if "--all" in args or not args:
        targets = projects.items()
    else:
        # explicit project names after --project or bare
        names = [a for a in args if not a.startswith("--")]
        targets = [(n, p) for n, p in projects.items() if n in names]

    print(f"=== PROGRESS MARKERS (last 7 days) ===")
    for name, proj in sorted(targets):
        project_dir = proj.get("project_dir", f"/home/proj-{name}/{name}")
        res = process_project(name, project_dir, since_epoch)
        results.append(res)
        status = "PRODUCING" if res["producing"] else "STALLED"
        print(f"  {name}: {res['signals']} signals, {res['real']} real, "
              f"weight={res['total_weight']} [{status}]")

    print("\n=== SUMMARY ===")
    producing = sum(1 for r in results if r["producing"])
    print(f"  {producing}/{len(results)} projects producing real progress")


if __name__ == "__main__":
    main()
