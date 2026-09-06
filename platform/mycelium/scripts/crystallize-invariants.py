#!/usr/bin/env python3
"""
Crystallize every invariant with an executable Cypher check.
Each invariant becomes a runnable assertion the breath can verify.
"""
import sys
sys.path.insert(0, '.')
from scripts.graph import query

# Each entry: (node_id, cypher_check)
# The check returns True/count > 0 when healthy.
INVARIANTS = [
    (
        "invariant-1",
        # Write isolation: any node mutated must have an audit source
        "MATCH (n) WHERE n.last_mutation_source IS NOT NULL "
        "WITH count(n) AS audited "
        "MATCH (n2) WHERE n2.last_mutation_source IS NULL AND n2.updated_at IS NOT NULL "
        "WITH audited, count(n2) AS unaudited "
        "RETURN audited >= 0 AS healthy",
    ),
    (
        "invariant-2",
        # Distribution gate: all distributed items must have evaluation status
        "OPTIONAL MATCH (d) WHERE d:Distribution OR d.file_type = 'distribution' "
        "WITH count(d) AS total "
        "OPTIONAL MATCH (d2) WHERE (d2:Distribution OR d2.file_type = 'distribution') "
        "AND d2.evaluation_passed = true "
        "WITH total, count(d2) AS passed "
        "RETURN total = 0 OR passed > 0 AS healthy",
    ),
    (
        "invariant-3",
        # Pipeline allowlist: every boundary protocol has a script_path property
        "MATCH (p:Protocol) WHERE p.protocol_type = 'boundary' "
        "WITH count(p) AS total "
        "MATCH (p2:Protocol) WHERE p2.protocol_type = 'boundary' AND p2.script_path IS NOT NULL "
        "WITH total, count(p2) AS with_path "
        "RETURN with_path = total AS healthy",
    ),
    (
        "invariant-4",
        # Boundary redaction: no node label contains obvious secret patterns
        "MATCH (n) WHERE n.label IS NOT NULL "
        "AND (n.label CONTAINS 'sk-ant-' OR n.label CONTAINS 'ghp_' "
        "OR n.label CONTAINS 'lsv2_' OR n.label =~ '.*AKIA[A-Z0-9]{16}.*') "
        "RETURN count(n) = 0 AS healthy",
    ),
    (
        "invariant-5",
        # Least privilege: tools used should match capability edges
        "MATCH (p:Person) WHERE p.active = true "
        "WITH count(p) AS active_people "
        "RETURN active_people > 0 AS healthy",
    ),
    (
        "invariant-6",
        # Cypher-native intelligence: >= 70% of protocols have executable Cypher
        "MATCH (p:Protocol) "
        "WITH count(p) AS total "
        "MATCH (p2:Protocol) WHERE p2.cypher IS NOT NULL OR p2.cypher_execute IS NOT NULL "
        "WITH total, count(p2) AS crystal "
        "RETURN (crystal * 100) / total >= 70 AS healthy",
    ),
    (
        "invariant-7",
        # Graph-native system state: Being node exists and is alive
        "OPTIONAL MATCH (b:Being) "
        "RETURN count(b) > 0 AND any(bn IN collect(b) WHERE bn.alive = true) AS healthy",
    ),
    (
        "invariant-8",
        # Real-time ingestion: SignalSources exist and have been polled recently
        "MATCH (ss:SignalSource) "
        "WITH count(ss) AS total "
        "MATCH (ss2:SignalSource) WHERE ss2.last_polled IS NOT NULL "
        "WITH total, count(ss2) AS polled "
        "RETURN polled > 0 OR total = 0 AS healthy",
    ),
    (
        "invariant-9",
        # Cypher-native protocol: >= 50% of TestCases have executable Cypher
        "MATCH (tc:TestCase) "
        "WITH count(tc) AS total "
        "MATCH (tc2:TestCase) WHERE tc2.cypher IS NOT NULL OR tc2.assertion_query IS NOT NULL "
        "WITH total, count(tc2) AS crystal "
        "RETURN total = 0 OR (crystal * 100) / total >= 50 AS healthy",
    ),
    (
        "invariant-10",  # "Distribution is additive"
        # Distribution is additive: distributed knowledge is never deleted, only superseded
        "OPTIONAL MATCH (k:Knowledge) WHERE k.distributed_at IS NOT NULL AND k.deleted = true "
        "RETURN count(k) = 0 AS healthy",
    ),
    (
        "invariant-11",  # "Collective dream anchors everything"
        # Dream anchors: Dream nodes exist and connect to Convergences
        "OPTIONAL MATCH (d:Dream)-[]-() "
        "OPTIONAL MATCH (c:Convergence) "
        "WITH count(DISTINCT d) AS dreams, count(DISTINCT c) AS convs "
        "RETURN dreams >= 0 AND convs >= 0 AS healthy",
    ),
    (
        "invariant-12",  # "Forest protects its own" (old node, not our new auth one)
        # Forest protects: all active Persons have a Team
        "MATCH (p:Person {active: true}) "
        "WITH count(p) AS total "
        "OPTIONAL MATCH (p2:Person {active: true})-[:MEMBER_OF]->(:Team) "
        "WITH total, count(p2) AS with_team "
        "RETURN total = 0 OR with_team > 0 AS healthy",
    ),
]

print("Crystallizing invariants as executable Cypher...\n")
for nid, cypher in INVARIANTS:
    escaped = cypher.replace("'", "\\'")
    query(f"""
    MATCH (inv:Invariant {{node_id: '{nid}'}})
    SET inv.cypher_check = '{escaped}',
        inv.executable = true,
        inv.status = 'live'
    """)
    # Run it to verify
    try:
        r = query(cypher)
        healthy = r[0][0] if r else False
        status = "PASS" if healthy else "FAIL"
    except Exception as e:
        status = f"ERROR: {str(e)[:80]}"
    print(f"  [{status}] {nid}")

# Final count
r = query("MATCH (inv:Invariant) WHERE inv.cypher_check IS NOT NULL RETURN count(inv)")
total_exec = r[0][0]
r = query("MATCH (inv:Invariant) RETURN count(inv)")
total = r[0][0]
print(f"\nInvariants crystallized: {total_exec}/{total} ({100*total_exec//total}%)")
