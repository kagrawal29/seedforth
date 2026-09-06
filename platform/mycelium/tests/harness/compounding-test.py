#!/usr/bin/env python3
"""
Compounding Test — replays historical signals across multiple iterations.

Watches Asgard evolve: does the system compound (validate, extend, refine)
or just accumulate (unbounded growth)?

3 timeframes × (synthesis + counterfactual feedback) = 6 agent runs.

Usage:
  python3 tests/harness/compounding-test.py
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = ROOT / "signals" / "test-harness"

# Signal files grouped by timeframe
TIMEFRAMES = {
    "T1-apr6": {
        "label": "Apr 6 — Architecture decisions, first signals",
        "signals": [
            "signals/github/2026-04-06-deep-ingest.md",
            "signals/github/2026-04-06-delta-2.md",
            "signals/github/2026-04-06.md",
            "signals/langsmith/2026-04-06-cycle2.md",
        ],
    },
    "T2-apr7": {
        "label": "Apr 7 — Tech stack, feature design, enrichment",
        "signals": [
            "signals/github/2026-04-07-auto.md",
            "signals/langsmith/2026-04-07-auto.md",
            "signals/artifacts/2026-04-07-auto.md",
        ],
    },
    "T3-apr9": {
        "label": "Apr 9 — RAG research, memory scopes, rule builder",
        "signals": [
            "signals/github/2026-04-09-auto.md",
            "signals/langsmith/2026-04-09-auto.md",
            "signals/artifacts/2026-04-09-auto.md",
        ],
    },
}


def setup_workspace() -> Path:
    """Create clean workspace with empty Asgard but full tooling."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    workspace = Path(f"/tmp/compounding-test-{ts}")
    workspace.mkdir()

    # Copy everything except knowledge entries (start empty)
    for item in ["agents", "scripts", "config.yaml", ".claude", "CLAUDE.md"]:
        src = ROOT / item
        dst = workspace / item
        if src.is_dir():
            shutil.copytree(src, dst)
        elif src.is_file():
            shutil.copy2(src, dst)

    # Create empty knowledge structure
    (workspace / "knowledge").mkdir()
    for cat in ["architecture", "anti-patterns", "patterns", "workflows", "tool-configs"]:
        (workspace / "knowledge" / cat).mkdir()
    (workspace / "knowledge" / "meta").mkdir()

    # Empty index
    (workspace / "knowledge" / "index.md").write_text("# Team Knowledge Base\n\nNo entries yet.\n")
    (workspace / "knowledge" / "search-index.md").write_text("# Search Index\n\nNo entries yet.\n")

    # Create signals directory
    for d in ["langsmith", "github", "artifacts", "manual"]:
        (workspace / "signals" / d).mkdir(parents=True, exist_ok=True)

    # Remove hooks that would interfere
    hooks_dir = workspace / ".claude" / "hooks"
    if hooks_dir.exists():
        for f in hooks_dir.glob("*"):
            if f.name != "auto-sync.sh":
                f.unlink()

    # Git init (agents may commit)
    subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=workspace, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=workspace, capture_output=True)

    print(f"  Workspace: {workspace}")
    return workspace


def stage_signals(workspace: Path, timeframe_key: str):
    """Copy signal files for a specific timeframe into the workspace."""
    tf = TIMEFRAMES[timeframe_key]
    for signal_path in tf["signals"]:
        src = ROOT / signal_path
        if src.exists():
            dst = workspace / signal_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    print(f"  Staged {len(tf['signals'])} signal files for {timeframe_key}")


def snapshot_asgard(workspace: Path, label: str) -> dict:
    """Take a snapshot of Asgard state."""
    entries = list((workspace / "knowledge").rglob("*.md"))
    entries = [e for e in entries if "meta" not in str(e.relative_to(workspace / "knowledge"))
               and e.name not in ("index.md", "search-index.md")]

    rules = list((workspace / ".claude" / "rules").glob("*.md")) if (workspace / ".claude" / "rules").exists() else []

    return {
        "label": label,
        "entry_count": len(entries),
        "entries": [str(e.relative_to(workspace / "knowledge")) for e in entries],
        "rule_count": len(rules),
        "rules": [r.name for r in rules],
    }


async def run_synthesis(workspace: Path, timeframe_key: str) -> dict:
    """Run synthesis agent on the workspace."""
    tf = TIMEFRAMES[timeframe_key]
    print(f"\n  Running synthesis for {timeframe_key}: {tf['label']}")

    start = time.time()
    cost = 0
    async for msg in query(
        prompt=f"""You are the synthesis agent. Read the signal files in signals/ and create knowledge entries.

Read signals/langsmith/*.md, signals/github/*.md, signals/artifacts/*.md.
Read existing knowledge/ entries to check for connections (validate/contradict/extend).
Classify each signal into 8 types (T1-T8). Create entries with full frontmatter.
Run: python3 scripts/lint-knowledge.py && python3 scripts/build-search-index.py
Git commit your changes.""",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
            permission_mode="bypassPermissions",
            cwd=str(workspace),
            max_turns=30,
            max_budget_usd=5.0,
            model="sonnet",
        ),
    ):
        if isinstance(msg, ResultMessage):
            cost = msg.total_cost_usd or 0

    elapsed = time.time() - start
    return {"stage": "synthesis", "timeframe": timeframe_key, "cost": cost, "elapsed": round(elapsed, 1)}


async def run_heimdall(workspace: Path, context: str) -> dict:
    """Run Heimdall evaluation on workspace."""
    print(f"\n  Running Heimdall: {context}")

    start = time.time()
    cost = 0
    async for msg in query(
        prompt=f"""You are Heimdall, gatekeeper of Asgard. Review recent changes to the knowledge base.

Check git log for recent commits. Read each new/modified entry.
Score on: trace evidence, uniqueness, actionability, adoption likelihood, risk.
Approve (≥3/5), hold (2), discard (≤1).
Write evaluation to knowledge/meta/evaluation-log.md.
Git commit.""",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
            permission_mode="bypassPermissions",
            cwd=str(workspace),
            max_turns=25,
            max_budget_usd=3.0,
            model="sonnet",
        ),
    ):
        if isinstance(msg, ResultMessage):
            cost = msg.total_cost_usd or 0

    elapsed = time.time() - start
    return {"stage": "heimdall", "context": context, "cost": cost, "elapsed": round(elapsed, 1)}


async def run_counterfactual_feedback(workspace: Path, reference_traces_key: str) -> dict:
    """Run feedback in counterfactual mode using traces from a future timeframe."""
    tf = TIMEFRAMES[reference_traces_key]
    print(f"\n  Running counterfactual feedback using {reference_traces_key} traces")

    # Copy reference traces to a temp location the agent can read
    ref_dir = workspace / "signals" / "feedback-reference"
    ref_dir.mkdir(parents=True, exist_ok=True)
    for signal_path in tf["signals"]:
        src = ROOT / signal_path
        if src.exists() and "langsmith" in signal_path:
            shutil.copy2(src, ref_dir / Path(signal_path).name)

    start = time.time()
    cost = 0
    async for msg in query(
        prompt=f"""You are the feedback agent in COUNTERFACTUAL MODE.

The entries in knowledge/ were NOT actually deployed to the team. You cannot find evidence of actual usage. Instead, look for counterfactual evidence.

Read the reference traces in signals/feedback-reference/ — these are from AFTER the entries were created. For each knowledge entry, check:

- WOULD_PREVENT: Does a trace show someone re-exploring a decision this entry has settled? If yes → high value.
- WOULD_SURFACE: Does a trace show someone working on a topic this entry covers? If yes → medium value.
- WOULD_WARN: Does a trace show someone heading toward something an entry warns about? If yes → high value.
- GAP_CONFIRMED: Does a trace show frustration on a topic with NO matching entry? If yes → gap exists.

Write your analysis to knowledge/meta/feedback-counterfactual.md.
For each entry, propose: AMPLIFY, MONITOR, REVIEW, or REMOVE with reasoning.
Write proposals to knowledge/meta/feedback-proposals.md.
Git commit.""",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
            permission_mode="bypassPermissions",
            cwd=str(workspace),
            max_turns=30,
            max_budget_usd=4.0,
            model="sonnet",
        ),
    ):
        if isinstance(msg, ResultMessage):
            cost = msg.total_cost_usd or 0

    elapsed = time.time() - start
    return {"stage": "feedback-counterfactual", "reference": reference_traces_key, "cost": cost, "elapsed": round(elapsed, 1)}


async def main():
    print(f"{'='*60}")
    print(f"  COMPOUNDING TEST")
    print(f"  3 timeframes × (synthesis + feedback) = 6 iterations")
    print(f"{'='*60}")

    workspace = setup_workspace()
    results = []
    snapshots = {"v0": snapshot_asgard(workspace, "v0 — empty")}

    # === ITERATION 1: T1 → synthesis → Heimdall → feedback(T2) ===
    print(f"\n{'='*60}")
    print(f"  ITERATION 1: T1 (Apr 6) → synthesis → Heimdall → feedback(T2)")
    print(f"{'='*60}")

    stage_signals(workspace, "T1-apr6")
    results.append(await run_synthesis(workspace, "T1-apr6"))
    snapshots["v1-post-synthesis"] = snapshot_asgard(workspace, "v1 — post T1 synthesis")
    results.append(await run_heimdall(workspace, "T1 synthesis gate"))
    snapshots["v1-post-heimdall"] = snapshot_asgard(workspace, "v1 — post Heimdall")
    results.append(await run_counterfactual_feedback(workspace, "T2-apr7"))
    results.append(await run_heimdall(workspace, "T1 feedback gate"))
    snapshots["v1.1"] = snapshot_asgard(workspace, "v1.1 — post feedback")

    # === ITERATION 2: T2 → synthesis → Heimdall → feedback(T3) ===
    print(f"\n{'='*60}")
    print(f"  ITERATION 2: T2 (Apr 7) → synthesis → Heimdall → feedback(T3)")
    print(f"{'='*60}")

    stage_signals(workspace, "T2-apr7")
    results.append(await run_synthesis(workspace, "T2-apr7"))
    snapshots["v2-post-synthesis"] = snapshot_asgard(workspace, "v2 — post T2 synthesis")
    results.append(await run_heimdall(workspace, "T2 synthesis gate"))
    snapshots["v2-post-heimdall"] = snapshot_asgard(workspace, "v2 — post Heimdall")
    results.append(await run_counterfactual_feedback(workspace, "T3-apr9"))
    results.append(await run_heimdall(workspace, "T2 feedback gate"))
    snapshots["v2.1"] = snapshot_asgard(workspace, "v2.1 — post feedback")

    # === ITERATION 3: T3 → synthesis → Heimdall → feedback(all) ===
    print(f"\n{'='*60}")
    print(f"  ITERATION 3: T3 (Apr 9) → synthesis → Heimdall → feedback(all)")
    print(f"{'='*60}")

    stage_signals(workspace, "T3-apr9")
    results.append(await run_synthesis(workspace, "T3-apr9"))
    snapshots["v3-post-synthesis"] = snapshot_asgard(workspace, "v3 — post T3 synthesis")
    results.append(await run_heimdall(workspace, "T3 synthesis gate"))
    snapshots["v3-post-heimdall"] = snapshot_asgard(workspace, "v3 — post Heimdall")
    # Final feedback uses all traces
    results.append(await run_counterfactual_feedback(workspace, "T1-apr6"))
    results.append(await run_heimdall(workspace, "T3 feedback gate"))
    snapshots["v3.1"] = snapshot_asgard(workspace, "v3.1 — final")

    # === SUMMARY ===
    print(f"\n{'='*60}")
    print(f"  COMPOUNDING TEST RESULTS")
    print(f"{'='*60}")

    total_cost = sum(r["cost"] for r in results)
    total_time = sum(r["elapsed"] for r in results)
    print(f"\n  Total cost: ${total_cost:.2f}")
    print(f"  Total time: {total_time:.0f}s")

    print(f"\n  Asgard evolution:")
    for key, snap in snapshots.items():
        print(f"    {key}: {snap['entry_count']} entries, {snap['rule_count']} rules")

    print(f"\n  Per-stage costs:")
    for r in results:
        print(f"    {r['stage']}: ${r['cost']:.2f} ({r['elapsed']}s)")

    # Save full results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    result_file = RESULTS_DIR / f"{ts}-compounding.json"
    result_file.write_text(json.dumps({
        "snapshots": snapshots,
        "results": results,
        "total_cost": total_cost,
        "total_time": total_time,
        "workspace": str(workspace),
    }, indent=2, default=str))

    print(f"\n  Results: {result_file}")
    print(f"  Workspace: {workspace}")


if __name__ == "__main__":
    asyncio.run(main())
