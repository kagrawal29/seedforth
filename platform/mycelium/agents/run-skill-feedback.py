#!/usr/bin/env python3
"""
Skill Feedback Orchestrator.

SKILL FEEDBACK (gate 3) → HEIMDALL (gate 1) → PRE-DIST AUDIT (gate 2) → DISTRIBUTE

Runs every 2 days. Checks last run timestamp before executing.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
LOCKFILE = ROOT / "knowledge" / "meta" / ".skill-feedback-lock"
STATE_FILE = ROOT / "knowledge" / "meta" / ".skill-feedback-state.json"
MAX_LOCK_AGE_MINUTES = 90
INTERVAL_DAYS = 2


def should_run():
    """Check if enough time has passed since last skill feedback run."""
    if not STATE_FILE.exists():
        return True
    try:
        state = json.loads(STATE_FILE.read_text())
        last_run = datetime.fromisoformat(state["last_run"])
        elapsed = datetime.now(timezone.utc) - last_run
        if elapsed < timedelta(days=INTERVAL_DAYS):
            hours_left = (timedelta(days=INTERVAL_DAYS) - elapsed).total_seconds() / 3600
            print(f"[skill-feedback] Last run {elapsed.total_seconds()/3600:.0f}h ago. Next in {hours_left:.0f}h. Skipping.")
            return False
        return True
    except Exception:
        return True


def acquire_lock():
    if LOCKFILE.exists():
        try:
            lock_data = json.loads(LOCKFILE.read_text())
            lock_time = datetime.fromisoformat(lock_data["ts"])
            age = (datetime.now(timezone.utc) - lock_time).total_seconds() / 60
            if age < MAX_LOCK_AGE_MINUTES:
                print(f"[skill-feedback] Lock held ({age:.0f}m ago). Skipping.")
                return False
            print(f"[skill-feedback] Breaking stale lock ({age:.0f}m old).")
        except Exception:
            pass
    LOCKFILE.write_text(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "pid": os.getpid()}))
    return True


def release_lock():
    try:
        LOCKFILE.unlink(missing_ok=True)
    except Exception:
        pass


def update_state():
    """Record successful run timestamp."""
    STATE_FILE.write_text(json.dumps({"last_run": datetime.now(timezone.utc).isoformat()}))


def run_agent(script, label, timeout_seconds=600):
    print(f"\n  [{label}] Running...")
    start = time.time()
    try:
        result = subprocess.run(
            ["python3", script], capture_output=True, text=True,
            cwd=ROOT, timeout=timeout_seconds,
        )
        elapsed = time.time() - start
        if result.stdout:
            for line in result.stdout.strip().split("\n")[-5:]:
                print(f"  [{label}] {line}")
        return {"agent": label, "success": result.returncode == 0, "elapsed_s": round(elapsed, 1)}
    except subprocess.TimeoutExpired:
        return {"agent": label, "success": False, "elapsed_s": round(time.time() - start, 1), "error": "timeout"}
    except Exception as e:
        return {"agent": label, "success": False, "elapsed_s": 0, "error": str(e)[:100]}


def main():
    print(f"[skill-feedback-loop] Starting at {datetime.now().isoformat()}")

    if not should_run():
        sys.exit(0)

    if not acquire_lock():
        sys.exit(0)

    try:
        results = []
        results.append(run_agent("agents/skill-feedback-agent.py", "skill-feedback", 500))
        results.append(run_agent("agents/evaluation-agent.py", "heimdall", 400))

        # Gate 2: pre-distribution audit
        audit_result = run_agent("agents/pre-dist-audit-agent.py", "pre-dist-audit", 500)
        results.append(audit_result)
        if not audit_result["success"]:
            print(f"\n[skill-feedback-loop] Gate 2 blocked distribution. Check knowledge/meta/pre-dist-audit.md")
        else:
            results.append(run_agent("agents/distribute.py", "distribute", 300))

        total = sum(r["elapsed_s"] for r in results)
        ok = sum(1 for r in results if r["success"])
        print(f"\n[skill-feedback-loop] Done: {ok}/{len(results)} ok, {total:.0f}s")
        for r in results:
            s = "✓" if r["success"] else "✗"
            print(f"  {s} {r['agent']}: {r['elapsed_s']}s")

        update_state()

    finally:
        release_lock()


if __name__ == "__main__":
    main()
