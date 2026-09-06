#!/usr/bin/env python3
"""
Graph-Driven Pipeline Orchestrator — the graph runs itself.

Instead of hardcoded sequential stages in Python, this reads the pipeline
from FalkorDB: walk PipelineStage nodes via FLOWS_TO edges, execute each
stage's script, record results on the node.

Adding a stage = adding a node + FLOWS_TO edge.
Changing order = changing edges.
Disabling a stage = removing a FLOWS_TO edge.
The dream round can modify the pipeline by editing the graph.

Falls back to the hardcoded run-synthesis.py if FalkorDB is unreachable.
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
MAX_LOCK_AGE_MINUTES = 60

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))


def _pid_alive(pid):
    """Check if a process is still running."""
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

            # Check if holding process is still alive
            if lock_pid and _pid_alive(lock_pid) and age < MAX_LOCK_AGE_MINUTES:
                print(f"[synthesis] Lock held by PID {lock_pid} ({age:.0f}m ago). Skipping.")
                return False

            if lock_pid and not _pid_alive(lock_pid):
                print(f"[synthesis] Breaking lock from dead PID {lock_pid} ({age:.0f}m old).")
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


def run_stage(script, label, timeout_seconds=600):
    """Execute a pipeline stage subprocess."""
    print(f"\n  [{label}] Running {script}...")
    start = time.time()
    proc = None
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
                    tf.flush()
        proc.wait(timeout=5)
        stdout = "".join(stdout_lines)
        elapsed = time.time() - start

        if stdout:
            for line in stdout.strip().split("\n")[-5:]:
                print(f"  [{label}] {line}")

        result = {"success": proc.returncode == 0, "elapsed_s": round(elapsed, 1)}

        # Parse SDK telemetry
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
        if proc:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=5)
            except Exception:
                try: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except: pass
        return {"success": False, "elapsed_s": round(elapsed, 1), "error": "timeout"}
    except Exception as e:
        elapsed = time.time() - start
        if proc:
            try: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except: pass
        return {"success": False, "elapsed_s": round(elapsed, 1), "error": str(e)[:100]}


def get_pipeline_from_graph():
    """Read the pipeline execution plan from Neo4j.

    Walks PipelineStage → FLOWS_TO → PipelineStage chain.
    Returns ordered list of {node_id, label, script, timeout, uses_llm}.
    """
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        session = driver.session()

        # Find the start node (no incoming FLOWS_TO)
        start_result = session.run(
            "MATCH (s:PipelineStage) "
            "WHERE NOT (:PipelineStage)-[:FLOWS_TO]->(s) "
            "RETURN s.node_id"
        )
        start_rows = [r.values() for r in start_result]

        if not start_rows:
            driver.close()
            return None

        start_id = start_rows[0][0]

        # Walk step by step with cycle detection
        stages = []
        visited = set()
        current_id = start_id
        max_depth = 30

        while current_id and current_id not in visited and len(stages) < max_depth:
            visited.add(current_id)
            safe_id = current_id.replace("'", "\\'")
            r = session.run(
                f"MATCH (s:PipelineStage {{node_id: '{safe_id}'}}) "
                f"OPTIONAL MATCH (s)-[:FLOWS_TO]->(next:PipelineStage) "
                f"RETURN s.node_id, s.label, s.script, s.cost_usd, s.uses_llm, next.node_id"
            )
            result_rows = [row.values() for row in r]
            if not result_rows:
                break

            row = result_rows[0]
            stages.append({
                "node_id": row[0],
                "label": row[1],
                "script": row[2],
                "cost_usd": row[3] or 0,
                "uses_llm": row[4],
            })

            current_id = row[5]

        if len(stages) >= max_depth:
            print(f"  [graph-pipeline] WARNING: pipeline walk hit depth limit ({max_depth}). Possible cycle.")

        driver.close()
        return stages if stages else None

    except Exception as e:
        print(f"  [graph-pipeline] Could not read pipeline from graph: {e}")
        return None


def record_result_to_graph(node_id, result):
    """Write stage execution result back to the PipelineStage node."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        session = driver.session()

        ts = datetime.now(timezone.utc).isoformat()
        success = result.get("success", False)
        elapsed = result.get("elapsed_s", 0)
        cost = result.get("sdk_cost_usd", 0)
        error = result.get("error", "")
        retry_count = result.get("retry_count", 0)

        session.run(
            f"MATCH (s:PipelineStage {{node_id: '{node_id}'}}) "
            f"SET s.last_run = '{ts}', "
            f"s.last_success = {str(success).lower()}, "
            f"s.last_elapsed_s = {elapsed}, "
            f"s.last_cost_usd = {cost}, "
            f"s.last_error = '{error[:100]}', "
            f"s.last_retry_count = {retry_count}"
        )
        driver.close()
    except Exception:
        pass


def refresh_graph_cache():
    """Refresh graph context cache files."""
    try:
        sys.path.insert(0, str(ROOT))
        from scripts.lib.graph_context import synthesis_context, heimdall_context, audit_context
        from scripts.lib.ask_asgard import ask_demand
        meta_dir = ROOT / "knowledge" / "meta"
        ctx = synthesis_context()
        if ctx.strip():
            (meta_dir / "graph-context.md").write_text(ctx)
        demand = ask_demand()
        if demand.strip():
            (meta_dir / "graph-demand.md").write_text(demand)
        (meta_dir / "heimdall-graph-context.md").write_text(heimdall_context())
        (meta_dir / "pre-dist-graph-context.md").write_text(audit_context())
        print(f"  [graph-cache] Refreshed")
    except Exception as e:
        print(f"  [graph-cache] Non-fatal: {str(e)[:60]}")


def main():
    print(f"[graph-pipeline] Starting at {datetime.now().isoformat()}")

    if not acquire_lock():
        sys.exit(0)

    try:
        # Read pipeline from graph
        stages = get_pipeline_from_graph()

        if stages:
            print(f"[graph-pipeline] Pipeline loaded from graph: {len(stages)} stages")
            for s in stages:
                marker = "$" if s["uses_llm"] else " "
                print(f"  {marker} {s['label']} ({s['script']})")
        else:
            print("[graph-pipeline] Could not load from graph — falling back to hardcoded")
            os.execv(sys.executable, [sys.executable, str(ROOT / "agents" / "run-synthesis.py")])
            return

        # Execute each stage
        results = []
        for stage in stages:
            label = stage["label"].lower().replace(" ", "-")
            script = stage["script"]

            if not script or not (ROOT / script).exists():
                print(f"\n  [{label}] Script not found: {script}. Skipping.")
                continue

            # Invariant 3: pipeline allowlist — only known scripts can execute
            try:
                from scripts.lib.invariants import is_allowed_pipeline_script
                if not is_allowed_pipeline_script(script):
                    print(f"\n  [{label}] BLOCKED: {script} not in pipeline allowlist. Skipping.")
                    continue
            except ImportError:
                pass  # If invariants module not available, fail open (log warning)

            # Determine timeout: LLM stages get more time
            timeout = 600 if stage["uses_llm"] else 120

            result = run_stage(script, label, timeout)

            # Retry with exponential backoff for transient LLM failures
            retry_count = 0
            if not result["success"] and stage.get("uses_llm"):
                max_retries = 2
                backoff_seconds = [30, 60]
                for attempt in range(max_retries):
                    wait = backoff_seconds[attempt]
                    retry_count = attempt + 1
                    print(f"  [{label}] Failed (attempt {retry_count}/{max_retries + 1}). "
                          f"Retrying in {wait}s...")
                    time.sleep(wait)
                    result = run_stage(script, label, timeout)
                    if result["success"]:
                        print(f"  [{label}] Succeeded on retry {retry_count}.")
                        break

            result["retry_count"] = retry_count
            results.append({"stage": stage, "result": result})

            # Record result back to graph
            record_result_to_graph(stage["node_id"], result)

            if not result["success"]:
                print(f"  [{label}] Non-fatal: failed after {retry_count + 1} attempt(s). Pipeline continues.")

            # Refresh graph cache after sync stages
            if stage["node_id"] in ("pipe-graph-sync", "pipe-sync-layers"):
                refresh_graph_cache()

        # Summary
        total_elapsed = sum(r["result"]["elapsed_s"] for r in results)
        ok = sum(1 for r in results if r["result"]["success"])
        total_cost = sum(r["result"].get("sdk_cost_usd", 0) for r in results)

        print(f"\n[graph-pipeline] Done: {ok}/{len(results)} ok, {total_elapsed:.0f}s, ${total_cost:.2f}")
        for r in results:
            s = "✓" if r["result"]["success"] else "✗"
            label = r["stage"]["label"]
            elapsed = r["result"]["elapsed_s"]
            cost = r["result"].get("sdk_cost_usd", 0)
            cost_str = f"${cost:.2f}" if cost else ""
            print(f"  {s} {label}: {elapsed}s {cost_str}")

    finally:
        release_lock()


if __name__ == "__main__":
    main()
