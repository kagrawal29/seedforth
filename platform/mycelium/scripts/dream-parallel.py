#!/usr/bin/env python3
"""
dream-parallel.py — multi-process dream loop (threaded).

Spawns N worker threads (default 10). Each worker:
  • Selects a Protocol node (round-robin across DREAM_PROTOCOL_NODES or fallback)
  • Executes its stored Cypher every DREAM_INTERVAL seconds (default 2s = 0.5Hz)
  • Logs the timestamp + worker id + row count, printing up to 2 rows for inspection
  • Continues until interrupted, or until DREAM_MAX_ITER iterations are reached

Environment:
  FALKORDB_HOST / FALKORDB_PORT   — graph endpoint (defaults 5.78.206.137:6380)
  GRAPH_NAME                      — target graph (default "asgard")
  DREAM_WORKERS                   — number of parallel workers (default 10)
  DREAM_INTERVAL                  — seconds between runs (default 2.0)
  DREAM_MAX_ITER                  — iterations per worker (0 = infinite)
  DREAM_PROTOCOL_NODES            — comma-separated node_ids to round-robin
  PROTOCOL_LOOP_NODE / LOOP_PROTOCOL_NODE — fallback single protocol id
"""

from __future__ import annotations

import os
import sys
import threading
import time
from datetime import datetime
from typing import List, Optional

try:
    from falkordb import FalkorDB
except ImportError:  # pragma: no cover - runtime helper
    print("pip install falkordb", file=sys.stderr)
    raise

HOST = os.environ.get("FALKORDB_HOST", "5.78.206.137")
PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
GRAPH = os.environ.get("GRAPH_NAME", "asgard")
WORKERS = int(os.environ.get("DREAM_WORKERS", "10"))
INTERVAL = float(os.environ.get("DREAM_INTERVAL", "2.0"))
MAX_ITER = int(os.environ.get("DREAM_MAX_ITER", "0"))

_protocol_list = os.environ.get("DREAM_PROTOCOL_NODES", "").strip()
if _protocol_list:
    PROTOCOLS: List[str] = [p.strip() for p in _protocol_list.split(",") if p.strip()]
else:
    fallback = (
        os.environ.get("PROTOCOL_LOOP_NODE")
        or os.environ.get("LOOP_PROTOCOL_NODE")
        or "protocol-self-iterate"
    )
    PROTOCOLS = [fallback]


def _connect():
    db = FalkorDB(host=HOST, port=PORT)
    return db.select_graph(GRAPH)


def _fetch_protocol(graph, node_id: str) -> Optional[dict]:
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


def _run_worker(worker_id: int):
    graph = _connect()
    protocol_id = PROTOCOLS[worker_id % len(PROTOCOLS)]
    iterations = 0
    print(
        f"Worker {worker_id} targeting {protocol_id} every {INTERVAL}s."
    )
    while True:
        stamp = datetime.utcnow().isoformat()
        proto = _fetch_protocol(graph, protocol_id)
        if not proto:
            print(f"[{stamp}] worker {worker_id}: protocol {protocol_id} missing; stopping")
            return
        try:
            result = graph.query(proto["cypher"])
            rows = result.result_set or []
            print(
                f"[{stamp}] worker {worker_id}: {protocol_id} → {len(rows)} rows"
            )
            for row in rows[:2]:
                print(
                    "    "
                    + " | ".join("" if v is None else str(v) for v in row)
                )
        except Exception as exc:  # pragma: no cover - live output only
            print(f"[{stamp}] worker {worker_id}: error {exc}")
        iterations += 1
        if MAX_ITER and iterations >= MAX_ITER:
            print(f"worker {worker_id}: reached {MAX_ITER} iterations, exiting")
            return
        time.sleep(INTERVAL)


def main() -> int:
    threads: List[threading.Thread] = []
    print(
        f"Parallel dream loop: {WORKERS} workers at {INTERVAL}s cadence on {HOST}:{PORT}/{GRAPH}."
    )
    for worker_id in range(WORKERS):
        t = threading.Thread(target=_run_worker, args=(worker_id,), daemon=False)
        threads.append(t)
        t.start()
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("Interrupted; exiting once workers finish current cycle.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
