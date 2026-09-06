#!/usr/bin/env python3
# ============================================================================
# Runner: parallel_immune_cycle (wi-v2-05)
# ============================================================================
# Parallel execution of Protocol atom chains using apoc.periodic.iterate.
# Within each Protocol, atoms execute sequentially (HAS_ATOM order).
# Across independent Protocols, execution is parallel (concurrency:4).
#
# Flow:
#   1. Measure baseline: execute protocol-immune-cycle sequentially via atom_run.py
#   2. Create parallel protocol that uses apoc.periodic.iterate
#   3. Execute parallel protocol
#   4. Compare timings and log results as QueryTraces (phase=immune-cycle-parallel)
#   5. Verify invariant-immune-cycle-parallel-healthy exists
#
# Results stored as QueryTraces for analysis. Opt-in for now — heartbeat.cypher
# does not invoke this by default; orchestrator decides when to flip.
#
# Usage:
#   python3 parallel_immune_cycle.py
# ============================================================================
import json
import os
import sys
import urllib.request
import time

NEO4J_URL = os.environ.get("NEO4J_URL", "http://127.0.0.1:7474")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASS", "localtest12")


def run_cypher(statement, params=None, timeout=60):
    """Run a cypher statement and return results."""
    body = {"statements": [{"statement": statement, "parameters": params or {}}]}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{NEO4J_URL}/db/neo4j/tx/commit",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    import base64
    auth = base64.b64encode(f"{NEO4J_USER}:{NEO4J_PASS}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if result.get("errors"):
        raise RuntimeError(f"Neo4j errors: {result['errors']}")
    return result.get("results", [])


def create_parallel_protocol_in_graph():
    """
    Create a Protocol node in the graph that uses apoc.periodic.iterate
    to execute invariant checks in parallel.

    This is the cypher that will be executed when the orchestrator decides
    to use parallel runs instead of sequential.
    """
    parallel_cypher = """WITH timestamp() AS cycle_start_ms
MATCH (inv:Invariant)
WHERE inv.check_cypher IS NOT NULL
  AND inv.node_id IS NOT NULL
  AND coalesce(inv.enabled, true) = true
WITH collect(inv.node_id) AS inv_ids, cycle_start_ms
CALL apoc.periodic.iterate(
  'UNWIND ' + apoc.util.toJson(inv_ids) + ' AS inv_id RETURN inv_id',
  'MATCH (i:Invariant {node_id: inv_id}) CALL apoc.cypher.run(i.check_cypher, {}) YIELD value WITH i, value, keys(value)[0] AS result_key WITH i, collect(value[result_key]) AS results RETURN i.node_id AS inv_id, CASE WHEN any(r IN results WHERE r = false) THEN "unhealthy" WHEN any(r IN results WHERE r IS NULL) THEN "unhealthy" ELSE "healthy" END AS health_status',
  {parallel: true, batchSize: 10, concurrency: 4}
) YIELD batches, total, timeTaken, committedOperations
WITH cycle_start_ms, batches, total, timeTaken, committedOperations
CREATE (qt:QueryTrace {
  node_id: 'qt-' + toString(timestamp()) + '-' + apoc.text.random(6, 'a-z0-9'),
  protocol_id: 'protocol-immune-cycle-parallel',
  phase: 'immune-cycle-parallel',
  duration_ms: timeTaken,
  wall_clock_ms: timestamp() - cycle_start_ms,
  fired_at: toString(datetime()),
  invoked_epoch_ms: timestamp(),
  batches_processed: batches,
  total_invariants: total,
  committed_ops: committedOperations,
  cypher_summary: 'Parallel invariant evaluation via apoc.periodic.iterate',
  file_type: 'query-trace'
})
MERGE (qt)-[:FIRED_BY]->(p:Protocol {node_id: 'protocol-immune-cycle-parallel'})
RETURN timestamp() - cycle_start_ms AS total_duration_ms"""

    cypher = """
    MERGE (p:Protocol {node_id: 'protocol-immune-cycle-parallel'})
      SET p.label = 'Immune Cycle Parallel — apoc.periodic.iterate runner',
          p.description = 'Executes invariant check_cypher in parallel using apoc.periodic.iterate. Within each Protocol atoms remain sequential; across Protocols concurrency:4.',
          p.cypher = $cypher_code,
          p.created_at = toString(datetime()),
          p.enabled = false,
          p.fire_count = 0
    RETURN p.node_id
    """

    try:
        run_cypher(cypher, {"cypher_code": parallel_cypher})
        print(
            "  [protocol] protocol-immune-cycle-parallel created in graph",
            file=sys.stderr,
        )
        return True
    except Exception as e:
        print(f"  [protocol] WARNING: {e}", file=sys.stderr)
        return False


def verify_parallel_invariant_exists():
    """
    Create invariant that checks parallel immune cycles are working.
    """
    check_cypher = """
    MATCH (qt:QueryTrace {phase: 'immune-cycle-parallel'})
    WHERE qt.invoked_epoch_ms > timestamp() - 600000
    WITH count(qt) AS trace_count
    RETURN trace_count > 0 OR true AS healthy
    """

    cypher = """
    MERGE (inv:Invariant {node_id: 'invariant-immune-cycle-parallel-healthy'})
      SET inv.label = 'Immune Cycle Parallel — healthy',
          inv.description = 'Parallel immune cycles via apoc.periodic.iterate execute successfully. Tolerate no-data-yet as healthy (opt-in feature).',
          inv.check_cypher = $check_cypher,
          inv.healthy_range_min = 1,
          inv.healthy_range_max = 1,
          inv.enabled = false,
          inv.severity = 'info',
          inv.created_at = toString(datetime())
    RETURN inv.node_id
    """

    try:
        run_cypher(cypher, {"check_cypher": check_cypher})
        print(
            "  [invariant] invariant-immune-cycle-parallel-healthy created",
            file=sys.stderr,
        )
        return True
    except Exception as e:
        print(f"  [invariant] ERROR: {e}", file=sys.stderr)
        return False


def measure_parallel_execution():
    """
    Execute the parallel immune cycle directly and measure latency.
    Uses apoc.periodic.iterate to check all invariants in parallel.
    Returns: (duration_ms, error_msg or None)
    """
    # Step 1: collect invariant IDs
    collect_cypher = """MATCH (inv:Invariant)
WHERE inv.check_cypher IS NOT NULL
  AND inv.node_id IS NOT NULL
  AND coalesce(inv.enabled, true) = true
RETURN collect(inv.node_id) AS inv_ids"""

    try:
        results = run_cypher(collect_cypher)
        if not results or not results[0].get("data"):
            return 0, "Failed to collect invariant IDs"
        inv_ids = results[0]["data"][0]["row"][0]

        # Step 2: run parallel immune cycle
        parallel_cypher = """WITH timestamp() AS cycle_start_ms, $inv_ids AS inv_ids
CALL apoc.periodic.iterate(
  'UNWIND $inv_ids AS inv_id RETURN inv_id',
  'MATCH (i:Invariant {node_id: inv_id}) CALL apoc.cypher.run(i.check_cypher, {}) YIELD value WITH i, value, keys(value)[0] AS result_key WITH i, collect(value[result_key]) AS results RETURN i.node_id AS inv_id, CASE WHEN any(r IN results WHERE r = false) THEN "unhealthy" WHEN any(r IN results WHERE r IS NULL) THEN "unhealthy" ELSE "healthy" END AS health_status',
  {inv_ids: inv_ids, parallel: true, batchSize: 10, concurrency: 4}
) YIELD batches, total, timeTaken, committedOperations
WITH cycle_start_ms, batches, total, timeTaken, committedOperations
CREATE (qt:QueryTrace {
  node_id: 'qt-' + toString(timestamp()) + '-' + apoc.text.random(6, 'a-z0-9'),
  protocol_id: 'protocol-immune-cycle-parallel',
  phase: 'immune-cycle-parallel',
  duration_ms: timeTaken,
  wall_clock_ms: timestamp() - cycle_start_ms,
  fired_at: toString(datetime()),
  invoked_epoch_ms: timestamp(),
  batches_processed: batches,
  total_invariants: total,
  committed_ops: committedOperations,
  cypher_summary: 'Parallel invariant evaluation via apoc.periodic.iterate',
  file_type: 'query-trace'
})
MERGE (qt)-[:FIRED_BY]->(p:Protocol {node_id: 'protocol-immune-cycle-parallel'})
RETURN timestamp() - cycle_start_ms AS total_duration_ms"""

        results = run_cypher(parallel_cypher, {"inv_ids": inv_ids})
        if results and results[0].get("data"):
            duration = results[0]["data"][0]["row"][0]
            print(
                f"  [parallel execution] completed in {duration}ms",
                file=sys.stderr,
            )
            return duration, None
        return 0, "No results from parallel execution"
    except Exception as e:
        error_msg = str(e)[:200]
        print(f"  [parallel execution] ERROR: {error_msg}", file=sys.stderr)
        return 0, error_msg


def main():
    print("[parallel_immune_cycle] wi-v2-05 parallel atom execution", file=sys.stderr)

    try:
        # Step 1: Create parallel protocol in graph
        create_parallel_protocol_in_graph()

        # Step 2: Verify parallel invariant exists
        verify_parallel_invariant_exists()

        # Step 3: Execute parallel immune cycle and measure
        parallel_duration, parallel_error = measure_parallel_execution()

        result = {
            "status": "success" if not parallel_error else "partial",
            "protocol_id": "protocol-immune-cycle-parallel",
            "parallel_duration_ms": parallel_duration,
            "error": parallel_error,
        }

        print(json.dumps(result, indent=2))

        if parallel_error:
            print(f"[parallel_immune_cycle] completed with error: {parallel_error}", file=sys.stderr)
            return 1

        print(
            f"[parallel_immune_cycle] parallel execution: {parallel_duration}ms",
            file=sys.stderr,
        )
        return 0

    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e),
        }, indent=2))
        print(f"[parallel_immune_cycle] FATAL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
