#!/usr/bin/env python3
"""
Dream Round — Cypher-native. The graph dreams about itself.

Sense → Heal → Propose → Learn. All graph traversal. Python is I/O glue.

Previous: NetworkX on exported JSON (2 files, 577+ lines).
Now: Cypher queries against live FalkorDB. No export step. No NetworkX.
"""

import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "knowledge" / "meta" / "dream-proposals.md"

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))


def esc(s):
    if s is None: return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")[:300]


def get_graph():
    from falkordb import FalkorDB
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph("asgard")


def main():
    print(f"[dream] Cypher-native dream round — {date.today().isoformat()}")

    try:
        graph = get_graph()
    except Exception as e:
        print(f"  FalkorDB unavailable: {e}")
        sys.exit(1)

    # ================================================================
    # SENSE — find structural issues via Cypher
    # ================================================================
    print("\nSensing...")

    # Graph stats
    stats = {}
    try:
        stats["nodes"] = graph.query("MATCH (n) RETURN count(n)").result_set[0][0]
        stats["edges"] = graph.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0]
        stats["types"] = len(graph.query("MATCH (n) RETURN DISTINCT labels(n)").result_set)
    except Exception:
        stats = {"nodes": "?", "edges": "?", "types": "?"}
    print(f"  Graph: {stats['nodes']} nodes, {stats['edges']} edges, {stats['types']} types")

    # Missing triangles: nodes that share a neighbor but have no direct edge
    triangles = []
    try:
        r = graph.query(
            "MATCH (a)-[]-(bridge)-[]-(c) "
            "WHERE a.node_id < c.node_id AND NOT (a)-[]-(c) "
            "AND a:Knowledge AND c:Knowledge "
            "WITH a, c, count(bridge) AS shared, "
            "  collect(bridge.label)[0] AS bridge_label "
            "ORDER BY shared DESC LIMIT 10 "
            "RETURN a.node_id, a.label, c.node_id, c.label, shared, bridge_label"
        )
        for row in r.result_set:
            triangles.append({"a": row[0], "a_label": row[1], "c": row[2], "c_label": row[3],
                              "shared": row[4], "bridge": row[5]})
    except Exception as e:
        print(f"  Triangle detection: {e}")
    print(f"  Missing triangles: {len(triangles)}")

    # Orphan nodes (degree 0) in transient layers
    orphans = []
    try:
        r = graph.query(
            "MATCH (n) WHERE NOT (n)-[]-() "
            "AND n.file_type IN ['concept', 'demand', 'intent', 'coupling', 'trace', 'commit'] "
            "RETURN n.node_id, labels(n), n.label"
        )
        orphans = [{"id": row[0], "type": row[1], "label": row[2]} for row in r.result_set]
    except Exception:
        pass
    print(f"  Orphan nodes (transient, degree 0): {len(orphans)}")

    # Hub dependency — highest betweenness approximation
    hubs = []
    try:
        r = graph.query(
            "MATCH (n)-[r]-() "
            "WITH n, count(r) AS degree "
            "WHERE degree > 10 "
            "RETURN n.node_id, n.label, labels(n), degree "
            "ORDER BY degree DESC LIMIT 5"
        )
        hubs = [{"id": row[0], "label": row[1], "type": row[2], "degree": row[3]} for row in r.result_set]
    except Exception:
        pass
    print(f"  High-degree hubs: {len(hubs)}")

    # ================================================================
    # HEAL — modify the graph
    # ================================================================
    print("\nHealing...")
    healed = {"triangles_closed": 0, "orphans_pruned": 0}

    # Close top triangles
    for tri in triangles[:10]:
        try:
            graph.query(
                f"MATCH (a {{node_id: '{esc(tri['a'])}'}}),"
                f" (c {{node_id: '{esc(tri['c'])}'}}) "
                f"MERGE (a)-[r:CONCEPTUALLY_RELATED_TO]->(c) "
                f"SET r.confidence = 'INFERRED', r.confidence_score = 0.4, "
                f"r.source = 'dream-round'"
            )
            healed["triangles_closed"] += 1
        except Exception:
            pass
    print(f"  Triangles closed: {healed['triangles_closed']}")

    # Prune orphans
    if orphans:
        try:
            r = graph.query(
                "MATCH (n) WHERE NOT (n)-[]-() "
                "AND n.file_type IN ['concept', 'demand', 'intent', 'coupling', 'trace', 'commit'] "
                "DETACH DELETE n RETURN count(n)"
            )
            healed["orphans_pruned"] = r.result_set[0][0] if r.result_set else 0
        except Exception:
            pass
    print(f"  Orphans pruned: {healed['orphans_pruned']}")

    # ================================================================
    # PROPOSE — walk purpose chains, find actionable gaps
    # ================================================================
    print("\nProposing...")
    ts = datetime.now(timezone.utc).isoformat()
    dream_id = f"dream-{date.today().isoformat()}"

    # Create Dream node
    try:
        graph.query(
            f"MERGE (d:Dream {{node_id: '{esc(dream_id)}'}}) "
            f"SET d.label = 'Dream round {date.today().isoformat()}', "
            f"d.timestamp = '{esc(ts)}', "
            f"d.triangles_closed = {healed['triangles_closed']}, "
            f"d.orphans_pruned = {healed['orphans_pruned']}, "
            f"d.file_type = 'dream'"
        )
        # Link to invariant 4
        graph.query(
            f"MATCH (d:Dream {{node_id: '{esc(dream_id)}'}}), "
            f"(inv:Invariant {{node_id: 'invariant-4'}}) "
            f"MERGE (d)-[:UPHOLDS]->(inv)"
        )
    except Exception:
        pass

    # Walk Purpose → Pull → Convergence → Intent → find resolutions
    proposals = 0
    try:
        r = graph.query(
            "MATCH (pur:Purpose {active: true})-[:DRIVEN_BY]->(gp:GravitationalPull)"
            "-[:PULLS_TOWARD]->(c:Convergence)<-[:CONVERGES_TO]-(i:Intent) "
            "WHERE i.recurrence_count >= 3 "
            "OPTIONAL MATCH (k:Knowledge) "
            "  WHERE k.community = i.community AND k.confidence IN ['high', 'medium'] "
            "WITH i, k, gp, c LIMIT 10 "
            "RETURN i.node_id, i.label, i.person, i.recurrence_count, "
            "  k.label AS resolution, k.node_id AS resolution_id, "
            "  gp.label AS pull, c.label AS convergence"
        )
        for row in r.result_set:
            intent_id, intent_label, person, recurrence, resolution, res_id, pull, conv = row
            action = "Route existing knowledge" if resolution else "Research the gap"
            proposal_id = f"proposal-{esc(intent_id or '')[:30]}-{date.today().isoformat()}"

            try:
                graph.query(
                    f"MERGE (p:ActionProposal {{node_id: '{esc(proposal_id)}'}}) "
                    f"SET p.label = '{esc(action)}: {esc(person)} — {esc(str(intent_label or '')[:60])}', "
                    f"p.action = '{esc(action)}', "
                    f"p.person = '{esc(person)}', "
                    f"p.proposed_at = '{esc(ts)}', "
                    f"p.status = 'proposed', "
                    f"p.source = 'dream-v2', "
                    f"p.created_by = '{esc(dream_id)}', "
                    f"p.file_type = 'action-proposal'"
                )
                graph.query(
                    f"MATCH (p:ActionProposal {{node_id: '{esc(proposal_id)}'}}), "
                    f"(d:Dream {{node_id: '{esc(dream_id)}'}}) "
                    f"MERGE (d)-[:PROPOSED]->(p)"
                )
                if res_id:
                    graph.query(
                        f"MATCH (p:ActionProposal {{node_id: '{esc(proposal_id)}'}}), "
                        f"(k:Knowledge {{node_id: '{esc(res_id)}'}}) "
                        f"MERGE (p)-[:RESOLVES_WITH]->(k)"
                    )
                proposals += 1
            except Exception:
                pass
    except Exception as e:
        print(f"  Purpose walk: {e}")

    # Check canary resolution paths
    try:
        r = graph.query(
            "MATCH (c:Canary)-[:RESOLUTION_PATH]->(k:Knowledge) "
            "RETURN c.node_id, c.label, c.person, k.label, k.node_id"
        )
        for row in r.result_set:
            canary_id, canary_label, person, k_label, k_id = row
            proposal_id = f"proposal-canary-{esc(canary_id or '')}-{date.today().isoformat()}"
            try:
                graph.query(
                    f"MERGE (p:ActionProposal {{node_id: '{esc(proposal_id)}'}}) "
                    f"SET p.label = 'Canary: route {esc(str(k_label or '')[:50])} to {esc(person)}', "
                    f"p.action = 'Route existing knowledge', "
                    f"p.person = '{esc(person)}', "
                    f"p.proposed_at = '{esc(ts)}', "
                    f"p.status = 'proposed', "
                    f"p.source = 'dream-canary', "
                    f"p.created_by = '{esc(dream_id)}', "
                    f"p.file_type = 'action-proposal'"
                )
                graph.query(
                    f"MATCH (p:ActionProposal {{node_id: '{esc(proposal_id)}'}}), "
                    f"(d:Dream {{node_id: '{esc(dream_id)}'}}) "
                    f"MERGE (d)-[:PROPOSED]->(p)"
                )
                proposals += 1
            except Exception:
                pass
    except Exception:
        pass

    # WorkItem proposals — surface unblocked development work
    try:
        r = graph.query(
            "MATCH (w:WorkItem {status: 'open'}) "
            "OPTIONAL MATCH (w)-[:DEPENDS_ON]->(dep:WorkItem) "
            "WHERE dep.status <> 'done' "
            "WITH w, count(dep) AS blocking "
            "WHERE blocking = 0 "
            "RETURN w.node_id, w.label, w.effort, w.issue_number"
        )
        for row in (r.result_set or []):
            w_id, w_label, w_effort, w_issue = row
            proposal_id = f"proposal-workitem-{w_issue or 0}-{date.today().isoformat()}"
            try:
                graph.query(
                    f"MERGE (p:ActionProposal {{node_id: '{esc(proposal_id)}'}}) "
                    f"SET p.label = 'Unblocked [{w_effort}]: {esc(str(w_label or '')[:80])}', "
                    f"p.action = 'WorkItem ready for execution', "
                    f"p.person = 'team', "
                    f"p.proposed_at = '{esc(ts)}', "
                    f"p.status = 'proposed', "
                    f"p.source = 'dream-workplan', "
                    f"p.created_by = '{esc(dream_id)}', "
                    f"p.file_type = 'action-proposal'"
                )
                graph.query(
                    f"MATCH (p:ActionProposal {{node_id: '{esc(proposal_id)}'}}), "
                    f"(d:Dream {{node_id: '{esc(dream_id)}'}}) "
                    f"MERGE (d)-[:PROPOSED]->(p)"
                )
                # Link to a Knowledge node the WorkItem touches
                graph.query(
                    f"MATCH (p:ActionProposal {{node_id: '{esc(proposal_id)}'}}), "
                    f"(w:WorkItem {{node_id: '{esc(w_id)}'}})-[:RELATES_TO]->(k:Knowledge) "
                    f"WITH p, k LIMIT 1 "
                    f"MERGE (p)-[:RESOLVES_WITH]->(k)"
                )
                proposals += 1
            except Exception:
                pass
        if r.result_set:
            print(f"  WorkItems unblocked: {len(r.result_set)}")
    except Exception as e:
        print(f"  WorkItem check: {e}")

    print(f"  Dream node: {dream_id}")
    print(f"  Proposals: {proposals}")

    # ================================================================
    # LEARN — measure, attribute, adjust
    # ================================================================
    print("\nLearning...")
    learned = learn(graph, dream_id)
    for key, val in learned.items():
        print(f"  {key}: {val}")

    # ================================================================
    # REPORT — write markdown
    # ================================================================
    report = generate_report(stats, triangles, orphans, hubs, healed, proposals, learned)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(report)
    print(f"\nReport: {OUTPUT_PATH}")

    # Summary
    print(f"\n=== DREAM SUMMARY ===")
    print(f"Sensed: {len(triangles)} triangles, {len(orphans)} orphans, {len(hubs)} hubs")
    print(f"Healed: {healed['triangles_closed']} closures, {healed['orphans_pruned']} prunes")
    print(f"Proposed: {proposals} actions from purpose")
    print(f"Learned: {learned.get('learnings_created', 0)} new learnings")


def learn(graph, dream_id):
    """Measure → Attribute → Adjust → Learn. All Cypher."""
    ts = datetime.now(timezone.utc).isoformat()
    result = {"measurements": 0, "attributions": 0, "adjustments": 0, "learnings_created": 0}

    # Measure: dream edge activations
    dream_edge_activations = 0
    try:
        r = graph.query(
            "MATCH ()-[r:CONCEPTUALLY_RELATED_TO]->() WHERE r.source = 'dream-round' "
            "WITH startNode(r) AS a, endNode(r) AS b "
            "OPTIONAL MATCH (t:Trace)-[:TOUCHES]->(a) "
            "OPTIONAL MATCH (t2:Trace)-[:TOUCHES]->(b) "
            "WITH a, b, count(t) + count(t2) AS activations "
            "WHERE activations > 0 "
            "RETURN count(*), sum(activations)"
        )
        if r.result_set and r.result_set[0][1]:
            dream_edge_activations = r.result_set[0][1]
    except Exception:
        pass

    # Measure: concept activation
    concept_activation = 0
    total_concepts = 0
    try:
        total_concepts = graph.query("MATCH (c:Concept) RETURN count(c)").result_set[0][0] or 0
        r = graph.query(
            "MATCH (t:Trace)-[:TOUCHES]->(k:Knowledge)<-[]-(c:Concept) "
            "RETURN count(DISTINCT c)"
        )
        concept_activation = r.result_set[0][0] if r.result_set else 0
    except Exception:
        pass

    # Measure: proposal execution
    proposals_total = 0
    proposals_executed = 0
    try:
        r = graph.query(
            "MATCH (ap:ActionProposal) "
            "RETURN count(ap), count(CASE WHEN ap.status = 'executed' THEN 1 END)"
        )
        if r.result_set:
            proposals_total = r.result_set[0][0] or 0
            proposals_executed = r.result_set[0][1] or 0
    except Exception:
        pass

    # Record measurement
    meas_id = f"meas-{date.today().isoformat()}"
    try:
        graph.query(
            f"MERGE (m:Measurement {{node_id: '{esc(meas_id)}'}}) "
            f"SET m.label = 'Measurement {date.today().isoformat()}', "
            f"m.dream_edge_activations = {dream_edge_activations}, "
            f"m.concept_activation = {concept_activation}, "
            f"m.total_concepts = {total_concepts}, "
            f"m.proposals_total = {proposals_total}, "
            f"m.proposals_executed = {proposals_executed}, "
            f"m.timestamp = '{esc(ts)}', "
            f"m.file_type = 'measurement'"
        )
        graph.query(
            f"MATCH (d:Dream {{node_id: 'dream-{date.today().isoformat()}'}}), "
            f"(m:Measurement {{node_id: '{esc(meas_id)}'}}) "
            f"MERGE (d)-[:MEASURED_BY]->(m)"
        )
        result["measurements"] = 1
    except Exception:
        pass

    # Attribute: dream edges activated
    if dream_edge_activations > 0:
        attr_id = f"attr-edges-{date.today().isoformat()}"
        try:
            graph.query(
                f"MERGE (a:Attribution {{node_id: '{esc(attr_id)}'}}) "
                f"SET a.label = 'Dream edges attracted {dream_edge_activations} activations', "
                f"a.cause = 'triangle_closure', a.effect = 'trace_activation', "
                f"a.strength = {dream_edge_activations}, "
                f"a.timestamp = '{esc(ts)}', a.file_type = 'attribution'"
            )
            result["attributions"] += 1
        except Exception:
            pass

    # Adjust: proposals unexecuted
    if proposals_total > 0 and proposals_executed == 0:
        try:
            graph.query(
                f"MERGE (adj:Adjustment {{node_id: 'adj-escalate-{date.today().isoformat()}'}}) "
                f"SET adj.label = 'Escalate: {proposals_total} proposals unexecuted', "
                f"adj.action = 'Shift from route to research proposals', "
                f"adj.timestamp = '{esc(ts)}', adj.file_type = 'adjustment'"
            )
            result["adjustments"] += 1
        except Exception:
            pass

    # Adjust: cold concepts
    if total_concepts > 0 and concept_activation == 0:
        try:
            graph.query(
                f"MERGE (adj:Adjustment {{node_id: 'adj-concepts-{date.today().isoformat()}'}}) "
                f"SET adj.label = 'Warm concepts: 0/{total_concepts} activated', "
                f"adj.action = 'Close triangles between Concept and high-traffic Knowledge', "
                f"adj.timestamp = '{esc(ts)}', adj.file_type = 'adjustment'"
            )
            result["adjustments"] += 1
        except Exception:
            pass

    # Learn: if dream edges confirmed
    if dream_edge_activations > 2:
        learn_id = f"learning-edges-{date.today().isoformat()}"
        try:
            graph.query(
                f"MERGE (l:Learning {{node_id: '{esc(learn_id)}'}}) "
                f"SET l.label = 'Dream edges attract traffic ({dream_edge_activations} activations)', "
                f"l.insight = 'Close more triangles near high-traffic nodes.', "
                f"l.confidence = 'confirmed', "
                f"l.timestamp = '{esc(ts)}', l.file_type = 'learning'"
            )
            graph.query(
                f"MATCH (l:Learning {{node_id: '{esc(learn_id)}'}}), (d:Dream) "
                f"MERGE (l)-[:GUIDES]->(d)"
            )
            result["learnings_created"] += 1
        except Exception:
            pass

    # Read existing learnings
    try:
        learnings = graph.query(
            "MATCH (l:Learning) WHERE l.confidence = 'confirmed' RETURN l.label"
        ).result_set
        if learnings:
            result["active_learnings"] = len(learnings)
            for l in learnings:
                print(f"    [learned] {l[0]}")
    except Exception:
        pass

    return result


def generate_report(stats, triangles, orphans, hubs, healed, proposals, learned):
    today = date.today().isoformat()
    lines = [
        f"# Dream Round — {today}",
        "",
        f"**Method:** Cypher-native (zero NetworkX, zero JSON export)",
        f"**Graph:** {stats.get('nodes', '?')} nodes, {stats.get('edges', '?')} edges",
        "",
        f"## Sensed",
        f"- Missing triangles (Knowledge layer): {len(triangles)}",
        f"- Orphan nodes (transient, degree 0): {len(orphans)}",
        f"- High-degree hubs (>10 edges): {len(hubs)}",
        "",
    ]
    if triangles:
        lines.append("### Top Missing Triangles")
        for t in triangles[:5]:
            lines.append(f"- {t['a_label'][:40]} ↔ {t['c_label'][:40]} (shared: {t['shared']}, via: {t['bridge'][:30]})")
        lines.append("")
    if hubs:
        lines.append("### Hub Dependencies")
        for h in hubs:
            lines.append(f"- {h['label'][:50]} ({h['type']}, degree {h['degree']})")
        lines.append("")

    lines.extend([
        f"## Healed",
        f"- Triangles closed: {healed['triangles_closed']}",
        f"- Orphans pruned: {healed['orphans_pruned']}",
        "",
        f"## Proposed",
        f"- Action proposals: {proposals}",
        "",
        f"## Learned",
        f"- Measurements: {learned.get('measurements', 0)}",
        f"- Attributions: {learned.get('attributions', 0)}",
        f"- Adjustments: {learned.get('adjustments', 0)}",
        f"- Learnings created: {learned.get('learnings_created', 0)}",
        f"- Active learnings: {learned.get('active_learnings', 0)}",
        "",
        "---",
        f"*Dream round {today}. Cypher-native. Python is I/O glue only.*",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
