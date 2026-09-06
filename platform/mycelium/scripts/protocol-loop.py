#!/usr/bin/env python3
"""
protocol-loop.py — dream cadence runner

Each iteration:
  • Finds the next enabled Protocol node (least-recently-run)
  • Executes its Cypher
  • Prints the Cypher + English plain-language summary
  • Updates last_run / last_elapsed_s / last_status
Sleeps GRAPH_LOOP_INTERVAL seconds between iterations (default 120).

Environment:
  FALKORDB_HOST / PORT — defaults localhost:6380
  GRAPH_NAME           — defaults "asgard"
  GRAPH_LOOP_INTERVAL  — seconds between iterations
  GRAPH_LOOP_MAX_ITER  — optional iteration cap (0 = infinite)
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Sequence

try:
    from falkordb import FalkorDB
except ImportError:
    print("pip install falkordb", file=sys.stderr)
    raise

HOST = os.environ.get("FALKORDB_HOST", "localhost")
PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
GRAPH = os.environ.get("GRAPH_NAME", "asgard")
INTERVAL = int(os.environ.get("GRAPH_LOOP_INTERVAL", "120"))
MAX_ITER = int(os.environ.get("GRAPH_LOOP_MAX_ITER", "0"))
TARGET_PROTOCOL = (
    os.environ.get("PROTOCOL_LOOP_NODE")
    or os.environ.get("LOOP_PROTOCOL_NODE")
)
INLINE_CYPHER = os.environ.get("PROTOCOL_LOOP_CYPHER")
INLINE_DESC = os.environ.get("PROTOCOL_LOOP_DESC", "Inline Cypher")


def _connect():
    db = FalkorDB(host=HOST, port=PORT)
    return db.select_graph(GRAPH)


NEXT_PROTOCOL_CYPHER = """
MATCH (p:Protocol)
WHERE coalesce(p.enabled, true)
RETURN p.node_id AS node_id,
       p.cypher   AS cypher,
       coalesce(p.plain_english, p.label, p.name, p.node_id) AS description,
       p.label    AS label,
       coalesce(p.protocol_order, 0) AS ord,
       coalesce(p.last_run, '1970-01-01T00:00:00Z') AS lr
ORDER BY lr ASC, ord ASC, node_id ASC
LIMIT 1
"""


def _fetch_next_protocol(graph) -> Dict[str, Any] | None:
    result = graph.query(NEXT_PROTOCOL_CYPHER).result_set or []
    if not result:
        return None
    row = result[0]
    return {
        "node_id": row[0],
        "cypher": row[1],
        "description": row[2],
        "label": row[3],
    }


def _fetch_protocol_by_id(graph, node_id: str) -> Dict[str, Any] | None:
    safe_id = node_id.replace("\\", "\\\\").replace("'", "\\'")
    cypher = (
        "MATCH (p:Protocol {node_id: '%s'}) "
        "RETURN p.node_id, p.cypher, "
        "coalesce(p.plain_english, p.label, p.name, p.node_id), "
        "p.label"
    ) % safe_id
    result = graph.query(cypher).result_set or []
    if not result:
        return None
    row = result[0]
    return {
        "node_id": row[0],
        "cypher": row[1],
        "description": row[2],
        "label": row[3],
    }


def _update_protocol_status(graph, node_id: str, elapsed: float, status: str) -> None:
    if not node_id:
        return
    now = datetime.utcnow().isoformat() + "Z"
    cypher = (
        "MATCH (p:Protocol {node_id: '%s'}) "
        "SET p.last_run = '%s', "
        "p.last_elapsed_s = %.4f, "
        "p.last_status = '%s', "
        "p.fire_count = coalesce(p.fire_count, 0) + 1, "
        "p.amortization_status = CASE "
        "  WHEN coalesce(p.fire_count, 0) + 1 = 0 THEN 'dead' "
        "  WHEN coalesce(p.fire_count, 0) + 1 >= 1 AND coalesce(p.fire_count, 0) + 1 <= 2 THEN 'experimental' "
        "  WHEN coalesce(p.fire_count, 0) + 1 >= 3 AND coalesce(p.fire_count, 0) + 1 <= 10 THEN 'active' "
        "  WHEN coalesce(p.fire_count, 0) + 1 >= 11 AND coalesce(p.fire_count, 0) + 1 <= 50 THEN 'strengthened' "
        "  WHEN coalesce(p.fire_count, 0) + 1 >= 51 THEN 'critical' "
        "  ELSE 'unknown' "
        "END"
    ) % (
        node_id.replace("'", "\\'"),
        now,
        elapsed,
        status,
    )
    graph.query(cypher)


def _print_rows(rows: Sequence[Sequence[Any]]) -> None:
    rows = list(rows)
    if not rows:
        print("  (empty)")
        return
    for row in rows:
        print("  → " + " | ".join("" if v is None else str(v) for v in row))


def main() -> int:
    graph = _connect()
    print(
        f"Protocol loop connected to {HOST}:{PORT}/{GRAPH}. "
        f"Interval: {INTERVAL}s. Ctrl+C to stop."
    )
    if INLINE_CYPHER:
        print("Mode: inline Cypher from PROTOCOL_LOOP_CYPHER")
    elif TARGET_PROTOCOL:
        print(f"Mode: fixed Protocol node {TARGET_PROTOCOL}")
    else:
        print("Mode: rotating least-recently-run Protocols")
    iterations = 0

    try:
        while True:
            iterations += 1
            stamp = datetime.utcnow().isoformat()
            if INLINE_CYPHER:
                proto = {
                    "node_id": None,
                    "cypher": INLINE_CYPHER,
                    "description": INLINE_DESC,
                    "label": INLINE_DESC,
                }
            elif TARGET_PROTOCOL:
                proto = _fetch_protocol_by_id(graph, TARGET_PROTOCOL)
            else:
                proto = _fetch_next_protocol(graph)
            if not proto:
                if TARGET_PROTOCOL:
                    print(f"[{stamp}] Protocol {TARGET_PROTOCOL} not found. Exiting.")
                else:
                    print(f"[{stamp}] No enabled Protocol nodes found. Exiting.")
                break

            node_id = proto["node_id"]
            desc = proto["description"]
            cypher = proto["cypher"]
            display_id = node_id or "(inline)"
            print(f"\n[{stamp}] Protocol {display_id}")
            print("Description:")
            print(f"  {desc}")
            print("Cypher:")
            print(cypher)

            status = "ok"
            start = time.time()
            try:
                result = graph.query(cypher)
                rows = result.result_set or []
                elapsed = time.time() - start
                print("English:")
                print(f"  {desc}")
                _print_rows(rows)
            except Exception as exc:
                elapsed = time.time() - start
                status = "error"
                print(f"  error: {exc}")
            _update_protocol_status(graph, node_id, elapsed, status)

            if MAX_ITER and iterations >= MAX_ITER:
                print("Reached GRAPH_LOOP_MAX_ITER, exiting.")
                break

            print(f"\nSleeping {INTERVAL} seconds...\n")
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("\nStopped protocol loop.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
