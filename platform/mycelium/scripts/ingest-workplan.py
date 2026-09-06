#!/usr/bin/env python3
"""
Ingest open issues as WorkItem nodes with dependency edges.
Query the graph for optimal parallel execution paths.

This is how the system plans its own evolution — through its own topology.
"""

import os
import sys
from pathlib import Path

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))


def esc(s):
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")[:300]


def main():
    from falkordb import FalkorDB
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    g = db.select_graph("asgard")

    # === INGEST: WorkItem nodes with dependencies ===

    issues = [
        (40, "Stale skill: spec-to-ship v2", "small", []),
        (41, "Workflow drift detection", "medium", [40]),
        (46, "MCP write access control — deploy per-person tokens", "small", []),
        (47, "Security + rhythm — TLS via Caddy, final deployment", "medium", [46]),
        (48, "Secrets in traces — wire redaction into ingest-agent", "small", []),
        (49, "Threat model — FalkorDB requirepass, verify agent perms", "medium", []),
        (51, "Self-test harness — liveness, correctness, regression", "medium", []),
        (53, "Countermeasures CM1-CM7 — confidence decay, rate limit, content guard", "medium", []),
        (54, "Immune system — patrol, signatures, threat memory", "large", [51, 53]),
        (55, "Versioning — ChangeEvent logging, tracked_write", "medium", []),
    ]

    for num, title, effort, deps in issues:
        nid = f"workitem-issue-{num}"
        g.query(
            f"MERGE (w:WorkItem {{node_id: '{esc(nid)}'}}) "
            f"SET w.label = '#{num}: {esc(title)}', "
            f"w.issue_number = {num}, "
            f"w.effort = '{effort}', "
            f"w.status = 'open', "
            f"w.file_type = 'workitem'"
        )
        # Link to existing Issue nodes
        g.query(
            f"MATCH (w:WorkItem {{node_id: '{esc(nid)}'}}), "
            f"(i:Issue {{node_id: 'issue-maverick-meta-{num}'}}) "
            f"MERGE (w)-[:TRACKS]->(i)"
        )
        # Dependency edges
        for dep in deps:
            dep_nid = f"workitem-issue-{dep}"
            g.query(
                f"MATCH (w:WorkItem {{node_id: '{esc(nid)}'}}), "
                f"(d:WorkItem {{node_id: '{esc(dep_nid)}'}}) "
                f"MERGE (w)-[:DEPENDS_ON]->(d)"
            )

    # Create Wave nodes
    waves = [
        ("wave-2", "Wave 2: Quick closes + security basics", [48, 46]),
        ("wave-3", "Wave 3: Security hardening (parallel)", [53, 55, 49]),
        ("wave-4", "Wave 4: Test + skill evolution (parallel)", [51, 40, 41]),
        ("wave-5", "Wave 5: Integration — immune system + TLS", [54, 47]),
    ]

    for wave_id, wave_label, issue_nums in waves:
        g.query(
            f"MERGE (wave:Wave {{node_id: '{esc(wave_id)}'}}) "
            f"SET wave.label = '{esc(wave_label)}', wave.file_type = 'wave'"
        )
        for num in issue_nums:
            nid = f"workitem-issue-{num}"
            g.query(
                f"MATCH (wave:Wave {{node_id: '{esc(wave_id)}'}}), "
                f"(w:WorkItem {{node_id: '{esc(nid)}'}}) "
                f"MERGE (wave)-[:CONTAINS]->(w)"
            )

    # Wave sequence
    for i in range(len(waves) - 1):
        g.query(
            f"MATCH (a:Wave {{node_id: '{esc(waves[i][0])}'}}), "
            f"(b:Wave {{node_id: '{esc(waves[i+1][0])}'}}) "
            f"MERGE (a)-[:FLOWS_TO]->(b)"
        )

    # Link WorkItems to Knowledge nodes by keyword
    keywords = {
        40: ["spec-to-ship", "skill"],
        41: ["skill", "workflow"],
        46: ["asgard", "graph", "access"],
        49: ["security", "threat"],
        51: ["testing", "harness", "health"],
        53: ["injection", "defense", "redact"],
        55: ["versioning", "history", "change"],
    }

    for num, kws in keywords.items():
        nid = f"workitem-issue-{num}"
        for kw in kws:
            try:
                g.query(
                    f"MATCH (w:WorkItem {{node_id: '{esc(nid)}'}}), (k:Knowledge) "
                    f"WHERE toLower(k.label) CONTAINS '{esc(kw)}' "
                    f"WITH w, k LIMIT 2 "
                    f"MERGE (w)-[:RELATES_TO]->(k)"
                )
            except Exception:
                pass

    print("Ingested: 10 WorkItems, 4 Waves, dependency edges, knowledge links")

    # === ANALYZE: Parallel execution paths ===

    print("\n=== PARALLEL EXECUTION ANALYSIS ===\n")

    # Independent items (no blockers)
    r = g.query(
        "MATCH (w:WorkItem {status: 'open'}) "
        "WHERE NOT (w)-[:DEPENDS_ON]->(:WorkItem) "
        "RETURN w.label, w.effort ORDER BY w.effort"
    )
    print("Independent items (can start immediately, in parallel):")
    for row in r.result_set:
        print(f"  [{row[1]}] {row[0]}")

    # Critical path (longest dependency chain)
    print()
    r2 = g.query(
        "MATCH path = (w:WorkItem)-[:DEPENDS_ON*]->(dep:WorkItem) "
        "RETURN w.label, length(path) AS depth, collect(dep.label) AS chain "
        "ORDER BY depth DESC LIMIT 3"
    )
    print("Longest dependency chains (critical path):")
    for row in r2.result_set:
        print(f"  {row[0]} (depth {row[1]}): depends on {row[2]}")

    # Highest-impact items (unblock the most work)
    print()
    r3 = g.query(
        "MATCH (blocker:WorkItem)<-[:DEPENDS_ON]-(dependent:WorkItem) "
        "RETURN blocker.label, count(dependent) AS blocks_count "
        "ORDER BY blocks_count DESC"
    )
    print("Highest-impact items (unblock the most work):")
    for row in r3.result_set:
        print(f"  {row[0]} — unblocks {row[1]} items")

    # Knowledge areas most touched by open work
    print()
    r4 = g.query(
        "MATCH (w:WorkItem {status: 'open'})-[:RELATES_TO]->(k:Knowledge) "
        "RETURN k.label, count(w) AS work_connections "
        "ORDER BY work_connections DESC LIMIT 5"
    )
    print("Knowledge areas most connected to open work:")
    for row in r4.result_set:
        print(f"  {row[0]} — {row[1]} items")

    # Wave execution plan with effort
    print()
    r5 = g.query(
        "MATCH (wave:Wave)-[:CONTAINS]->(w:WorkItem) "
        "WITH wave, collect(w.label + ' [' + w.effort + ']') AS items, count(w) AS size "
        "ORDER BY wave.node_id "
        "RETURN wave.label, size, items"
    )
    print("Wave execution plan:")
    for row in r5.result_set:
        print(f"\n  {row[0]} ({row[1]} items):")
        for item in row[2]:
            print(f"    - {item}")

    # Max parallelism per wave
    print("\n\n=== OPTIMAL PARALLEL STRATEGY ===\n")
    print("Wave 2: 2 items, both independent → run 2 agents in parallel")
    print("Wave 3: 3 items, all independent → run 3 agents in parallel")
    print("Wave 4: 3 items, #41 depends on #40 → run #51 + #40 in parallel, then #41")
    print("Wave 5: 2 items, #54 depends on #51+#53, #47 depends on #46 → run after Wave 3+4")
    print()
    print("Total agents across all waves: 10")
    print("With max parallelism: 4 rounds of parallel execution")

    # How this encodes in the graph
    print("\n\n=== HOW THIS ENCODES IN THE GRAPH ===\n")
    print("The planning topology is now part of the graph itself:")
    print("  WorkItem nodes — what needs to be done")
    print("  DEPENDS_ON edges — what blocks what")
    print("  Wave nodes — parallel execution groups")
    print("  FLOWS_TO edges — wave sequence")
    print("  RELATES_TO edges — which knowledge areas are touched")
    print("  TRACKS edges — link back to Issue nodes")
    print()
    print("This means:")
    print("  1. The system can query its own development plan")
    print("  2. Dream rounds can detect work convergence (multiple items touching same knowledge)")
    print("  3. When a WorkItem is completed, set status='done' — the graph updates")
    print("  4. The heartbeat can check: are any WorkItems stale? blocked? stuck?")
    print("  5. The planning itself becomes structural coupling — the graph knows what it needs")


if __name__ == "__main__":
    main()
