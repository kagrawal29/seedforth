#!/usr/bin/env python3
"""Read-only SeedForth repository reconciler.

Reports the repositories declared in registry/repositories.json and their
local Git state. It never fetches, checks out, writes, or changes remotes.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "repositories.json"


def classify_runtime(declared_sha: str, observed_sha: str,
                     process_status: str | None = None,
                     graph_status: str | None = None) -> str:
    """Classify an observed deployment without mutating any authority."""
    if not declared_sha or not observed_sha:
        return "unknown"
    if not (observed_sha == declared_sha
            or observed_sha.startswith(declared_sha)
            or declared_sha.startswith(observed_sha)):
        return "drifted"
    if process_status is not None and graph_status is not None:
        process_running = process_status in {"running", "ready", "active"}
        graph_active = graph_status in {"running", "ready", "active"}
        if process_running != graph_active:
            return "conflicting"
    return "healthy"


def run(command: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True,
                              timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return proc.returncode, (proc.stdout or proc.stderr).strip()


def clean_remote(value: str) -> str:
    return re.sub(r"//[^/@]+@", "//", value)


def inspect_repo(path_text: str, canonical_branch: str | None = None) -> dict[str, object]:
    path = ROOT / path_text
    result: dict[str, object] = {"path": path_text, "exists": path.exists()}
    if not path.exists():
        return result
    commands = {
        "root": ["git", "rev-parse", "--show-toplevel"],
        "branch": ["git", "symbolic-ref", "--short", "-q", "HEAD"],
        "sha": ["git", "rev-parse", "HEAD"],
        "upstream": ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        "status": ["git", "status", "--porcelain=v1"],
        "origin": ["git", "remote", "get-url", "origin"],
    }
    for key, command in commands.items():
        code, output = run(command, cwd=path)
        if key == "status":
            result["dirty_files"] = len(output.splitlines()) if code == 0 and output else 0
        elif key == "origin":
            result[key] = clean_remote(output) if code == 0 else None
        else:
            result[key] = output if code == 0 else None
    if canonical_branch:
        code, output = run(
            ["git", "ls-remote", "origin", f"refs/heads/{canonical_branch}"],
            cwd=path,
        )
        if code == 0 and output:
            result["github_sha"] = output.split()[0]
            result["github_branch"] = canonical_branch
            result["local_matches_github"] = result.get("sha") == result["github_sha"]
        else:
            result["github_sha"] = None
            result["github_branch"] = canonical_branch
            result["local_matches_github"] = None
    return result


def inspect_server(host: str, paths: list[str]) -> dict[str, object]:
    """Inspect server checkouts without changing Git configuration."""
    remote_script = (
        "for d in " + shlex.join(paths) + "; do "
        "if [ -e \"$d/.git\" ]; then "
        "b=$(git --git-dir=\"$d/.git\" --work-tree=\"$d\" symbolic-ref --short -q HEAD 2>/dev/null || echo detached); "
        "s=$(git --git-dir=\"$d/.git\" --work-tree=\"$d\" rev-parse HEAD 2>/dev/null || echo unknown); "
        "n=$(git --git-dir=\"$d/.git\" --work-tree=\"$d\" status --porcelain=v1 2>/dev/null | wc -l | tr -d ' '); "
        "printf '%s\\t%s\\t%s\\t%s\\n' \"$d\" \"$b\" \"$s\" \"$n\"; "
        "else printf '%s\\tmissing\\t\\t\\n' \"$d\"; fi; done"
    )
    command = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host,
               remote_script]
    try:
        proc = subprocess.run(command, text=True, capture_output=True,
                              timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": str(exc)}
    if proc.returncode != 0:
        return {"error": (proc.stderr or proc.stdout).strip()}
    records = []
    for line in proc.stdout.splitlines():
        path, branch, sha, dirty = (line.split("\t") + ["", "", "", ""])[:4]
        records.append({"path": path, "branch": branch, "sha": sha,
                        "dirty_files": int(dirty or 0)})
    return {"host": host, "repositories": records}


def inspect_graph(host: str) -> dict[str, object]:
    """Collect graph health through the shared HTTP helper without exposing credentials."""
    remote = r'''set -eu
set -a
. /opt/seedforth/shared/env/seedforth.env
set +a
cd /opt/seedforth/current/platform/delta
python3 - <<'PY'
from tools.neo4j_helper import scalar

facts = {
    "nodes": "MATCH (n) RETURN count(n)",
    "relationships": "MATCH ()-[r]->() RETURN count(r)",
    "protocols_enabled": "MATCH (p:Protocol {enabled:true}) RETURN count(p)",
    "active_agents": "MATCH (s:SubAgent {status:'active'}) RETURN count(s)",
    "pending_decisions": "MATCH (d:DecisionRequest {status:'pending'}) RETURN count(d)",
    "latest_protocol_run": "MATCH (r:ProtocolRun) RETURN max(r.timestamp)",
}
for key, cypher in facts.items():
    print(f"{key}\t{scalar(cypher, default='unknown')}")
PY'''
    command = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, remote]
    try:
        proc = subprocess.run(command, text=True, capture_output=True,
                              timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": str(exc)}
    if proc.returncode != 0:
        return {"error": (proc.stderr or proc.stdout).strip()}
    facts = {}
    for line in proc.stdout.splitlines():
        if "\t" in line:
            key, value = line.split("\t", 1)
            facts[key] = value.strip()
    return {"host": host, "facts": facts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--server", help="also inspect declared server paths via SSH")
    parser.add_argument("--graph", help="also inspect live Neo4j facts through a server")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    repos = manifest.get("repositories", [])
    live = manifest.get("live_deployment", {})
    report = {
        "manifest": str(args.manifest),
        "mode": "read-only",
        "repositories": [
            {
                **entry,
                **({"status": "active", "deployment_release": live["release"]}
                   if live.get("status") == "active"
                   and entry.get("role") == "platform"
                   else {}),
                "local": inspect_repo(entry["local_path"], entry.get("canonical_branch")),
            }
            for entry in repos
        ],
    }
    if args.server:
        paths = [entry["observed_server_path"] for entry in repos
                 if entry.get("observed_server_path")]
        # Legacy paths are observations too, but remain separate from the
        # canonical release path so each is inspected as its own checkout.
        paths.extend(entry["legacy_server_path"] for entry in repos
                     if entry.get("legacy_server_path"))
        paths = list(dict.fromkeys(paths))
        report["server"] = inspect_server(args.server, paths)
        declared_release = live.get("release", "")
        for record in report["server"].get("repositories", []):
            if record.get("path") == live.get("server_path", "/opt/seedforth/current"):
                record["state"] = classify_runtime(declared_release, record.get("sha", ""))
    if args.graph:
        report["graph"] = inspect_graph(args.graph)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
