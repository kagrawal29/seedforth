#!/usr/bin/env python3
"""
Distribute — the exhale. Validates and pushes to team repos.

Plain Python script (no Agent SDK needed — no AI).
Runs lint, rebuilds indexes, pushes knowledge + rules + per-person context.
The team breathes in what the system exhales.
Cost: $0.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run(cmd, label):
    """Run a command, return success bool."""
    print(f"  [{label}] Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)
    if result.returncode != 0:
        print(f"  [{label}] FAILED: {result.stderr[:200]}")
        return False
    if result.stdout.strip():
        print(f"  [{label}] {result.stdout.strip()[:200]}")
    return True


def main():
    print(f"[distribute] Starting at {datetime.now().isoformat()}")

    # Step 1: Lint
    if not run("python3 scripts/lint-knowledge.py", "lint"):
        print("  [distribute] Lint failed — aborting distribution")
        sys.exit(1)

    # Step 2: Rebuild search indexes (lint already does this, but be explicit)
    run("python3 scripts/build-search-index.py", "index")

    # Step 2.5: Regenerate community map from live FalkorDB (non-fatal)
    script = ROOT / "scripts" / "generate-community-map-live.py"
    if script.exists():
        if not run(f"python3 {script}", "community-map"):
            print("  [distribute] Community map regeneration failed — using existing static map")
    else:
        print("  [distribute] generate-community-map-live.py not found — using existing static community-map.md")

    # Step 3: Push knowledge to team repos
    run("bash scripts/push-knowledge.sh", "push-knowledge")

    # Step 4: Push rules to team repos
    run("bash scripts/push-to-all-branches.sh", "push-rules")

    # Step 5: Push per-person context (if demand data exists)
    demand_dir = ROOT / "signals" / "demand"
    if demand_dir.exists() and list(demand_dir.glob("*-demand.json")):
        # Generate per-person context from demand profiles + graph
        run("python3 agents/run-context.py", "context-gen")
        # Push to team branches
        run("bash scripts/push-person-context.sh", "push-context")
    else:
        print("  [distribute] No demand data yet — skipping per-person context")

    # Step 6: Log to cycle-log.md
    date = datetime.now().strftime("%Y-%m-%d")
    log_path = ROOT / "knowledge" / "meta" / "cycle-log.md"
    if log_path.exists():
        with open(log_path, "a") as f:
            f.write(f"| {date} | auto | auto-ingest | auto-synthesis | auto-distribute | Automated cycle |\n")

    # Step 6: Git commit
    run("git add knowledge/ distribution/ .claude/", "stage")
    run(f'git commit -m "auto-distribute: {date}" --allow-empty', "commit")

    print(f"[distribute] Complete.")


if __name__ == "__main__":
    main()
