#!/usr/bin/env python3
"""
Full Cycle — convenience wrapper that runs both loops sequentially.

For independent operation, use:
  python3 agents/run-synthesis.py   (every 3h during work hours)
  python3 agents/run-feedback.py    (daily + skill feedback every 2d)

This script runs both in sequence for when you want a complete cycle.
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run_loop(script, label):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    start = time.time()
    result = subprocess.run(
        ["python3", script],
        cwd=ROOT,
        timeout=1200,  # 20 min max per loop
    )
    elapsed = time.time() - start
    status = "✓" if result.returncode == 0 else "✗"
    print(f"\n  {status} {label}: {elapsed:.0f}s")
    return result.returncode == 0


def main():
    print(f"[full-cycle] Starting at {datetime.now().isoformat()}")

    s1 = run_loop("agents/run-synthesis.py", "SYNTHESIS LOOP")
    s2 = run_loop("agents/run-feedback.py", "FEEDBACK LOOP")

    print(f"\n{'='*60}")
    print(f"  FULL CYCLE: {'BOTH OK' if s1 and s2 else 'PARTIAL'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
