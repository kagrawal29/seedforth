#!/usr/bin/env python3
"""
Protocol Runner — the graph tells Python what to think about.

Reads Protocol nodes, follows ENABLES edges, executes Cypher or boundary scripts.
This file has zero intelligence. The intelligence is graph topology.

To change the system's behavior, change the graph — not this file.

Usage:
    python3 scripts/pipeline.py              # full protocol chain
    python3 scripts/pipeline.py boundary     # boundary only
    python3 scripts/pipeline.py digest       # digest + excrete only
"""

import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Import traced graph from ingest.py — single source of truth for graph connections
sys.path.insert(0, str(REPO_ROOT))
from scripts.ingest import get_graph


def resolve_template(cypher: str) -> str:
    now = datetime.now(timezone.utc)
    return (cypher
        .replace("$TODAY", now.strftime("%Y-%m-%d"))
        .replace("$NOW", now.isoformat())
        .replace("$CUTOFF_2D", (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"))
        .replace("$CUTOFF_7D", (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S"))
        .replace("$CUTOFF_14D", (now - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S"))
    )


def load_protocols(graph, phases=None):
    """Read Protocol nodes from the graph, ordered by topology."""
    phase_filter = ""
    if phases:
        quoted = ", ".join(f"'{p}'" for p in phases)
        phase_filter = f"AND p.phase IN [{quoted}] "

    r = graph.query(
        f"MATCH (p:Protocol) "
        f"WHERE p.enabled = true {phase_filter}"
        f"RETURN p.node_id, p.name, p.phase, p.protocol_type, "
        f"  p.description, p.cypher, p.script_path, p.protocol_order "
        f"ORDER BY p.protocol_order"
    )
    return [
        {"node_id": row[0], "name": row[1], "phase": row[2],
         "type": row[3], "description": row[4], "cypher": row[5],
         "script_path": row[6], "order": row[7]}
        for row in (r.result_set or [])
    ]


def execute(graph, protocol):
    """Execute a single protocol. Returns (status, summary)."""
    ptype = protocol["type"]

    if ptype == "boundary":
        script = str(REPO_ROOT / protocol["script_path"])
        try:
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True, text=True, timeout=300,
                cwd=str(REPO_ROOT), env=os.environ.copy(),
            )
            output = (result.stdout or "").strip()
            if output:
                for line in output.split("\n")[-3:]:
                    print(f"      {line}")
            if result.returncode != 0:
                return "failed", (result.stderr or "")[-200:]
            return "ok", output.split("\n")[-1] if output else ""
        except subprocess.TimeoutExpired:
            return "timeout", ""

    elif ptype in ("cypher", "template"):
        cypher = protocol["cypher"]
        if not cypher:
            return "skipped", "no cypher"
        if ptype == "template":
            cypher = resolve_template(cypher)
        try:
            r = graph.query(cypher)
            if r.result_set:
                row = r.result_set[0]
                return "ok", ", ".join(str(v) for v in row)
            return "ok", "no results"
        except Exception as e:
            return "failed", str(e)[:200]

    return "skipped", f"unknown type: {ptype}"


def check_tdd_gate(graph, protocol_id):
    """TDD enforcement: refuse to execute protocols without tests."""
    try:
        r = graph.query(
            f"MATCH (tc:TestCase)-[:VALIDATES]->(p:Protocol {{node_id: '{protocol_id}'}}) "
            f"RETURN count(tc)"
        )
        count = r.result_set[0][0] if r.result_set else 0
        return count > 0
    except Exception:
        return False


def run_tests(graph, protocol_id, pipeline_run_id):
    """Run TestCase nodes, record TestRun nodes with full evidence."""
    ts = datetime.now(timezone.utc).isoformat()

    try:
        r = graph.query(
            f"MATCH (t:TestCase)-[:VALIDATES]->(p:Protocol {{node_id: '{protocol_id}'}}) "
            f"RETURN t.node_id, t.label, t.cypher"
        )
    except Exception:
        return []

    results = []
    for row in (r.result_set or []):
        test_id, label, cypher = row
        if not cypher:
            continue

        # Resolve templates in test cypher too
        resolved_cypher = resolve_template(cypher)

        start = time.time()
        try:
            tr = graph.query(resolved_cypher)
            elapsed = time.time() - start
            passed = tr.result_set[0][0] if tr.result_set else False
            output = str(tr.result_set) if tr.result_set else "[]"
            error = None
        except Exception as e:
            elapsed = time.time() - start
            passed = False
            output = ""
            error = str(e)[:200]

        status = "pass" if passed else "fail"

        # Create TestRun node — the evidence trail
        run_node_id = f"testrun-{test_id}-{ts.replace(':', '-')}"
        try:
            graph.query(
                f"MERGE (tr:TestRun {{node_id: '{run_node_id}'}}) "
                f"SET tr.passed = {'true' if passed else 'false'}, "
                f"tr.timestamp = '{ts}', "
                f"tr.elapsed_s = {elapsed:.3f}, "
                f"tr.output = \"{esc_dq(output[:500])}\", "
                f"tr.file_type = 'test-run'"
            )
            # Link to TestCase
            graph.query(
                f"MATCH (tr:TestRun {{node_id: '{run_node_id}'}}), "
                f"(tc:TestCase {{node_id: '{test_id}'}}) "
                f"MERGE (tr)-[:INSTANCE_OF]->(tc)"
            )
            # Link to PipelineRun
            if pipeline_run_id:
                graph.query(
                    f"MATCH (tr:TestRun {{node_id: '{run_node_id}'}}), "
                    f"(pr:PipelineRun {{node_id: '{pipeline_run_id}'}}) "
                    f"MERGE (tr)-[:DURING]->(pr)"
                )
        except Exception:
            pass

        # Update TestCase aggregates
        try:
            graph.query(
                f"MATCH (t:TestCase {{node_id: '{test_id}'}}) "
                f"SET t.last_result = '{status}', "
                f"t.last_run = '{ts}', "
                f"t.run_count = coalesce(t.run_count, 0) + 1, "
                f"t.pass_count = coalesce(t.pass_count, 0) + {'1' if passed else '0'}, "
                f"t.fail_count = coalesce(t.fail_count, 0) + {'0' if passed else '1'}, "
                f"t.streak = CASE WHEN '{status}' = 'pass' THEN coalesce(t.streak, 0) + 1 ELSE 0 END"
            )
        except Exception:
            pass

        results.append((label, status.upper() if status == "FAIL" else status))

    return results


def esc_dq(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def main():
    phases = None
    if len(sys.argv) > 1:
        valid = ("meta", "boundary", "digest", "excrete")
        phases = [a for a in sys.argv[1:] if a in valid]
        if not phases:
            print(f"Usage: {sys.argv[0]} [{' | '.join(valid)}]")
            sys.exit(1)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[protocol] {ts}")
    print(f"[protocol] Graph: {FALKORDB_HOST}:{FALKORDB_PORT}")

    try:
        graph = get_graph()
    except Exception as e:
        print(f"[protocol] FalkorDB unavailable: {e}")
        sys.exit(1)

    protocols = load_protocols(graph, phases)
    if not protocols:
        print("[protocol] No Protocol nodes found. Run seed-protocols.py first.")
        sys.exit(1)

    phase_names = sorted(set(p["phase"] for p in protocols), key=lambda x: protocols[0]["order"])
    print(f"[protocol] Phases: {' → '.join(dict.fromkeys(p['phase'] for p in protocols))}")
    print(f"[protocol] Protocols: {len(protocols)}")
    print(f"[protocol] Cost: $0.00")

    # Create PipelineRun node upfront so TestRuns can link to it
    pipeline_run_id = f"pipeline-run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"

    results = []
    current_phase = None
    total_start = time.time()
    tdd_blocked = []

    for protocol in protocols:
        if protocol["phase"] != current_phase:
            current_phase = protocol["phase"]
            label = {"meta": "decide", "boundary": "perceive",
                     "digest": "connect", "excrete": "act"}
            print(f"\n  {'='*40}")
            print(f"  {current_phase.upper()} — {label.get(current_phase, '')}")
            print(f"  {'='*40}")

        # TDD GATE: refuse to execute protocols without tests
        if not check_tdd_gate(graph, protocol["node_id"]):
            print(f"\n    [{protocol['name']}] BLOCKED — no TestCase validates this protocol")
            tdd_blocked.append(protocol["name"])
            results.append({"name": protocol["name"], "status": "tdd-blocked", "elapsed": 0})
            try:
                graph.query(
                    f"MATCH (p:Protocol {{node_id: '{protocol['node_id']}'}}) "
                    f"SET p.last_status = 'tdd-blocked', p.last_run = '{ts}'"
                )
            except Exception:
                pass
            continue

        print(f"\n    [{protocol['name']}] {protocol['description']}")
        start = time.time()

        status, summary = execute(graph, protocol)
        elapsed = time.time() - start

        # Update protocol node
        try:
            graph.query(
                f"MATCH (p:Protocol {{node_id: '{protocol['node_id']}'}}) "
                f"SET p.last_status = '{status}', "
                f"p.last_run = '{ts}', "
                f"p.last_elapsed_s = {elapsed:.1f}"
            )
        except Exception:
            pass

        print(f"    [{protocol['name']}] {status.upper()} ({elapsed:.1f}s) {summary[:100]}")
        results.append({"name": protocol["name"], "status": status, "elapsed": elapsed})

        # Run tests and record TestRun nodes
        for label, test_status in run_tests(graph, protocol["node_id"], pipeline_run_id):
            print(f"      TEST {test_status}: {label}")

    total_elapsed = time.time() - total_start
    ok = sum(1 for r in results if r["status"] == "ok")
    failed = [r["name"] for r in results if r["status"] not in ("ok", "skipped", "tdd-blocked")]
    blocked = [r["name"] for r in results if r["status"] == "tdd-blocked"]

    # Finalize PipelineRun node
    try:
        graph.query(
            f"MERGE (pr:PipelineRun {{node_id: '{pipeline_run_id}'}}) "
            f"SET pr.label = 'Protocol run {ts}', "
            f"pr.timestamp = '{ts}', "
            f"pr.protocols_total = {len(results)}, "
            f"pr.protocols_ok = {ok}, "
            f"pr.protocols_failed = {len(failed)}, "
            f"pr.protocols_tdd_blocked = {len(blocked)}, "
            f"pr.elapsed_s = {total_elapsed:.1f}, "
            f"pr.cost = 0, "
            f"pr.file_type = 'pipeline-run'"
        )
    except Exception:
        pass

    print(f"\n  {'='*40}")
    print(f"  PROTOCOL COMPLETE")
    print(f"  {'='*40}")
    print(f"  Protocols: {ok}/{len(results)} passed")
    if blocked:
        print(f"  TDD blocked: {len(blocked)} ({', '.join(blocked)})")
    print(f"  Time: {total_elapsed:.1f}s")
    print(f"  Cost: $0.00")
    if failed:
        print(f"  Failed: {', '.join(failed)}")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
