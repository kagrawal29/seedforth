#!/usr/bin/env python3
"""
wi-v3-05-swarm-refactor: Single Python process with persistent bolt connection.

Design Choice A: Python neo4j driver with one Session, 6 worker threads.
- Single persistent bolt connection across all workers
- No bash subprocess spawning per worker
- Thread pool for parallel execution
- Target: <5s total for 6-worker sweep (baseline was 45s)

Usage:
  python3 swarm_driver.py [--workers 6] [--from-prompt "task"]
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from neo4j import GraphDatabase, basic_auth

NEO4J_BOLT = os.environ.get("NEO4J_BOLT", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASS", "localtest12")


class SwarmDriver:
    def __init__(self, bolt_url=NEO4J_BOLT, user=NEO4J_USER, password=NEO4J_PASS):
        """Initialize driver with persistent connection pool."""
        self.driver = GraphDatabase.driver(bolt_url, auth=basic_auth(user, password))

    def close(self):
        """Close the driver."""
        self.driver.close()

    def get_swarm_atoms(self, worker_count=6, from_prompt=None):
        """Fetch atom list from cmd-swarm protocol execution."""
        with self.driver.session() as session:
            # Execute cmd-swarm protocol to get atom list
            cypher = """
            MATCH (p:Protocol {node_id: 'protocol-heartbeat-core'})-[:HAS_ATOM]->(a:CypherAtom)
            WHERE a.cypher IS NOT NULL
            WITH a ORDER BY a.order ASC
            LIMIT $limit
            RETURN COLLECT({
                atom_id: a.atom_id,
                cypher: a.cypher,
                order: a.order
            }) AS atoms
            """
            result = session.run(cypher, {"limit": worker_count})
            row = result.single()
            if row:
                return row["atoms"]
            return []

    def execute_atom(self, atom_id, atom_cypher):
        """Execute a single atom, measuring duration."""
        with self.driver.session() as session:
            start_ms = int(time.time() * 1000)
            try:
                result = session.run(atom_cypher)
                records = result.data()
                end_ms = int(time.time() * 1000)
                duration_ms = end_ms - start_ms
                return {
                    "atom_id": atom_id,
                    "status": "success",
                    "duration_ms": duration_ms,
                    "record_count": len(records),
                }
            except Exception as e:
                end_ms = int(time.time() * 1000)
                duration_ms = end_ms - start_ms
                return {
                    "atom_id": atom_id,
                    "status": "error",
                    "duration_ms": duration_ms,
                    "error": str(e)[:100],
                }

    def dispatch_swarm(self, worker_count=6, from_prompt=None):
        """
        Dispatch N workers in parallel via thread pool.
        Single connection, persistent session reuse.
        """
        start_ts = time.time()
        start_ms = int(start_ts * 1000)

        # Fetch atoms to execute
        atoms = self.get_swarm_atoms(worker_count, from_prompt)
        if not atoms:
            return {
                "status": "error",
                "error": "no atoms found",
                "wallclock_ms": 0,
                "workers_executed": 0,
            }

        # Execute atoms in parallel via ThreadPoolExecutor
        worker_results = []
        with ThreadPoolExecutor(max_workers=min(worker_count, len(atoms))) as executor:
            futures = {
                executor.submit(self.execute_atom, atom["atom_id"], atom["cypher"]): atom
                for atom in atoms
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    worker_results.append(result)
                except Exception as e:
                    atom = futures[future]
                    worker_results.append({
                        "atom_id": atom["atom_id"],
                        "status": "error",
                        "error": str(e)[:100],
                        "duration_ms": 0,
                    })

        end_ts = time.time()
        end_ms = int(end_ts * 1000)
        wallclock_ms = end_ms - start_ms

        # Aggregate stats
        successful = sum(1 for r in worker_results if r["status"] == "success")
        total_work_ms = sum(r.get("duration_ms", 0) for r in worker_results)

        return {
            "status": "success",
            "workers_requested": len(atoms),
            "workers_executed": successful,
            "wallclock_ms": wallclock_ms,
            "total_work_ms": total_work_ms,
            "design": "A - Python driver pool, persistent connection, ThreadPoolExecutor",
            "results": worker_results,
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Mycelium swarm with persistent connection")
    parser.add_argument("--workers", type=int, default=6, help="Number of parallel workers")
    parser.add_argument("--from-prompt", type=str, help="Task prompt for semantic dispatch")
    args = parser.parse_args()

    driver = SwarmDriver()
    try:
        result = driver.dispatch_swarm(worker_count=args.workers, from_prompt=args.from_prompt)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] == "success" else 1)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
