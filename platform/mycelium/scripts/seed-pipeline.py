#!/usr/bin/env python3
"""
Seed the Cypher-native pipeline into the graph.

The pipeline IS the graph. Each stage is a node. Each Cypher query is a property.
FLOWS_TO edges define execution order. TestCase nodes validate each stage.

Python is I/O glue. This script runs once to create the pipeline topology.
After that, pipeline.py traverses and executes — reading structure from the graph.
"""

import os
import sys
from datetime import datetime, timezone

try:
    from falkordb import FalkorDB
except ImportError:
    print("ERROR: pip install falkordb", file=sys.stderr)
    sys.exit(1)

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "5.78.206.137")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))


def esc(s):
    """Escape for single-quoted Cypher strings."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


def esc_dq(s):
    """Escape for double-quoted Cypher strings (used for storing Cypher as properties)."""
    return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def get_graph():
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph("asgard")


# ================================================================
# PIPELINE DEFINITION — the Cypher queries ARE the pipeline
# ================================================================

STAGES = [
    # ============================================================
    # INGEST — the system perceives
    # ============================================================
    {
        "node_id": "pipeline-ingest-traces",
        "name": "ingest-traces",
        "phase": "ingest",
        "order": 1,
        "stage_type": "script",
        "description": "LangSmith traces + GitHub commits/issues → Trace, Commit, Issue, WorkItem nodes",
        "script_path": "scripts/ingest-to-graph.py",
        "cypher": None,  # external API calls required — script handles I/O
        "cost": 0,
    },
    {
        "node_id": "pipeline-ingest-knowledge",
        "name": "ingest-knowledge",
        "phase": "ingest",
        "order": 2,
        "stage_type": "script",
        "description": "knowledge/*.md → Knowledge nodes (delta via content hash)",
        "script_path": "scripts/graph-sync.py",
        "cypher": None,  # reads files, writes Cypher — script handles I/O
        "cost": 0,
    },

    # ============================================================
    # DIGEST — the system connects, validates, transforms
    # ============================================================

    # Sync any demand/intent/convergence JSON already produced
    {
        "node_id": "pipeline-digest-sync-layers",
        "name": "sync-layers",
        "phase": "digest",
        "order": 3,
        "stage_type": "script",
        "description": "demand/intent JSON → Intent, Convergence, Phase nodes",
        "script_path": "scripts/sync-layers.py",
        "cypher": None,  # reads JSON files — script handles I/O
        "cost": 0,
    },

    # Integrity Rule 1: Demand decay
    {
        "node_id": "pipeline-digest-demand-decay",
        "name": "demand-decay",
        "phase": "digest",
        "order": 4,
        "stage_type": "cypher",
        "description": "Flag Knowledge nodes with no demand, trace, or coupling activity",
        "cypher": (
            "MATCH (k:Knowledge) "
            "WHERE NOT (:Demand)-[]->(k) AND NOT (:Trace)-[:TOUCHES]->(k) "
            "AND NOT (:CouplingEvent)-[:ACTIVATED]->(k) "
            "SET k._decay_flagged = true "
            "RETURN count(k) AS decaying_nodes"
        ),
        "cost": 0,
    },

    # Integrity Rule 2: Stale edge pruning
    {
        "node_id": "pipeline-digest-stale-edges",
        "name": "stale-edge-pruning",
        "phase": "digest",
        "order": 5,
        "stage_type": "cypher",
        "description": "Delete INFERRED edges where neither endpoint has trace or coupling activity",
        "cypher": (
            "MATCH (a)-[r:CONCEPTUALLY_RELATED_TO]->(b) "
            "WHERE r.confidence = 'INFERRED' "
            "AND NOT (:Trace)-[:TOUCHES]->(a) "
            "AND NOT (:Trace)-[:TOUCHES]->(b) "
            "AND NOT (:CouplingEvent)-[:ACTIVATED]->(a) "
            "AND NOT (:CouplingEvent)-[:ACTIVATED]->(b) "
            "DELETE r "
            "RETURN count(r) AS pruned_edges"
        ),
        "cost": 0,
    },

    # Integrity Rule 3: Contradiction detection + resolution
    {
        "node_id": "pipeline-digest-contradictions",
        "name": "contradiction-resolution",
        "phase": "digest",
        "order": 6,
        "stage_type": "cypher",
        "description": "Demote lower-importance entry when same-category Knowledge nodes share 4+ tags",
        "cypher": (
            "MATCH (a:Knowledge), (b:Knowledge) "
            "WHERE a.node_id < b.node_id "
            "AND a.category = b.category AND a.category IS NOT NULL "
            "AND a.tags IS NOT NULL AND b.tags IS NOT NULL "
            "AND size([t IN split(a.tags, ', ') WHERE b.tags CONTAINS t AND size(t) > 3]) >= 4 "
            "WITH a, b, "
            "  size([(a)-[]-() | 1]) AS a_degree, "
            "  size([(b)-[]-() | 1]) AS b_degree, "
            "  size([(:CouplingEvent)-[:ACTIVATED]->(a) | 1]) AS a_coupling, "
            "  size([(:CouplingEvent)-[:ACTIVATED]->(b) | 1]) AS b_coupling "
            "WITH a, b, "
            "  a_degree + a_coupling AS a_score, "
            "  b_degree + b_coupling AS b_score "
            "WITH CASE WHEN a_score < b_score THEN a "
            "          WHEN b_score < a_score THEN b "
            "          ELSE b END AS loser "
            "SET loser.confidence_lowered_by = 'integrity-contradiction' "
            "RETURN count(loser) AS contradictions_resolved"
        ),
        "cost": 0,
    },

    # Integrity Rule 6: CouplingEvent decay (7 days)
    {
        "node_id": "pipeline-digest-coupling-decay",
        "name": "coupling-decay",
        "phase": "digest",
        "order": 7,
        "stage_type": "cypher_template",
        "description": "Prune CouplingEvent nodes older than 7 days",
        "cypher": (
            "MATCH (e:CouplingEvent) WHERE e.timestamp < '$CUTOFF_7D' "
            "WITH e LIMIT 500 DETACH DELETE e RETURN count(e) AS pruned"
        ),
        "cost": 0,
    },

    # Integrity Rule 6b: Trace decay (2 days)
    {
        "node_id": "pipeline-digest-trace-decay",
        "name": "trace-decay",
        "phase": "digest",
        "order": 8,
        "stage_type": "cypher_template",
        "description": "Prune Trace nodes older than 2 days",
        "cypher": (
            "MATCH (t:Trace) WHERE t.timestamp < '$CUTOFF_2D' "
            "WITH t LIMIT 500 DETACH DELETE t RETURN count(t) AS pruned"
        ),
        "cost": 0,
    },

    # Integrity Rule 6c: Commit decay (14 days)
    {
        "node_id": "pipeline-digest-commit-decay",
        "name": "commit-decay",
        "phase": "digest",
        "order": 9,
        "stage_type": "cypher_template",
        "description": "Prune Commit nodes older than 14 days",
        "cypher": (
            "MATCH (c:Commit) WHERE c.timestamp < '$CUTOFF_14D' "
            "WITH c LIMIT 500 DETACH DELETE c RETURN count(c) AS pruned"
        ),
        "cost": 0,
    },

    # Integrity Rule 7d: WorkItem sync from closed issues
    {
        "node_id": "pipeline-digest-workitem-sync",
        "name": "workitem-sync",
        "phase": "digest",
        "order": 10,
        "stage_type": "cypher",
        "description": "Sync WorkItem status from closed GitHub issues",
        "cypher": (
            "MATCH (w:WorkItem)-[:TRACKS]->(i:Issue) "
            "WHERE i.state = 'closed' AND w.status <> 'done' "
            "SET w.status = 'done' "
            "RETURN w.label AS closed_item, w.issue_number AS issue"
        ),
        "cost": 0,
    },

    # Integrity Rule 8: Confidence decay (single-source)
    {
        "node_id": "pipeline-digest-confidence-decay",
        "name": "confidence-decay",
        "phase": "digest",
        "order": 11,
        "stage_type": "cypher",
        "description": "Cap single-source Knowledge entries to low confidence",
        "cypher": (
            "MATCH (k:Knowledge) "
            "WHERE coalesce(k.evidence_count, 0) <= 1 "
            "AND k.confidence IN ['high', 'medium'] "
            "SET k.confidence = 'low', k.confidence_capped_reason = 'single-source' "
            "RETURN count(k) AS capped"
        ),
        "cost": 0,
    },

    # Convergence detection — region convergence
    {
        "node_id": "pipeline-digest-convergence",
        "name": "convergence-detect",
        "phase": "digest",
        "order": 12,
        "stage_type": "cypher",
        "description": "Detect cross-person intent convergence by graph region",
        "cypher": (
            "MATCH (i:Intent) "
            "WITH i.graph_region AS region, "
            "  collect(DISTINCT i.person) AS people, "
            "  count(i) AS intent_count, "
            "  sum(i.recurrence_count) AS total_recurrence "
            "WHERE intent_count >= 3 AND size(people) >= 2 "
            "RETURN region, people, intent_count, total_recurrence "
            "ORDER BY total_recurrence DESC"
        ),
        "cost": 0,
    },

    # ============================================================
    # EXCRETE — the system acts, proposes, reports
    # ============================================================

    # Dream: Sense — missing triangles
    {
        "node_id": "pipeline-excrete-sense-triangles",
        "name": "sense-triangles",
        "phase": "excrete",
        "order": 13,
        "stage_type": "cypher",
        "description": "Find Knowledge nodes that share neighbors but have no direct edge",
        "cypher": (
            "MATCH (a:Knowledge)-[]-(bridge)-[]-(c:Knowledge) "
            "WHERE a.node_id < c.node_id AND NOT (a)-[]-(c) "
            "WITH a, c, count(bridge) AS shared, "
            "  collect(bridge.label)[0] AS bridge_label "
            "ORDER BY shared DESC LIMIT 10 "
            "RETURN a.node_id AS a_id, a.label AS a_label, "
            "  c.node_id AS c_id, c.label AS c_label, shared, bridge_label"
        ),
        "cost": 0,
    },

    # Dream: Heal — close triangles
    {
        "node_id": "pipeline-excrete-heal-triangles",
        "name": "heal-triangles",
        "phase": "excrete",
        "order": 14,
        "stage_type": "cypher",
        "description": "Close top missing triangles with INFERRED edges",
        "cypher": (
            "MATCH (a:Knowledge)-[]-(bridge)-[]-(c:Knowledge) "
            "WHERE a.node_id < c.node_id AND NOT (a)-[]-(c) "
            "WITH a, c, count(bridge) AS shared "
            "ORDER BY shared DESC LIMIT 10 "
            "MERGE (a)-[r:CONCEPTUALLY_RELATED_TO]->(c) "
            "SET r.confidence = 'INFERRED', r.confidence_score = 0.4, "
            "r.source = 'dream-round' "
            "RETURN count(r) AS triangles_closed"
        ),
        "cost": 0,
    },

    # Dream: Heal — prune orphans
    {
        "node_id": "pipeline-excrete-prune-orphans",
        "name": "prune-orphans",
        "phase": "excrete",
        "order": 15,
        "stage_type": "cypher",
        "description": "Delete transient nodes with zero edges",
        "cypher": (
            "MATCH (n) WHERE NOT (n)-[]-() "
            "AND n.file_type IN ['concept', 'demand', 'intent', 'coupling', 'trace', 'commit'] "
            "DETACH DELETE n RETURN count(n) AS orphans_pruned"
        ),
        "cost": 0,
    },

    # Dream: Propose — surface unblocked WorkItems
    {
        "node_id": "pipeline-excrete-propose-workitems",
        "name": "propose-workitems",
        "phase": "excrete",
        "order": 16,
        "stage_type": "cypher_template",
        "description": "Create ActionProposal nodes for unblocked WorkItems",
        "cypher": (
            "MATCH (w:WorkItem {status: 'open'}) "
            "OPTIONAL MATCH (w)-[:DEPENDS_ON]->(dep:WorkItem) "
            "WHERE dep.status <> 'done' "
            "WITH w, count(dep) AS blocking "
            "WHERE blocking = 0 "
            "MERGE (p:ActionProposal {node_id: 'proposal-workitem-' + toString(w.issue_number) + '-$TODAY'}) "
            "SET p.label = 'Unblocked: ' + w.label, "
            "p.action = 'WorkItem ready for execution', "
            "p.person = 'team', "
            "p.proposed_at = '$NOW', "
            "p.status = 'proposed', "
            "p.source = 'pipeline', "
            "p.file_type = 'action-proposal' "
            "RETURN count(p) AS proposals"
        ),
        "cost": 0,
    },

    # Dream: Propose — purpose chain walk
    {
        "node_id": "pipeline-excrete-propose-purpose",
        "name": "propose-purpose",
        "phase": "excrete",
        "order": 17,
        "stage_type": "cypher",
        "description": "Walk Purpose → Pull → Convergence → Intent to find actionable gaps",
        "cypher": (
            "MATCH (pur:Purpose {active: true})-[:DRIVEN_BY]->(gp:GravitationalPull)"
            "-[:PULLS_TOWARD]->(c:Convergence)<-[:CONVERGES_TO]-(i:Intent) "
            "WHERE i.recurrence_count >= 3 "
            "OPTIONAL MATCH (k:Knowledge) "
            "  WHERE k.community = i.community AND k.confidence IN ['high', 'medium'] "
            "WITH i, k, gp, c LIMIT 10 "
            "RETURN i.node_id AS intent, i.label AS intent_label, i.person, "
            "  i.recurrence_count AS recurrence, "
            "  k.label AS resolution, gp.label AS pull, c.label AS convergence"
        ),
        "cost": 0,
    },

    # Dream: Learn — measure system effectiveness
    {
        "node_id": "pipeline-excrete-measure",
        "name": "measure",
        "phase": "excrete",
        "order": 18,
        "stage_type": "cypher_template",
        "description": "Record Measurement node: dream edge activations, concept activation, proposal execution",
        "cypher": (
            "MATCH ()-[r:CONCEPTUALLY_RELATED_TO]->() WHERE r.source = 'dream-round' "
            "WITH startNode(r) AS a, endNode(r) AS b "
            "OPTIONAL MATCH (t:Trace)-[:TOUCHES]->(a) "
            "OPTIONAL MATCH (t2:Trace)-[:TOUCHES]->(b) "
            "WITH count(t) + count(t2) AS activations "
            "MERGE (m:Measurement {node_id: 'meas-$TODAY'}) "
            "SET m.label = 'Measurement $TODAY', "
            "m.dream_edge_activations = activations, "
            "m.timestamp = '$NOW', "
            "m.file_type = 'measurement' "
            "RETURN activations AS dream_edge_activations"
        ),
        "cost": 0,
    },

    # Health check — graph stats
    {
        "node_id": "pipeline-excrete-health",
        "name": "health-check",
        "phase": "excrete",
        "order": 19,
        "stage_type": "cypher",
        "description": "Count nodes, edges, types — the system's vital signs",
        "cypher": (
            "MATCH (n) WITH count(n) AS nodes "
            "MATCH ()-[r]->() WITH nodes, count(r) AS edges "
            "RETURN nodes, edges"
        ),
        "cost": 0,
    },
]

# ================================================================
# TEST CASES — each validates a pipeline stage
# ================================================================

TESTS = [
    {
        "node_id": "test-pipeline-no-orphan-traces",
        "label": "No orphan Trace nodes after pipeline",
        "validates": "pipeline-excrete-prune-orphans",
        "cypher": (
            "MATCH (t:Trace) WHERE NOT (t)-[]-() "
            "RETURN count(t) = 0 AS passed"
        ),
    },
    {
        "node_id": "test-pipeline-no-stale-inferred",
        "label": "No stale INFERRED edges after pipeline",
        "validates": "pipeline-digest-stale-edges",
        "cypher": (
            "MATCH (a)-[r:CONCEPTUALLY_RELATED_TO]->(b) "
            "WHERE r.confidence = 'INFERRED' "
            "AND NOT (:Trace)-[:TOUCHES]->(a) AND NOT (:Trace)-[:TOUCHES]->(b) "
            "AND NOT (:CouplingEvent)-[:ACTIVATED]->(a) AND NOT (:CouplingEvent)-[:ACTIVATED]->(b) "
            "RETURN count(r) = 0 AS passed"
        ),
    },
    {
        "node_id": "test-pipeline-workitems-synced",
        "label": "Closed issues have done WorkItems",
        "validates": "pipeline-digest-workitem-sync",
        "cypher": (
            "MATCH (w:WorkItem)-[:TRACKS]->(i:Issue) "
            "WHERE i.state = 'closed' AND w.status <> 'done' "
            "RETURN count(w) = 0 AS passed"
        ),
    },
    {
        "node_id": "test-pipeline-health-nonzero",
        "label": "Graph has nodes and edges",
        "validates": "pipeline-excrete-health",
        "cypher": (
            "MATCH (n) WITH count(n) AS nodes "
            "MATCH ()-[r]->() WITH nodes, count(r) AS edges "
            "RETURN nodes > 0 AND edges > 0 AS passed"
        ),
    },
    {
        "node_id": "test-pipeline-single-source-capped",
        "label": "No single-source entries with high confidence",
        "validates": "pipeline-digest-confidence-decay",
        "cypher": (
            "MATCH (k:Knowledge) "
            "WHERE coalesce(k.evidence_count, 0) <= 1 "
            "AND k.confidence IN ['high', 'medium'] "
            "RETURN count(k) = 0 AS passed"
        ),
    },
]


def seed_pipeline(graph):
    """Create PipelineStage nodes, FLOWS_TO edges, and TestCase nodes."""
    ts = datetime.now(timezone.utc).isoformat()
    created = 0

    print("[seed-pipeline] Creating PipelineStage nodes...")

    for stage in STAGES:
        # Use double-quoted strings for cypher/description (they contain single quotes)
        cypher_val = f', s.cypher = "{esc_dq(stage["cypher"])}"' if stage["cypher"] else ""
        script_val = f', s.script_path = "{esc_dq(stage["script_path"])}"' if stage.get("script_path") else ""

        q = (
            f"MERGE (s:PipelineStage {{node_id: '{esc(stage['node_id'])}'}}) "
            f"SET s.name = '{esc(stage['name'])}', "
            f"s.phase = '{esc(stage['phase'])}', "
            f"s.stage_order = {stage['order']}, "
            f"s.stage_type = '{esc(stage['stage_type'])}', "
            f"s.description = \"{esc_dq(stage['description'])}\", "
            f"s.cost = {stage['cost']}, "
            f"s.enabled = true, "
            f"s.seeded_at = '{esc(ts)}'"
            f"{cypher_val}{script_val}"
        )
        try:
            graph.query(q)
            created += 1
        except Exception as e:
            print(f"  FAILED {stage['node_id']}: {e}")

    print(f"  {created}/{len(STAGES)} stages created")

    # Create FLOWS_TO edges (ordered by stage_order)
    print("[seed-pipeline] Wiring FLOWS_TO edges...")
    edges = 0
    sorted_stages = sorted(STAGES, key=lambda s: s["order"])
    for i in range(len(sorted_stages) - 1):
        a = sorted_stages[i]
        b = sorted_stages[i + 1]
        try:
            graph.query(
                f"MATCH (a:PipelineStage {{node_id: '{esc(a['node_id'])}'}}), "
                f"(b:PipelineStage {{node_id: '{esc(b['node_id'])}'}}) "
                f"MERGE (a)-[:FLOWS_TO]->(b)"
            )
            edges += 1
        except Exception as e:
            print(f"  FAILED edge {a['name']} → {b['name']}: {e}")

    print(f"  {edges} FLOWS_TO edges created")

    # Create phase grouping edges
    print("[seed-pipeline] Creating phase markers...")
    for phase in ["ingest", "digest", "excrete"]:
        phase_stages = [s for s in STAGES if s["phase"] == phase]
        if phase_stages:
            try:
                graph.query(
                    f"MERGE (ph:PipelinePhase {{node_id: 'phase-{phase}'}}) "
                    f"SET ph.name = '{phase}', "
                    f"ph.label = '{phase.upper()}: "
                    f"{'perceive' if phase == 'ingest' else 'connect' if phase == 'digest' else 'act'}'"
                )
                for s in phase_stages:
                    graph.query(
                        f"MATCH (ph:PipelinePhase {{node_id: 'phase-{phase}'}}), "
                        f"(s:PipelineStage {{node_id: '{esc(s['node_id'])}'}}) "
                        f"MERGE (ph)-[:CONTAINS]->(s)"
                    )
            except Exception as e:
                print(f"  FAILED phase {phase}: {e}")

    # Create TestCase nodes
    print("[seed-pipeline] Creating TestCase nodes...")
    tests = 0
    for test in TESTS:
        try:
            graph.query(
                f"MERGE (t:TestCase {{node_id: '{esc(test['node_id'])}'}}) "
                f"SET t.label = \"{esc_dq(test['label'])}\", "
                f"t.cypher = \"{esc_dq(test['cypher'])}\", "
                f"t.source = 'pipeline', "
                f"t.last_result = 'pending'"
            )
            graph.query(
                f"MATCH (t:TestCase {{node_id: '{esc(test['node_id'])}'}}), "
                f"(s:PipelineStage {{node_id: '{esc(test['validates'])}'}}) "
                f"MERGE (t)-[:VALIDATES]->(s)"
            )
            tests += 1
        except Exception as e:
            print(f"  FAILED test {test['node_id']}: {e}")

    print(f"  {tests}/{len(TESTS)} tests created")

    # Link pipeline to Invariant (the pipeline upholds the cypher-native principle)
    try:
        graph.query(
            "MERGE (inv:Invariant {node_id: 'invariant-pipeline'}) "
            "SET inv.label = 'Cypher-Native Pipeline', "
            "inv.description = 'The system does not read. It ingests. All pipeline intelligence is Cypher. Python is I/O glue. Zero LLM cost.', "
            "inv.status = 'active', "
            "inv.number = 9"
        )
        # Link all stages to the invariant
        graph.query(
            "MATCH (s:PipelineStage), (inv:Invariant {node_id: 'invariant-pipeline'}) "
            "MERGE (s)-[:UPHOLDS]->(inv)"
        )
        print("[seed-pipeline] Linked pipeline to Invariant 9: Cypher-Native Pipeline")
    except Exception as e:
        print(f"  FAILED invariant: {e}")

    return created, edges, tests


def main():
    print("[seed-pipeline] Seeding Cypher-native pipeline into graph...")
    print(f"[seed-pipeline] Graph: {FALKORDB_HOST}:{FALKORDB_PORT}")

    try:
        graph = get_graph()
    except Exception as e:
        print(f"FalkorDB unavailable: {e}")
        sys.exit(1)

    stages, edges, tests = seed_pipeline(graph)

    # Verify
    try:
        r = graph.query(
            "MATCH path = (s:PipelineStage)-[:FLOWS_TO*]->(e:PipelineStage) "
            "WHERE NOT ()-[:FLOWS_TO]->(s) "
            "RETURN length(path) + 1 AS total_stages"
        )
        chain_length = r.result_set[0][0] if r.result_set else 0
        print(f"\n[seed-pipeline] Pipeline chain: {chain_length} stages")
    except Exception:
        pass

    try:
        r = graph.query(
            "MATCH (t:TestCase)-[:VALIDATES]->(s:PipelineStage) "
            "RETURN count(t)"
        )
        test_count = r.result_set[0][0] if r.result_set else 0
        print(f"[seed-pipeline] Tests wired: {test_count}")
    except Exception:
        pass

    print(f"\n[seed-pipeline] Done. The pipeline is now graph topology.")
    print(f"[seed-pipeline] Query it: MATCH (s:PipelineStage)-[:FLOWS_TO]->(next) RETURN s.name, next.name")


if __name__ == "__main__":
    main()
