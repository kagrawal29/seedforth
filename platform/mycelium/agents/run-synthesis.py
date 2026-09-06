#!/usr/bin/env python3
"""
Synthesis Loop Orchestrator — the breath of the living system.

INGEST → SENSE (demand) → INTENT (L5) → CONVERGENCE (L6) → SYNTHESIZE → GRAPH-SYNC → DREAM → INTEGRITY → HEIMDALL (gate 1) → PRE-DIST AUDIT (gate 2) → DISTRIBUTE

Each cycle is one breath:
  - Inhale: ingest signals from team activity (traces, commits, questions)
  - Sense: extract demand — what the team needs, not just what they did
  - Process: synthesize signals into knowledge, weave into the graph
  - Filter: Heimdall gates quality (immune system), audit checks health
  - Exhale: distribute back to team sessions (per-person context)
  - The team breathes in the context, works better, produces richer signals
  - The next breath begins

Runs independently from the feedback loop. Every 3h during work hours (10am-10pm IST), or on-demand.
"""

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
LOCKFILE = ROOT / "knowledge" / "meta" / ".synthesis-lock"
CYCLE_LOG = ROOT / "knowledge" / "meta" / "cycle-log.md"
MAX_LOCK_AGE_MINUTES = 60


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def acquire_lock():
    if LOCKFILE.exists():
        try:
            lock_data = json.loads(LOCKFILE.read_text())
            lock_time = datetime.fromisoformat(lock_data["ts"])
            lock_pid = lock_data.get("pid")
            age = (datetime.now(timezone.utc) - lock_time).total_seconds() / 60
            if lock_pid and _pid_alive(lock_pid) and age < MAX_LOCK_AGE_MINUTES:
                print(f"[synthesis] Lock held by PID {lock_pid} ({age:.0f}m ago). Skipping.")
                return False
            if lock_pid and not _pid_alive(lock_pid):
                print(f"[synthesis] Breaking lock from dead PID {lock_pid}.")
            elif age >= MAX_LOCK_AGE_MINUTES:
                print(f"[synthesis] Breaking stale lock ({age:.0f}m old).")
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
    """Run an agent subprocess with proper process-group cleanup on timeout.

    Uses start_new_session=True so the child (and any grandchildren like the
    Claude binary spawned by the Agent SDK) live in their own process group.
    On timeout we kill the entire group via os.killpg(), preventing orphaned
    grandchild processes from blocking the pipeline.

    Works on both macOS and Linux (Docker).
    """
    print(f"\n  [{label}] Running...")
    start = time.time()
    proc = None
    # Live trace: stream agent output to a log file for real-time monitoring
    trace_dir = ROOT / "knowledge" / "meta" / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_file = trace_dir / f"{label}-latest.log"
    try:
        proc = subprocess.Popen(
            ["python3", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=ROOT,
            start_new_session=True,
        )
        # Stream stdout to both log file and capture buffer
        stdout_lines = []
        with open(trace_file, "w") as tf:
            tf.write(f"=== {label} started at {datetime.now().isoformat()} ===\n")
            tf.flush()
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    stdout_lines.append(line)
                    tf.write(line)
                    tf.flush()  # Immediate write for tail -f
        proc.wait(timeout=5)
        stdout = "".join(stdout_lines)
        elapsed = time.time() - start
        if stdout:
            for line in stdout.strip().split("\n")[-5:]:
                print(f"  [{label}] {line}")
        # Parse Agent SDK telemetry from stdout
        result = {"agent": label, "success": proc.returncode == 0, "elapsed_s": round(elapsed, 1)}
        if stdout:
            for line in stdout.split("\n"):
                if "Duration:" in line:
                    try: result["sdk_duration_s"] = float(line.split("Duration:")[1].strip().rstrip("s"))
                    except: pass
                elif "Turns:" in line:
                    try: result["sdk_turns"] = int(line.split("Turns:")[1].strip())
                    except: pass
                elif "Cost: $" in line:
                    try: result["sdk_cost_usd"] = float(line.split("$")[1].strip())
                    except: pass
        return result
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        # Kill the entire process group (child + all grandchildren)
        if proc is not None:
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGTERM)
                # Give processes a moment to exit gracefully, then force-kill
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(pgid, signal.SIGKILL)
                    proc.wait(timeout=5)
            except (ProcessLookupError, OSError):
                # Process group already exited
                pass
        return {"agent": label, "success": False, "elapsed_s": round(elapsed, 1), "error": "timeout"}
    except Exception as e:
        elapsed = time.time() - start
        # Best-effort cleanup on unexpected errors
        if proc is not None:
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
        return {"agent": label, "success": False, "elapsed_s": round(elapsed, 1), "error": str(e)[:100]}


def refresh_graph_cache():
    """
    Refresh the graph cache files that agents sense on demand.

    Tier 1: graph-context.md — stable map (communities, god nodes)
    Tier 2: graph-demand.md — cycle demand signals

    Agents read these when their directives tell them to — not every run.
    Non-fatal: if FalkorDB is down, existing files stay (stale > absent).
    """
    try:
        sys.path.insert(0, str(ROOT))
        from scripts.lib.graph_context import synthesis_context, heimdall_context, audit_context
        from scripts.lib.ask_asgard import ask_demand

        meta_dir = ROOT / "knowledge" / "meta"

        # Tier 1: Stable map — communities, god nodes, cross-person connections
        ctx = synthesis_context()
        if ctx.strip():
            (meta_dir / "graph-context.md").write_text(ctx)

        # Tier 2: Demand signals — what the team is asking
        demand = ask_demand()
        if demand.strip():
            (meta_dir / "graph-demand.md").write_text(demand)

        # Backward compat: agents that reference old filenames
        (meta_dir / "heimdall-graph-context.md").write_text(heimdall_context())
        (meta_dir / "pre-dist-graph-context.md").write_text(audit_context())

        print(f"  [graph-cache] Refreshed context files from FalkorDB")
    except Exception as e:
        print(f"  [graph-cache] Non-fatal: {str(e)[:80]}. Agents sense stale or empty.")


def main():
    print(f"[synthesis-loop] Starting at {datetime.now().isoformat()}")

    if not acquire_lock():
        sys.exit(0)

    # --- TELEMETRY: the system observes itself ---
    try:
        sys.path.insert(0, str(ROOT))
        from scripts.lib.cycle_telemetry import CycleTelemetry
        tel = CycleTelemetry()
    except Exception:
        tel = None  # Telemetry unavailable — proceed without

    try:
        results = []

        # --- INHALE: pull signals from team activity ---
        if tel: tel.step_start("ingest")
        r = run_agent("agents/ingest-agent.py", "ingest", 300)
        results.append(r)
        if tel: tel.step_end("ingest", r)

        # --- DIRECT GRAPH INGEST: traces, commits, issues → FalkorDB (zero LLM) ---
        if tel: tel.step_start("graph-ingest")
        gi_result = run_agent("scripts/ingest-to-graph.py", "graph-ingest", 120)
        results.append(gi_result)
        if tel: tel.step_end("graph-ingest", gi_result)
        if not gi_result["success"]:
            print(f"  [graph-ingest] Non-fatal: direct ingestion failed. Pipeline continues.")

        # --- GRAPHIFY: extract graph structure from team docs ---
        if tel: tel.step_start("artifact-graphify")
        ag_result = run_agent("agents/artifact-graphify.py", "artifact-graphify", 600)
        results.append(ag_result)
        if tel: tel.step_end("artifact-graphify", ag_result)
        if not ag_result["success"]:
            print(f"  [artifact-graphify] Non-fatal: doc extraction failed. Pipeline continues.")

        # --- SENSE: extract demand — what does the team need? ---
        if tel: tel.step_start("demand")
        demand_result = run_agent("agents/demand-engine.py", "demand", 600)
        results.append(demand_result)
        if tel: tel.step_end("demand", demand_result)
        if not demand_result["success"]:
            print(f"  [demand] Non-fatal: demand extraction failed. Pipeline continues.")

        # --- INTENT: extract the question beneath the question (L5) ---
        if tel: tel.step_start("intent")
        intent_result = run_agent("agents/intent-engine.py", "intent", 600)
        results.append(intent_result)
        if tel: tel.step_end("intent", intent_result)
        if not intent_result["success"]:
            print(f"  [intent] Non-fatal: intent extraction failed. Pipeline continues.")

        # --- CONVERGENCE: detect cross-person intent alignment (L6) ---
        if tel: tel.step_start("convergence")
        conv_result = run_agent("scripts/convergence-detect.py", "convergence", 120)
        results.append(conv_result)
        if tel: tel.step_end("convergence", conv_result)
        if not conv_result["success"]:
            print(f"  [convergence] Non-fatal: convergence detection failed. Pipeline continues.")

        # --- SYNC LAYERS: write intents, convergences, phases to FalkorDB ---
        if tel: tel.step_start("sync-layers")
        sl_result = run_agent("scripts/sync-layers.py", "sync-layers", 120)
        results.append(sl_result)
        if tel: tel.step_end("sync-layers", sl_result)
        if not sl_result["success"]:
            print(f"  [sync-layers] Non-fatal: layer sync failed. Pipeline continues.")

        # --- CACHE: refresh graph context files (agents sense on demand) ---
        refresh_graph_cache()
        if tel:
            cache_files = ["graph-context.md", "graph-demand.md", "heimdall-graph-context.md", "pre-dist-graph-context.md"]
            tel.note_graph_cache_refresh(cache_files, falkordb_reachable=True)

        # --- PROCESS: weave signals into knowledge ---
        if tel: tel.step_start("synthesis")
        r = run_agent("agents/synthesis-agent.py", "synthesis", 600)
        results.append(r)
        if tel: tel.step_end("synthesis", r)

        # --- COUPLE: sync knowledge entries to FalkorDB ---
        if tel: tel.step_start("graph-sync")
        sync_result = run_agent("scripts/graph-sync.py", "graph-sync", 120)
        results.append(sync_result)
        if tel: tel.step_end("graph-sync", sync_result)
        if not sync_result["success"]:
            print(f"  [graph-sync] Non-fatal: graph sync failed. Pipeline continues.")

        # --- CACHE: refresh after sync (graph grew, cache should reflect it) ---
        refresh_graph_cache()
        if tel:
            tel.note_graph_cache_refresh(["graph-context.md", "graph-demand.md"], falkordb_reachable=True)

        # --- COMMUNITY MAP: regenerate from live graph after sync ---
        cmap_result = run_agent("scripts/generate-community-map-live.py", "community-map", 60)
        if not cmap_result["success"]:
            print(f"  [community-map] Non-fatal: community map regeneration failed. Pipeline continues.")
        else:
            results.append(cmap_result)

        # --- DREAM: structural analysis — missing triangles, fragile bridges, orphans ---
        if tel: tel.step_start("dream")
        # Export live graph to JSON format for dream-round.py
        dream_ok = False
        export_result = run_agent("scripts/export-graph.py", "graph-export", 60)
        if export_result["success"]:
            dream_result = run_agent("scripts/dream-round.py", "dream", 120)
            results.append(dream_result)
            dream_ok = dream_result["success"]
            if not dream_ok:
                print(f"  [dream] Non-fatal: dream analysis failed. Pipeline continues.")
        else:
            dream_result = export_result
            print(f"  [dream] Non-fatal: graph export failed, skipping dream round. Pipeline continues.")
        if tel: tel.step_end("dream", dream_result)

        # --- INTEGRITY: demand decay, edge verification, contradiction detection ---
        if tel: tel.step_start("integrity")
        integrity_result = run_agent("scripts/integrity-rules.py", "integrity", 120)
        results.append(integrity_result)
        if tel: tel.step_end("integrity", integrity_result)
        if not integrity_result["success"]:
            print(f"  [integrity] Non-fatal: integrity check failed. Pipeline continues.")

        # --- FILTER: immune system + health check ---
        if tel: tel.step_start("heimdall")
        r = run_agent("agents/evaluation-agent.py", "heimdall", 400)
        results.append(r)
        if tel: tel.step_end("heimdall", r)

        # Gate 2: pre-distribution audit (opus). Exit code 2 = NO-GO.
        if tel: tel.step_start("pre-dist-audit")
        audit_result = run_agent("agents/pre-dist-audit-agent.py", "pre-dist-audit", 900)
        results.append(audit_result)
        if tel: tel.step_end("pre-dist-audit", audit_result)

        if not audit_result["success"]:
            print(f"\n[synthesis-loop] Gate 2 blocked distribution. Check knowledge/meta/pre-dist-audit.md")
        else:
            if tel: tel.step_start("distribute")
            r = run_agent("agents/distribute.py", "distribute", 300)
            results.append(r)
            if tel: tel.step_end("distribute", r)

        # --- OBSERVE: save telemetry ---
        if tel:
            tel.save()
            print(f"  [telemetry] Saved to knowledge/meta/cycle-telemetry-latest.md")

        # Log
        date = datetime.now().strftime("%Y-%m-%d")
        total = sum(r["elapsed_s"] for r in results)
        ok = sum(1 for r in results if r["success"])
        print(f"\n[synthesis-loop] Done: {ok}/{len(results)} ok, {total:.0f}s")
        for r in results:
            s = "✓" if r["success"] else "✗"
            print(f"  {s} {r['agent']}: {r['elapsed_s']}s")

    finally:
        release_lock()


if __name__ == "__main__":
    main()
