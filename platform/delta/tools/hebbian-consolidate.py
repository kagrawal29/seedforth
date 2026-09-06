#!/usr/bin/env python3
"""Hebbian consolidation (P3.3) — strengthen well-read paths, decay stale ones.

QueryTraces link to nodes via READS (written by graph-tool.py). The more a
node is read, the more its connected reasoning edges strengthen; the longer
since a read, the more they decay. We adjust edge weights, never delete.

Runs in the weekly (long) cycle. Uses the fast HTTP API like all graph tools.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from neo4j_helper import q_strict

# 1. STRENGTHEN: nodes read often (>=3 distinct traces) in 7 days boost edges.
q_strict(
    "MATCH (n)<-[:READS]-(qt:QueryTrace) "
    "WHERE qt.created_at > datetime() - duration({days: 7}) "
    "WITH n, count(DISTINCT qt) AS reads "
    "WHERE reads >= 3 "
    "MATCH (n)-[e]->() "
    "SET e.weight = coalesce(e.weight, 1.0) + 0.1 * reads "
    "SET n.hebbian_boost = reads"
)
print("hebbian: strengthened well-read paths")

# 2. DECAY: nodes with no reads in 14 days lose edge weight (floor 0.2).
q_strict(
    "MATCH (n) "
    "WHERE NOT ((n)<-[:READS]-()) "
    "AND (n.created_at IS NULL OR n.created_at < datetime() - duration({days: 14})) "
    "MATCH (n)-[e]->() "
    "WHERE NOT e.decay_protected "
    "SET e.weight = coalesce(e.weight, 1.0) * 0.95 "
    "WITH n, count(e) AS decayed "
    "WHERE decayed > 0 "
    "SET n.decayed_at = datetime()"
)
print("hebbian: decayed stale paths")
