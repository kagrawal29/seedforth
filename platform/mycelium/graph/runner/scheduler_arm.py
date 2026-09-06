#!/usr/bin/env python3
"""Graph-native loop registrar.

Reads every (:SchedulerJob {enabled:true}) node and registers it with
apoc.periodic.repeat. Adding a new autonomous loop = MERGE a SchedulerJob node
and re-run `./mycelium start`.
"""
import os
import sys

from neo4j import GraphDatabase

BOLT = os.environ.get("NEO4J_BOLT", "bolt://localhost:7687")
USER = os.environ.get("NEO4J_USER", "neo4j")
PASS = os.environ.get("NEO4J_PASS", "localtest12")


def main() -> int:
    driver = GraphDatabase.driver(BOLT, auth=(USER, PASS))
    with driver.session() as s:
        jobs = list(
            s.run(
                "MATCH (j:SchedulerJob {enabled: true}) "
                "RETURN j.job_name AS name, j.target_protocol_id AS target, "
                "j.interval_seconds AS every"
            )
        )
        if not jobs:
            print("no SchedulerJob nodes — nothing to arm")
            return 0
        for j in jobs:
            try:
                s.run(
                    "CALL apoc.periodic.cancel($n) YIELD name RETURN name",
                    n=j["name"],
                ).consume()
            except Exception:
                pass
            stmt = (
                f'MATCH (p:Protocol {{node_id: "{j["target"]}"}}) '
                "WHERE p.cypher IS NOT NULL "
                "CALL apoc.cypher.runMany(p.cypher, {}) YIELD result "
                "RETURN count(result)"
            )
            r = list(
                s.run(
                    "CALL apoc.periodic.repeat($n, $s, $i) YIELD name RETURN name",
                    n=j["name"],
                    s=stmt,
                    i=j["every"],
                )
            )
            if r:
                print(f"armed {r[0]['name']} → {j['target']} every {j['every']}s")
            else:
                print(f"FAILED to arm {j['name']}", file=sys.stderr)
        active = list(
            s.run("CALL apoc.periodic.list() YIELD name, delay RETURN name, delay")
        )
        print(f"active periodic jobs: {len(active)}")
    driver.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
