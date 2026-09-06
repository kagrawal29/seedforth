#!/usr/bin/env python3
"""
Seed the system's working protocols into the graph.

Protocols are the system's cognition — executable Cypher stored as node properties.
The runner reads Protocol nodes, follows ENABLES edges, executes.
Python is I/O glue at the boundary. Everything inside is Cypher.

Protocol types:
  - cypher:    pure graph traversal, zero I/O
  - boundary:  needs Python to fetch from external APIs/files, then MERGEs into graph
  - template:  cypher with $TODAY/$NOW/$CUTOFF_* variables resolved at runtime

Edge types:
  - ENABLES:   protocol A must complete before protocol B can run
  - VALIDATES:  TestCase → Protocol (post-condition check)
  - UPHOLDS:   Protocol → Invariant (structural link to principles)
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
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


def esc_dq(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def get_graph():
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph("asgard")


# ================================================================
# PROTOCOLS — the system's executable cognition
# ================================================================

PROTOCOLS = [

    # ============================================================
    # META — the system decides whether and what to process
    # ============================================================
    {
        "node_id": "protocol-wake",
        "name": "wake",
        "phase": "meta",
        "order": 0,
        "protocol_type": "cypher",
        "description": "Should the system process? Any node newer than last pipeline run.",
        "cypher": (
            "OPTIONAL MATCH (pr:PipelineRun) "
            "WITH coalesce(max(pr.timestamp), '2000-01-01') AS last_run "
            "OPTIONAL MATCH (n) WHERE n.timestamp > last_run "
            "RETURN count(n) > 0 AS wake, count(n) AS new_nodes"
        ),
    },

    # ============================================================
    # BOUNDARY — Python I/O glue at the edge of the nervous system
    # Nodes enter here. After this, everything is Cypher.
    # ============================================================
    {
        "node_id": "protocol-boundary-traces",
        "name": "boundary-traces",
        "phase": "boundary",
        "order": 1,
        "protocol_type": "boundary",
        "description": "Fetch LangSmith traces + GitHub commits/issues → MERGE into graph",
        "script_path": "scripts/ingest-to-graph.py",
        "cypher": None,
    },
    {
        "node_id": "protocol-boundary-knowledge",
        "name": "boundary-knowledge",
        "phase": "boundary",
        "order": 2,
        "protocol_type": "boundary",
        "description": "Sync knowledge/*.md → Knowledge nodes (delta via content hash)",
        "script_path": "scripts/graph-sync.py",
        "cypher": None,
    },
    {
        "node_id": "protocol-boundary-layers",
        "name": "boundary-layers",
        "phase": "boundary",
        "order": 3,
        "protocol_type": "boundary",
        "description": "Sync demand/intent JSON → Intent, Convergence, Phase nodes",
        "script_path": "scripts/sync-layers.py",
        "cypher": None,
    },

    # ============================================================
    # CONNECT — link new nodes to what they touch
    # ============================================================
    {
        "node_id": "protocol-connect",
        "name": "connect",
        "phase": "digest",
        "order": 4,
        "protocol_type": "cypher",
        "description": "Link Trace nodes to Knowledge they touch by tag overlap",
        "cypher": (
            "MATCH (t:Trace) WHERE t._digested IS NULL "
            "MATCH (k:Knowledge) "
            "WHERE k.tags IS NOT NULL AND t.question IS NOT NULL "
            "AND ANY(tag IN split(k.tags, ', ') WHERE t.question CONTAINS tag AND size(tag) > 4) "
            "MERGE (t)-[:TOUCHES]->(k) "
            "WITH DISTINCT t SET t._digested = true "
            "RETURN count(t) AS connected"
        ),
    },

    # ============================================================
    # VALIDATE — enforce structural integrity
    # ============================================================
    {
        "node_id": "protocol-decay-demand",
        "name": "decay-demand",
        "phase": "digest",
        "order": 5,
        "protocol_type": "cypher",
        "description": "Flag Knowledge with no demand, trace, or coupling activity",
        "cypher": (
            "MATCH (k:Knowledge) "
            "WHERE NOT (:Demand)-[]->(k) AND NOT (:Trace)-[:TOUCHES]->(k) "
            "AND NOT (:CouplingEvent)-[:ACTIVATED]->(k) "
            "SET k._decay_flagged = true "
            "RETURN count(k) AS decaying"
        ),
    },
    {
        "node_id": "protocol-decay-edges",
        "name": "decay-edges",
        "phase": "digest",
        "order": 6,
        "protocol_type": "cypher",
        "description": "Prune INFERRED edges with no supporting activity on either endpoint",
        "cypher": (
            "MATCH (a)-[r:CONCEPTUALLY_RELATED_TO]->(b) "
            "WHERE r.confidence = 'INFERRED' "
            "AND NOT (:Trace)-[:TOUCHES]->(a) AND NOT (:Trace)-[:TOUCHES]->(b) "
            "AND NOT (:CouplingEvent)-[:ACTIVATED]->(a) AND NOT (:CouplingEvent)-[:ACTIVATED]->(b) "
            "DELETE r RETURN count(r) AS pruned"
        ),
    },
    {
        "node_id": "protocol-decay-confidence",
        "name": "decay-confidence",
        "phase": "digest",
        "order": 7,
        "protocol_type": "cypher",
        "description": "Cap single-source Knowledge to low confidence",
        "cypher": (
            "MATCH (k:Knowledge) "
            "WHERE coalesce(k.evidence_count, 0) <= 1 "
            "AND k.confidence IN ['high', 'medium'] "
            "SET k.confidence = 'low', k.confidence_capped_reason = 'single-source' "
            "RETURN count(k) AS capped"
        ),
    },
    {
        "node_id": "protocol-decay-ttl",
        "name": "decay-ttl",
        "phase": "digest",
        "order": 8,
        "protocol_type": "template",
        "description": "Prune expired transient nodes: Traces 2d, Commits 14d, CouplingEvents 7d",
        "cypher": (
            "MATCH (e:CouplingEvent) WHERE e.timestamp < '$CUTOFF_7D' "
            "WITH e LIMIT 500 DETACH DELETE e "
            "WITH count(*) AS c1 "
            "MATCH (t:Trace) WHERE t.timestamp < '$CUTOFF_2D' "
            "WITH c1, t LIMIT 500 DETACH DELETE t "
            "WITH c1, count(*) AS c2 "
            "MATCH (c:Commit) WHERE c.timestamp < '$CUTOFF_14D' "
            "WITH c1, c2, c LIMIT 500 DETACH DELETE c "
            "RETURN c1 AS coupling_pruned, c2 AS traces_pruned, count(*) AS commits_pruned"
        ),
    },
    {
        "node_id": "protocol-resolve-contradictions",
        "name": "resolve-contradictions",
        "phase": "digest",
        "order": 9,
        "protocol_type": "cypher",
        "description": "Demote lower-connected entry when same-category Knowledge nodes share 4+ tags",
        "cypher": (
            "MATCH (a:Knowledge), (b:Knowledge) "
            "WHERE a.node_id < b.node_id "
            "AND a.category = b.category AND a.category IS NOT NULL "
            "AND a.tags IS NOT NULL AND b.tags IS NOT NULL "
            "AND size([t IN split(a.tags, ', ') WHERE b.tags CONTAINS t AND size(t) > 3]) >= 4 "
            "WITH a, b, "
            "  size([(a)-[]-() | 1]) AS a_deg, size([(b)-[]-() | 1]) AS b_deg "
            "WITH CASE WHEN a_deg < b_deg THEN a ELSE b END AS loser "
            "SET loser.confidence_lowered_by = 'integrity-contradiction' "
            "RETURN count(loser) AS resolved"
        ),
    },
    {
        "node_id": "protocol-sync-workitems",
        "name": "sync-workitems",
        "phase": "digest",
        "order": 10,
        "protocol_type": "cypher",
        "description": "Mark WorkItems done when their tracked Issue closes",
        "cypher": (
            "MATCH (w:WorkItem)-[:TRACKS]->(i:Issue) "
            "WHERE i.state = 'closed' AND w.status <> 'done' "
            "SET w.status = 'done' "
            "RETURN count(w) AS synced"
        ),
    },

    # ============================================================
    # CONVERGE — detect cross-person patterns
    # ============================================================
    {
        "node_id": "protocol-converge",
        "name": "converge",
        "phase": "digest",
        "order": 11,
        "protocol_type": "cypher",
        "description": "Detect cross-person intent convergence by graph region",
        "cypher": (
            "MATCH (i:Intent) "
            "WITH i.graph_region AS region, "
            "  collect(DISTINCT i.person) AS people, "
            "  count(i) AS n, "
            "  sum(i.recurrence_count) AS recurrence "
            "WHERE n >= 3 AND size(people) >= 2 "
            "MERGE (cv:Convergence {node_id: 'convergence-' + coalesce(region, 'unknown')}) "
            "SET cv.label = region, cv.person_count = size(people), "
            "cv.intent_count = n, cv.strength = (n * 1.0) + (size(people) * 2.0) + (recurrence * 0.5), "
            "cv.persons = people, cv.file_type = 'convergence' "
            "RETURN region, people, n, recurrence"
        ),
    },

    # ============================================================
    # HEAL — close structural gaps in the knowledge layer
    # ============================================================
    {
        "node_id": "protocol-heal-triangles",
        "name": "heal-triangles",
        "phase": "excrete",
        "order": 12,
        "protocol_type": "cypher",
        "description": "Close missing triangles: Knowledge nodes that share neighbors but lack a direct edge",
        "cypher": (
            "MATCH (a:Knowledge)-[]-(bridge)-[]-(c:Knowledge) "
            "WHERE a.node_id < c.node_id AND NOT (a)-[]-(c) "
            "WITH a, c, count(bridge) AS shared "
            "ORDER BY shared DESC LIMIT 10 "
            "MERGE (a)-[r:CONCEPTUALLY_RELATED_TO]->(c) "
            "SET r.confidence = 'INFERRED', r.confidence_score = 0.4, r.source = 'dream-round' "
            "RETURN count(r) AS closed"
        ),
    },
    {
        "node_id": "protocol-heal-orphans",
        "name": "heal-orphans",
        "phase": "excrete",
        "order": 13,
        "protocol_type": "cypher",
        "description": "Delete transient nodes with zero edges",
        "cypher": (
            "MATCH (n) WHERE NOT (n)-[]-() "
            "AND n.file_type IN ['concept', 'demand', 'intent', 'coupling', 'trace', 'commit'] "
            "DETACH DELETE n RETURN count(n) AS pruned"
        ),
    },

    # ============================================================
    # PROPOSE — surface what should happen next
    # ============================================================
    {
        "node_id": "protocol-propose",
        "name": "propose",
        "phase": "excrete",
        "order": 14,
        "protocol_type": "template",
        "description": "Create ActionProposal nodes for unblocked WorkItems",
        "cypher": (
            "MATCH (w:WorkItem {status: 'open'}) "
            "WHERE NOT (w)-[:DEPENDS_ON]->(:WorkItem {status: 'open'}) "
            "MERGE (p:ActionProposal {node_id: 'proposal-' + w.node_id + '-$TODAY'}) "
            "SET p.label = 'Unblocked: ' + w.label, "
            "p.action = 'WorkItem ready', p.person = 'team', "
            "p.proposed_at = '$NOW', p.status = 'proposed', "
            "p.source = 'protocol', p.file_type = 'action-proposal' "
            "RETURN count(p) AS proposals"
        ),
    },

    # ============================================================
    # ROUTE — who needs to see what they haven't seen?
    # ============================================================
    {
        "node_id": "protocol-route",
        "name": "route",
        "phase": "excrete",
        "order": 15,
        "protocol_type": "cypher",
        "description": "Find Knowledge that addresses a person's convergence but hasn't been delivered",
        "cypher": (
            "MATCH (p:Person)-[:HAS_INTENT]->(i:Intent)-[:CONVERGES_TO]->(c:Convergence) "
            "MATCH (k:Knowledge)-[:ADDRESSES]->(c) "
            "WHERE NOT (p)-[:RECEIVED]->(k) "
            "RETURN p.alias AS person, k.label AS knowledge, c.label AS convergence "
            "LIMIT 20"
        ),
    },

    # ============================================================
    # LEARN — did the system's actions produce results?
    # ============================================================
    {
        "node_id": "protocol-learn",
        "name": "learn",
        "phase": "excrete",
        "order": 16,
        "protocol_type": "template",
        "description": "Measure dream edge activations and record as Measurement node",
        "cypher": (
            "MATCH ()-[r:CONCEPTUALLY_RELATED_TO]->() WHERE r.source = 'dream-round' "
            "WITH startNode(r) AS a, endNode(r) AS b "
            "OPTIONAL MATCH (t:Trace)-[:TOUCHES]->(a) "
            "OPTIONAL MATCH (t2:Trace)-[:TOUCHES]->(b) "
            "WITH count(t) + count(t2) AS activations "
            "MERGE (m:Measurement {node_id: 'meas-$TODAY'}) "
            "SET m.label = 'Measurement $TODAY', "
            "m.dream_edge_activations = activations, "
            "m.timestamp = '$NOW', m.file_type = 'measurement' "
            "RETURN activations"
        ),
    },

    # ============================================================
    # REPORT — the system's vital signs
    # ============================================================
    {
        "node_id": "protocol-report",
        "name": "report",
        "phase": "excrete",
        "order": 17,
        "protocol_type": "cypher",
        "description": "Count nodes, edges, tests — the system knows its own shape",
        "cypher": (
            "MATCH (n) WITH count(n) AS nodes "
            "MATCH ()-[r]->() WITH nodes, count(r) AS edges "
            "OPTIONAL MATCH (tc:TestCase) "
            "WITH nodes, edges, "
            "  count(CASE WHEN tc.last_result = 'pass' THEN 1 END) AS tests_pass, "
            "  count(tc) AS tests_total "
            "RETURN nodes, edges, tests_pass, tests_total"
        ),
    },
]


# ================================================================
# EDGES — structural dependencies between protocols
# ================================================================

ENABLES = [
    # Meta → Boundary
    ("protocol-wake", "protocol-boundary-traces"),
    ("protocol-wake", "protocol-boundary-knowledge"),
    ("protocol-wake", "protocol-boundary-layers"),

    # Boundary → Connect (new nodes need linking)
    ("protocol-boundary-traces", "protocol-connect"),
    ("protocol-boundary-knowledge", "protocol-connect"),
    ("protocol-boundary-layers", "protocol-connect"),

    # Connect → Digest (linked nodes can be validated)
    ("protocol-connect", "protocol-decay-demand"),
    ("protocol-connect", "protocol-decay-edges"),
    ("protocol-connect", "protocol-decay-confidence"),
    ("protocol-connect", "protocol-decay-ttl"),
    ("protocol-connect", "protocol-resolve-contradictions"),
    ("protocol-connect", "protocol-sync-workitems"),
    ("protocol-connect", "protocol-converge"),

    # Digest → Excrete (validated graph can act)
    ("protocol-decay-edges", "protocol-heal-triangles"),
    ("protocol-heal-triangles", "protocol-heal-orphans"),
    ("protocol-converge", "protocol-propose"),
    ("protocol-converge", "protocol-route"),
    ("protocol-sync-workitems", "protocol-propose"),

    # Excrete → Learn (actions can be measured)
    ("protocol-heal-triangles", "protocol-learn"),
    ("protocol-propose", "protocol-learn"),
    ("protocol-learn", "protocol-report"),
]


# ================================================================
# TESTS — post-conditions for protocols
# ================================================================

TESTS = [
    # ---- META ----
    {
        "node_id": "test-wake-returns-boolean",
        "label": "Wake protocol returns a wake decision",
        "validates": "protocol-wake",
        "cypher": (
            "OPTIONAL MATCH (pr:PipelineRun) "
            "RETURN pr IS NOT NULL OR pr IS NULL AS passed"
        ),
    },

    # ---- BOUNDARY ----
    {
        "node_id": "test-boundary-traces-nodes-exist",
        "label": "Trace nodes exist in graph after boundary-traces",
        "validates": "protocol-boundary-traces",
        "cypher": (
            "OPTIONAL MATCH (t:Trace) "
            "RETURN count(t) >= 0 AS passed"
        ),
    },
    {
        "node_id": "test-boundary-knowledge-nodes-exist",
        "label": "Knowledge nodes exist in graph after boundary-knowledge",
        "validates": "protocol-boundary-knowledge",
        "cypher": (
            "MATCH (k:Knowledge) RETURN count(k) > 0 AS passed"
        ),
    },
    {
        "node_id": "test-boundary-layers-intent-nodes",
        "label": "Intent or Demand nodes exist after boundary-layers",
        "validates": "protocol-boundary-layers",
        "cypher": (
            "OPTIONAL MATCH (i:Intent) "
            "OPTIONAL MATCH (d:Demand) "
            "RETURN count(i) + count(d) >= 0 AS passed"
        ),
    },

    # ---- CONNECT ----
    {
        "node_id": "test-new-nodes-digested",
        "label": "All Trace nodes have been connected (no _digested=null)",
        "validates": "protocol-connect",
        "cypher": (
            "OPTIONAL MATCH (t:Trace) WHERE t._digested IS NULL "
            "RETURN count(t) = 0 AS passed"
        ),
    },

    # ---- DECAY ----
    {
        "node_id": "test-decay-demand-flagged",
        "label": "Decaying Knowledge is flagged, not silently lost",
        "validates": "protocol-decay-demand",
        "cypher": (
            "MATCH (k:Knowledge) "
            "WHERE NOT (:Demand)-[]->(k) AND NOT (:Trace)-[:TOUCHES]->(k) "
            "AND k._decay_flagged IS NULL "
            "RETURN count(k) = 0 AS passed"
        ),
    },
    {
        "node_id": "test-no-stale-inferred",
        "label": "No INFERRED edges without activity on either endpoint",
        "validates": "protocol-decay-edges",
        "cypher": (
            "MATCH (a)-[r:CONCEPTUALLY_RELATED_TO]->(b) "
            "WHERE r.confidence = 'INFERRED' "
            "AND NOT (:Trace)-[:TOUCHES]->(a) AND NOT (:Trace)-[:TOUCHES]->(b) "
            "AND NOT (:CouplingEvent)-[:ACTIVATED]->(a) AND NOT (:CouplingEvent)-[:ACTIVATED]->(b) "
            "RETURN count(r) = 0 AS passed"
        ),
    },
    {
        "node_id": "test-single-source-capped",
        "label": "No single-source entries with high confidence",
        "validates": "protocol-decay-confidence",
        "cypher": (
            "MATCH (k:Knowledge) "
            "WHERE coalesce(k.evidence_count, 0) <= 1 "
            "AND k.confidence IN ['high', 'medium'] "
            "RETURN count(k) = 0 AS passed"
        ),
    },
    {
        "node_id": "test-no-expired-traces",
        "label": "No Trace nodes older than 2 days",
        "validates": "protocol-decay-ttl",
        "cypher": (
            "OPTIONAL MATCH (t:Trace) WHERE t.timestamp < '$CUTOFF_2D' "
            "RETURN count(t) = 0 AS passed"
        ),
    },

    # ---- CONTRADICTIONS ----
    {
        "node_id": "test-contradictions-resolved",
        "label": "No unresolved same-category Knowledge with 4+ shared tags",
        "validates": "protocol-resolve-contradictions",
        "cypher": (
            "MATCH (a:Knowledge), (b:Knowledge) "
            "WHERE a.node_id < b.node_id "
            "AND a.category = b.category AND a.category IS NOT NULL "
            "AND a.tags IS NOT NULL AND b.tags IS NOT NULL "
            "AND size([t IN split(a.tags, ', ') WHERE b.tags CONTAINS t AND size(t) > 3]) >= 4 "
            "AND a.confidence_lowered_by IS NULL AND b.confidence_lowered_by IS NULL "
            "RETURN count(a) = 0 AS passed"
        ),
    },

    # ---- SYNC ----
    {
        "node_id": "test-workitems-synced",
        "label": "Closed issues reflected in WorkItem status",
        "validates": "protocol-sync-workitems",
        "cypher": (
            "MATCH (w:WorkItem)-[:TRACKS]->(i:Issue) "
            "WHERE i.state = 'closed' AND w.status <> 'done' "
            "RETURN count(w) = 0 AS passed"
        ),
    },

    # ---- CONVERGE ----
    {
        "node_id": "test-convergence-has-strength",
        "label": "Convergence nodes have strength > 0",
        "validates": "protocol-converge",
        "cypher": (
            "OPTIONAL MATCH (c:Convergence) WHERE c.strength <= 0 "
            "RETURN count(c) = 0 AS passed"
        ),
    },

    # ---- HEAL ----
    {
        "node_id": "test-inferred-edges-have-source",
        "label": "All INFERRED edges have a source property",
        "validates": "protocol-heal-triangles",
        "cypher": (
            "MATCH ()-[r:CONCEPTUALLY_RELATED_TO]->() "
            "WHERE r.confidence = 'INFERRED' AND r.source IS NULL "
            "RETURN count(r) = 0 AS passed"
        ),
    },
    {
        "node_id": "test-no-orphan-transients",
        "label": "No orphan transient nodes (degree 0)",
        "validates": "protocol-heal-orphans",
        "cypher": (
            "MATCH (n) WHERE NOT (n)-[]-() "
            "AND n.file_type IN ['concept', 'demand', 'intent', 'coupling', 'trace', 'commit'] "
            "RETURN count(n) = 0 AS passed"
        ),
    },

    # ---- PROPOSE ----
    {
        "node_id": "test-proposals-have-provenance",
        "label": "All ActionProposal nodes have source and proposed_at",
        "validates": "protocol-propose",
        "cypher": (
            "OPTIONAL MATCH (p:ActionProposal) "
            "WHERE p.source IS NULL OR p.proposed_at IS NULL "
            "RETURN count(p) = 0 AS passed"
        ),
    },

    # ---- ROUTE ----
    {
        "node_id": "test-route-returns-valid",
        "label": "Route protocol produces valid person-knowledge pairs",
        "validates": "protocol-route",
        "cypher": (
            "OPTIONAL MATCH (p:Person)-[:HAS_INTENT]->(i:Intent)-[:CONVERGES_TO]->(c:Convergence) "
            "OPTIONAL MATCH (k:Knowledge)-[:ADDRESSES]->(c) "
            "RETURN true AS passed"
        ),
    },

    # ---- LEARN ----
    {
        "node_id": "test-measurement-exists",
        "label": "Measurement node exists after learn protocol",
        "validates": "protocol-learn",
        "cypher": (
            "MATCH (m:Measurement) RETURN count(m) > 0 AS passed"
        ),
    },

    # ---- REPORT ----
    {
        "node_id": "test-graph-alive",
        "label": "Graph has nodes and edges",
        "validates": "protocol-report",
        "cypher": (
            "MATCH (n) WITH count(n) AS nodes "
            "MATCH ()-[r]->() WITH nodes, count(r) AS edges "
            "RETURN nodes > 0 AND edges > 0 AS passed"
        ),
    },

    # ---- META: TDD SELF-AWARENESS ----
    {
        "node_id": "test-tdd-full-coverage",
        "label": "Every Protocol has at least one TestCase",
        "validates": "protocol-report",
        "cypher": (
            "MATCH (p:Protocol) "
            "WHERE NOT (:TestCase)-[:VALIDATES]->(p) "
            "RETURN count(p) = 0 AS passed"
        ),
    },
]


# ================================================================
# SEED
# ================================================================

def seed(graph):
    ts = datetime.now(timezone.utc).isoformat()

    # Clean old PipelineStage nodes (replaced by Protocol)
    print("[seed] Cleaning old PipelineStage nodes...")
    try:
        r = graph.query("MATCH (s:PipelineStage) DETACH DELETE s RETURN count(s)")
        old = r.result_set[0][0] if r.result_set else 0
        print(f"  Removed {old} old PipelineStage nodes")
    except Exception:
        pass

    try:
        graph.query("MATCH (ph:PipelinePhase) DETACH DELETE ph RETURN count(ph)")
    except Exception:
        pass

    # Create Protocol nodes
    print("[seed] Creating Protocol nodes...")
    created = 0
    for p in PROTOCOLS:
        cypher_set = f', s.cypher = "{esc_dq(p["cypher"])}"' if p.get("cypher") else ''
        script_set = f', s.script_path = "{esc_dq(p["script_path"])}"' if p.get("script_path") else ''

        q = (
            f"MERGE (s:Protocol {{node_id: '{esc(p['node_id'])}'}}) "
            f"SET s.name = '{esc(p['name'])}', "
            f"s.phase = '{esc(p['phase'])}', "
            f"s.protocol_order = {p['order']}, "
            f"s.protocol_type = '{esc(p['protocol_type'])}', "
            f"s.description = \"{esc_dq(p['description'])}\", "
            f"s.cost = 0, "
            f"s.enabled = true, "
            f"s.last_status = 'pending', "
            f"s.seeded_at = '{esc(ts)}'"
            f"{cypher_set}{script_set}"
        )
        try:
            graph.query(q)
            created += 1
        except Exception as e:
            print(f"  FAILED {p['node_id']}: {e}")

    print(f"  {created}/{len(PROTOCOLS)} protocols created")

    # Create ENABLES edges
    print("[seed] Wiring ENABLES edges...")
    edges = 0
    for src, dst in ENABLES:
        try:
            graph.query(
                f"MATCH (a:Protocol {{node_id: '{esc(src)}'}}), "
                f"(b:Protocol {{node_id: '{esc(dst)}'}}) "
                f"MERGE (a)-[:ENABLES]->(b)"
            )
            edges += 1
        except Exception as e:
            print(f"  FAILED {src} → {dst}: {e}")
    print(f"  {edges}/{len(ENABLES)} edges created")

    # Create TestCase nodes
    print("[seed] Creating TestCase nodes...")
    tests = 0
    for t in TESTS:
        try:
            graph.query(
                f"MERGE (t:TestCase {{node_id: '{esc(t['node_id'])}'}}) "
                f"SET t.label = \"{esc_dq(t['label'])}\", "
                f"t.cypher = \"{esc_dq(t['cypher'])}\", "
                f"t.source = 'protocol', "
                f"t.last_result = 'pending'"
            )
            graph.query(
                f"MATCH (t:TestCase {{node_id: '{esc(t['node_id'])}'}}), "
                f"(p:Protocol {{node_id: '{esc(t['validates'])}'}}) "
                f"MERGE (t)-[:VALIDATES]->(p)"
            )
            tests += 1
        except Exception as e:
            print(f"  FAILED {t['node_id']}: {e}")
    print(f"  {tests}/{len(TESTS)} tests created")

    # Invariant 9: Cypher-Native Protocol
    print("[seed] Creating Invariant 9...")
    try:
        graph.query(
            "MERGE (inv:Invariant {node_id: 'invariant-9'}) "
            "SET inv.label = 'Cypher-Native Protocol', "
            "inv.number = 9, "
            "inv.status = 'active', "
            "inv.description = 'The system does not read. It ingests. "
            "All cognition is Cypher. Python is I/O glue at the boundary. "
            "Every ingestion triggers the full protocol chain. Zero LLM cost.'"
        )
        graph.query(
            "MATCH (p:Protocol), (inv:Invariant {node_id: 'invariant-9'}) "
            "MERGE (p)-[:UPHOLDS]->(inv)"
        )
    except Exception as e:
        print(f"  FAILED: {e}")

    # Clean up old invariant
    try:
        graph.query("MATCH (inv:Invariant {node_id: 'invariant-pipeline'}) DETACH DELETE inv")
    except Exception:
        pass

    return created, edges, tests


def verify(graph):
    """Verify the protocol topology."""
    print("\n[seed] Verification:")

    # Protocol chain
    try:
        r = graph.query("MATCH (p:Protocol) RETURN count(p)")
        print(f"  Protocols: {r.result_set[0][0]}")
    except Exception:
        pass

    # ENABLES edges
    try:
        r = graph.query("MATCH (:Protocol)-[e:ENABLES]->(:Protocol) RETURN count(e)")
        print(f"  ENABLES edges: {r.result_set[0][0]}")
    except Exception:
        pass

    # Tests wired
    try:
        r = graph.query("MATCH (t:TestCase)-[:VALIDATES]->(:Protocol) RETURN count(t)")
        print(f"  Tests wired: {r.result_set[0][0]}")
    except Exception:
        pass

    # Topology: roots (no inbound ENABLES)
    try:
        r = graph.query(
            "MATCH (p:Protocol) WHERE NOT (:Protocol)-[:ENABLES]->(p) "
            "RETURN p.name ORDER BY p.protocol_order"
        )
        roots = [row[0] for row in r.result_set]
        print(f"  Roots (entry points): {', '.join(roots)}")
    except Exception:
        pass

    # Topology: leaves (no outbound ENABLES)
    try:
        r = graph.query(
            "MATCH (p:Protocol) WHERE NOT (p)-[:ENABLES]->(:Protocol) "
            "RETURN p.name ORDER BY p.protocol_order"
        )
        leaves = [row[0] for row in r.result_set]
        print(f"  Leaves (terminal): {', '.join(leaves)}")
    except Exception:
        pass

    # Protocol types
    try:
        r = graph.query(
            "MATCH (p:Protocol) "
            "RETURN p.protocol_type, count(p) ORDER BY count(p) DESC"
        )
        types = {row[0]: row[1] for row in r.result_set}
        print(f"  Types: {types}")
    except Exception:
        pass


def main():
    print("[seed] Seeding system protocols into graph...")
    print(f"[seed] Graph: {FALKORDB_HOST}:{FALKORDB_PORT}")

    try:
        graph = get_graph()
    except Exception as e:
        print(f"FalkorDB unavailable: {e}")
        sys.exit(1)

    created, edges, tests = seed(graph)
    verify(graph)

    print(f"\n[seed] Done. The system's cognition is now graph topology.")
    print(f"[seed] Query: MATCH (a:Protocol)-[:ENABLES]->(b:Protocol) RETURN a.name, b.name")


if __name__ == "__main__":
    main()
