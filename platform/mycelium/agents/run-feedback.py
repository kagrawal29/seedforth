#!/usr/bin/env python3
"""
Feedback Loop Orchestrator.

ENTRY FEEDBACK → HEIMDALL (gate 1) → PRE-DIST AUDIT (gate 2) → DISTRIBUTE

Runs independently from the synthesis loop. Entry feedback daily (end of work day).
Skill feedback runs on its own 2-day cadence (see run-skill-feedback.py).
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
LOCKFILE = ROOT / "knowledge" / "meta" / ".feedback-lock"
CYCLE_LOG = ROOT / "knowledge" / "meta" / "cycle-log.md"
MAX_LOCK_AGE_MINUTES = 60


def acquire_lock():
    if LOCKFILE.exists():
        try:
            lock_data = json.loads(LOCKFILE.read_text())
            lock_time = datetime.fromisoformat(lock_data["ts"])
            age = (datetime.now(timezone.utc) - lock_time).total_seconds() / 60
            if age < MAX_LOCK_AGE_MINUTES:
                print(f"[feedback] Lock held ({age:.0f}m ago). Skipping.")
                return False
            print(f"[feedback] Breaking stale lock ({age:.0f}m old).")
        except Exception:
            pass
    LOCKFILE.write_text(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "pid": os.getpid()}))
    return True


def release_lock():
    try:
        LOCKFILE.unlink(missing_ok=True)
    except Exception:
        pass


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
    print(f"[feedback-loop] Starting at {datetime.now().isoformat()}")

    if not acquire_lock():
        sys.exit(0)

    try:
        results = []
        results.append(run_agent("agents/feedback-agent.py", "entry-feedback", 400))
        results.append(run_agent("agents/evaluation-agent.py", "heimdall", 400))

        # Gate 2: pre-distribution audit (opus). Exit code 2 = NO-GO.
        audit_result = run_agent("agents/pre-dist-audit-agent.py", "pre-dist-audit", 500)
        results.append(audit_result)
        if not audit_result["success"]:
            print(f"\n[feedback-loop] Gate 2 blocked distribution. Check knowledge/meta/pre-dist-audit.md")
        else:
            results.append(run_agent("agents/distribute.py", "distribute", 300))

        date = datetime.now().strftime("%Y-%m-%d")
        total = sum(r["elapsed_s"] for r in results)
        ok = sum(1 for r in results if r["success"])
        print(f"\n[feedback-loop] Done: {ok}/{len(results)} ok, {total:.0f}s")
        for r in results:
            s = "✓" if r["success"] else "✗"
            print(f"  {s} {r['agent']}: {r['elapsed_s']}s")

    finally:
        release_lock()


if __name__ == "__main__":
    main()
