"""
Cycle Telemetry — captures everything observable about each breath.

This is the system's self-awareness layer. Every step of every cycle
gets recorded: what ran, how long, what it produced, what it read,
what it cost. The telemetry IS demand — the system observing itself.

Output: knowledge/meta/cycle-telemetry.json (append, last 50 cycles)
        knowledge/meta/cycle-telemetry-latest.md (human-readable, latest only)

Usage (in run-synthesis.py):
    from scripts.lib.cycle_telemetry import CycleTelemetry

    tel = CycleTelemetry(cycle_id="2026-04-10-cycle-5")
    tel.step_start("ingest")
    result = run_agent(...)
    tel.step_end("ingest", result, files_produced=["signals/langsmith/..."])

    tel.graph_interaction("synthesis", "read", "graph-context.md", tokens=750)
    tel.graph_interaction("synthesis", "ask_asgard", "what connects to memory?", results=8)

    tel.save()  # writes both JSON and markdown
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TELEMETRY_JSON = REPO_ROOT / "knowledge" / "meta" / "cycle-telemetry.json"
TELEMETRY_MD = REPO_ROOT / "knowledge" / "meta" / "cycle-telemetry-latest.md"
MAX_HISTORY = 50


class CycleTelemetry:
    def __init__(self, cycle_id: str = None):
        self.cycle_id = cycle_id or datetime.now(timezone.utc).strftime("%Y-%m-%d-cycle-%H%M")
        self.start_time = time.time()
        self.start_ts = datetime.now(timezone.utc).isoformat()
        self.steps = []
        self.graph_interactions = []
        self.files_produced = []
        self.files_read = []
        self._current_step = None
        self._step_start = None

    def step_start(self, name: str):
        """Mark the beginning of a pipeline step."""
        self._current_step = name
        self._step_start = time.time()

    def step_end(self, name: str, result: dict, files_produced: list = None):
        """Record a completed pipeline step and write immediately."""
        elapsed = time.time() - (self._step_start or time.time())
        step = {
            "name": name,
            "success": result.get("success", False),
            "elapsed_s": round(elapsed, 1),
            "error": result.get("error"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sdk_duration_s": result.get("sdk_duration_s"),
            "sdk_turns": result.get("sdk_turns"),
            "sdk_cost_usd": result.get("sdk_cost_usd"),
        }
        if files_produced:
            step["files_produced"] = files_produced
            self.files_produced.extend(files_produced)
        self.steps.append(step)
        self._current_step = None
        self._step_start = None
        # Write immediately — real-time visibility
        self._write_live()

    def graph_interaction(self, agent: str, action: str, target: str,
                          tokens: int = 0, results: int = 0):
        """Record an agent-graph interaction."""
        self.graph_interactions.append({
            "agent": agent,
            "action": action,
            "target": target,
            "tokens": tokens,
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def file_read(self, agent: str, file_path: str, size_bytes: int = 0):
        """Record a file read by an agent."""
        self.files_read.append({
            "agent": agent,
            "file": file_path,
            "size_bytes": size_bytes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def note_graph_cache_refresh(self, files_refreshed: list, falkordb_reachable: bool):
        """Record that graph cache was refreshed. Write immediately."""
        self.graph_interactions.append({
            "agent": "orchestrator",
            "action": "cache_refresh",
            "target": ", ".join(files_refreshed),
            "tokens": 0,
            "results": len(files_refreshed),
            "falkordb_reachable": falkordb_reachable,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._write_live()

    def _write_live(self):
        """Write current state immediately — real-time visibility."""
        try:
            TELEMETRY_MD.write_text(self.to_markdown())
        except Exception:
            pass  # Never block the pipeline

    def to_dict(self) -> dict:
        """Export as dictionary."""
        total_elapsed = time.time() - self.start_time
        ok_count = sum(1 for s in self.steps if s["success"])
        return {
            "cycle_id": self.cycle_id,
            "start": self.start_ts,
            "end": datetime.now(timezone.utc).isoformat(),
            "total_elapsed_s": round(total_elapsed, 1),
            "steps_ok": ok_count,
            "steps_total": len(self.steps),
            "steps": self.steps,
            "graph_interactions": self.graph_interactions,
            "graph_interactions_count": len(self.graph_interactions),
            "files_produced": self.files_produced,
            "files_read": self.files_read,
        }

    def to_markdown(self) -> str:
        """Export as human-readable markdown."""
        d = self.to_dict()
        lines = [
            f"# Cycle Telemetry — {d['cycle_id']}",
            f"",
            f"**Time:** {d['start'][:19]} → {d['end'][:19]} ({d['total_elapsed_s']}s)",
            f"**Steps:** {d['steps_ok']}/{d['steps_total']} OK",
            f"**Graph interactions:** {d['graph_interactions_count']}",
            f"",
            "## Pipeline Steps",
            "",
            "| Step | Status | Time | SDK Duration | Turns | Cost | Error |",
            "|---|---|---|---|---|---|---|",
        ]
        for s in d["steps"]:
            status = "OK" if s["success"] else "FAIL"
            err = s.get("error", "") or ""
            sdk_dur = f"{s['sdk_duration_s']}s" if s.get("sdk_duration_s") else "—"
            turns = str(s["sdk_turns"]) if s.get("sdk_turns") else "—"
            cost = f"${s['sdk_cost_usd']:.4f}" if s.get("sdk_cost_usd") else "—"
            lines.append(f"| {s['name']} | {status} | {s['elapsed_s']}s | {sdk_dur} | {turns} | {cost} | {err} |")

        if d["graph_interactions"]:
            lines.extend([
                "",
                "## Graph Interactions",
                "",
                "| Agent | Action | Target | Tokens | Results |",
                "|---|---|---|---|---|",
            ])
            for g in d["graph_interactions"]:
                lines.append(
                    f"| {g['agent']} | {g['action']} | {g['target'][:60]} | {g.get('tokens', 0)} | {g.get('results', 0)} |"
                )

        if d["files_produced"]:
            lines.extend([
                "",
                "## Files Produced",
                "",
            ])
            for f in d["files_produced"]:
                lines.append(f"- {f}")

        return "\n".join(lines)

    def save(self):
        """Save telemetry to both JSON (history) and markdown (latest)."""
        try:
            d = self.to_dict()

            # Append to JSON history
            history = []
            if TELEMETRY_JSON.exists():
                try:
                    history = json.loads(TELEMETRY_JSON.read_text())
                except (json.JSONDecodeError, Exception):
                    history = []

            history.append(d)
            # Keep last N cycles
            if len(history) > MAX_HISTORY:
                history = history[-MAX_HISTORY:]

            TELEMETRY_JSON.write_text(json.dumps(history, indent=2))

            # Write human-readable latest
            TELEMETRY_MD.write_text(self.to_markdown())

            return True
        except Exception:
            return False
