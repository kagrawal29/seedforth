#!/usr/bin/env python3
"""
Integrity Rules — Cypher-native. Graph health enforcement.

6 rules, all graph traversal. Python is I/O glue only.

1. Demand decay — Knowledge nodes with no demand edges
2. Edge verification — INFERRED edges with no supporting demand
3. Knowledge contradictions — same-category entries with high tag overlap
4. Cross-layer contradictions — Demand↔Knowledge, Concept↔Knowledge mismatches
5. Effectiveness metrics — frustration, gaps, intent resolution, concept activation
6. CouplingEvent decay — prune events older than 7 days
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
TODAY = datetime.now().strftime("%Y-%m-%d")
COUPLING_TTL_DAYS = 7


def get_graph():
    from falkordb import FalkorDB
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph("asgard")


def main():
    print(f"[integrity] Cypher-native integrity checks — {TODAY}")

    try:
        graph = get_graph()
    except Exception as e:
        print(f"  FalkorDB unavailable: {e}")
        sys.exit(1)

    total_issues = 0

    # ================================================================
    # RULE 1: Demand decay — Knowledge with no demand activity
    # ================================================================
    try:
        r = graph.query(
            "MATCH (k:Knowledge) "
            "WHERE NOT (:Demand)-[]->(k) AND NOT (:Trace)-[:TOUCHES]->(k) "
            "AND NOT (:CouplingEvent)-[:ACTIVATED]->(k) "
            "RETURN k.node_id, k.label "
            "LIMIT 20"
        )
        decay_count = len(r.result_set) if r.result_set else 0
        total_issues += decay_count
        print(f"\n  Demand decay (Knowledge with no demand/trace/coupling): {decay_count}")
        for row in (r.result_set or [])[:5]:
            print(f"    [DECAY] {row[1][:60]}")
        if decay_count > 5:
            print(f"    ... and {decay_count - 5} more")
    except Exception as e:
        print(f"  Rule 1 failed: {e}")

    # ================================================================
    # RULE 2: Edge verification — stale INFERRED edges
    # ================================================================
    try:
        r = graph.query(
            "MATCH (a)-[r:CONCEPTUALLY_RELATED_TO]->(b) "
            "WHERE r.confidence = 'INFERRED' "
            "AND NOT (:Trace)-[:TOUCHES]->(a) "
            "AND NOT (:Trace)-[:TOUCHES]->(b) "
            "RETURN count(r)"
        )
        stale_edges = r.result_set[0][0] if r.result_set else 0
        total_issues += stale_edges
        print(f"\n  Stale INFERRED edges (no trace activity on either endpoint): {stale_edges}")

        # Auto-prune: delete INFERRED edges where neither endpoint has trace/coupling activity
        if stale_edges > 0:
            r2 = graph.query(
                "MATCH (a)-[r:CONCEPTUALLY_RELATED_TO]->(b) "
                "WHERE r.confidence = 'INFERRED' "
                "AND NOT (:Trace)-[:TOUCHES]->(a) "
                "AND NOT (:Trace)-[:TOUCHES]->(b) "
                "AND NOT (:CouplingEvent)-[:ACTIVATED]->(a) "
                "AND NOT (:CouplingEvent)-[:ACTIVATED]->(b) "
                "DELETE r "
                "RETURN count(r)"
            )
            pruned = r2.result_set[0][0] if r2.result_set else 0
            print(f"  Pruned {pruned} stale INFERRED edges")
    except Exception as e:
        print(f"  Rule 2 failed: {e}")

    # ================================================================
    # RULE 3: Knowledge contradictions — same category, high tag overlap
    # ================================================================
    try:
        r = graph.query(
            "MATCH (a:Knowledge), (b:Knowledge) "
            "WHERE a.node_id < b.node_id "
            "AND a.category = b.category AND a.category IS NOT NULL "
            "AND a.tags IS NOT NULL AND b.tags IS NOT NULL "
            "AND size([t IN split(a.tags, ', ') WHERE b.tags CONTAINS t AND size(t) > 3]) >= 4 "
            "RETURN a.label, b.label, a.category "
            "LIMIT 10"
        )
        contradictions = len(r.result_set) if r.result_set else 0
        total_issues += contradictions
        print(f"\n  Knowledge contradictions (same category, 4+ shared tags): {contradictions}")
        for row in (r.result_set or []):
            print(f"    [{row[2]}] {row[0][:40]} vs {row[1][:40]}")

        # --- Auto-resolve: demote the less-connected entry in each pair ---
        if contradictions > 0:
            try:
                res = graph.query(
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
                    "RETURN count(loser)"
                )
                resolved = res.result_set[0][0] if res.result_set else 0
                print(f"    [RESOLVED] Demoted {resolved} lower-importance entries (confidence_lowered_by = 'integrity-contradiction')")
            except Exception as e2:
                print(f"    [RESOLVE-FAIL] Could not auto-resolve contradictions: {e2}")
    except Exception as e:
        print(f"  Rule 3 failed: {e}")

    # ================================================================
    # RULE 4: Cross-layer contradictions
    # ================================================================
    cross_issues = 0

    # 4a: High-frustration demand supposedly answered
    try:
        r = graph.query(
            "MATCH (d:Demand)-[:ANSWERED_BY]->(k:Knowledge) "
            "WHERE d.frustration IN ['high', 'medium'] AND d.frequency > 3 "
            "RETURN d.label, d.frustration, d.frequency, k.label"
        )
        for row in (r.result_set or []):
            print(f"    [CROSS] Frustrated demand (freq={row[2]}, {row[1]}) supposedly answered by '{row[3][:40]}'")
            cross_issues += 1
    except Exception:
        pass

    # 4b: Gap signal with partial coverage
    try:
        r = graph.query(
            "MATCH (d:Demand)-[:PARTIALLY_ANSWERED_BY]->(k:Knowledge) "
            "WHERE d.gap_signal = true "
            "RETURN d.label, k.label"
        )
        for row in (r.result_set or []):
            cross_issues += 1
    except Exception:
        pass

    # 4c: Concept constrains knowledge
    try:
        r = graph.query(
            "MATCH (c:Concept)-[:CONSTRAINS]->(k:Knowledge) "
            "RETURN c.label, k.label"
        )
        for row in (r.result_set or []):
            cross_issues += 1
    except Exception:
        pass

    total_issues += cross_issues
    print(f"\n  Cross-layer contradictions: {cross_issues}")

    # ================================================================
    # RULE 5: Effectiveness metrics
    # ================================================================
    print(f"\n  Effectiveness metrics:")

    # Frustration distribution
    try:
        r = graph.query(
            "MATCH (d:Demand) "
            "RETURN d.frustration, count(d) ORDER BY count(d) DESC"
        )
        frust = {row[0]: row[1] for row in (r.result_set or [])}
        total_d = sum(frust.values())
        print(f"    [tracking] frustration: {frust.get('high', 0)} high, {frust.get('medium', 0)} medium, "
              f"{frust.get('low', 0)} low out of {total_d}")
    except Exception:
        pass

    # Gap coverage
    try:
        r = graph.query(
            "MATCH (d:Demand) WHERE d.gap_signal = true "
            "RETURN count(d), avg(d.coverage_score)"
        )
        if r.result_set and r.result_set[0][0]:
            gaps = r.result_set[0][0]
            avg_cov = r.result_set[0][1] or 0
            direction = "needs_attention" if avg_cov < 0.3 else "improving"
            print(f"    [{direction}] gaps: {gaps} active, avg coverage {avg_cov:.2f}")
    except Exception:
        pass

    # Intent resolution (compare current vs previous via Learning/Measurement)
    try:
        r = graph.query("MATCH (i:Intent) RETURN count(i)")
        current_intents = r.result_set[0][0] if r.result_set else 0
        r2 = graph.query(
            "MATCH (m:Measurement) WHERE m.file_type = 'measurement' "
            "RETURN m.concept_activation, m.total_concepts ORDER BY m.timestamp DESC LIMIT 1"
        )
        if r2.result_set:
            activation = r2.result_set[0][0] or 0
            total_c = r2.result_set[0][1] or 0
            pct = round(activation / max(total_c, 1) * 100, 1)
            print(f"    [{'cold' if pct < 10 else 'warm'}] concept activation: {activation}/{total_c} ({pct}%)")
        print(f"    [tracking] intents: {current_intents} active")
    except Exception:
        pass

    # Convergence strength
    try:
        r = graph.query("MATCH (c:Convergence) RETURN sum(c.strength)")
        strength = r.result_set[0][0] if r.result_set else 0
        print(f"    [tracking] convergence strength: {strength:.1f}")
    except Exception:
        pass

    # ================================================================
    # RULE 6: CouplingEvent decay
    # ================================================================
    coupling_pruned = 0
    try:
        cutoff = (datetime.now() - timedelta(days=COUPLING_TTL_DAYS)).strftime("%Y-%m-%dT%H:%M:%S")
        r = graph.query(
            f"MATCH (e:CouplingEvent) WHERE e.timestamp < '{cutoff}' "
            f"WITH e LIMIT 500 DETACH DELETE e RETURN count(e)"
        )
        coupling_pruned = r.result_set[0][0] if r.result_set else 0
    except Exception:
        pass

    # Trace decay (2 days)
    trace_pruned = 0
    try:
        cutoff = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
        r = graph.query(
            f"MATCH (t:Trace) WHERE t.timestamp < '{cutoff}' "
            f"WITH t LIMIT 500 DETACH DELETE t RETURN count(t)"
        )
        trace_pruned = r.result_set[0][0] if r.result_set else 0
    except Exception:
        pass

    # Commit decay (14 days)
    commit_pruned = 0
    try:
        cutoff = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S")
        r = graph.query(
            f"MATCH (c:Commit) WHERE c.timestamp < '{cutoff}' "
            f"WITH c LIMIT 500 DETACH DELETE c RETURN count(c)"
        )
        commit_pruned = r.result_set[0][0] if r.result_set else 0
    except Exception:
        pass

    print(f"\n  Decay: {coupling_pruned} CouplingEvents, {trace_pruned} Traces, {commit_pruned} Commits pruned")

    # ================================================================
    # RULE 7: WorkItem health — staleness, wave progression, convergence
    # ================================================================
    workitem_issues = 0

    # 7a: Stale WorkItems (in_progress > 48h)
    try:
        cutoff = (datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S")
        r = graph.query(
            f"MATCH (w:WorkItem {{status: 'in_progress'}}) "
            f"WHERE w.started_at < '{cutoff}' "
            f"RETURN w.label, w.issue_number"
        )
        for row in (r.result_set or []):
            print(f"    [STALE] WorkItem #{row[1]}: {row[0][:60]}")
            workitem_issues += 1
    except Exception:
        pass

    # 7b: Wave progression — is the current wave complete?
    try:
        r = graph.query(
            "MATCH (wave:Wave)-[:CONTAINS]->(w:WorkItem) "
            "WITH wave, count(w) AS total, "
            "  count(CASE WHEN w.status = 'done' THEN 1 END) AS done_count "
            "RETURN wave.label, total, done_count "
            "ORDER BY wave.node_id"
        )
        for row in (r.result_set or []):
            status = "COMPLETE" if row[1] == row[2] else f"{row[2]}/{row[1]}"
            print(f"    [WAVE] {row[0]}: {status}")
    except Exception:
        pass

    # 7c: Work convergence — multiple open items touching same knowledge
    try:
        r = graph.query(
            "MATCH (w1:WorkItem {status: 'open'})-[:RELATES_TO]->(k:Knowledge)"
            "<-[:RELATES_TO]-(w2:WorkItem {status: 'open'}) "
            "WHERE w1.node_id < w2.node_id "
            "RETURN k.label, count(*) AS convergence "
            "ORDER BY convergence DESC LIMIT 3"
        )
        for row in (r.result_set or []):
            if row[1] > 1:
                print(f"    [CONVERGE] '{row[0][:50]}' touched by {row[1]} open items")
    except Exception:
        pass

    # 7d: Sync WorkItem status from closed GitHub issues
    try:
        r = graph.query(
            "MATCH (w:WorkItem)-[:TRACKS]->(i:Issue) "
            "WHERE i.state = 'closed' AND w.status <> 'done' "
            "SET w.status = 'done' "
            "RETURN w.label, w.issue_number"
        )
        for row in (r.result_set or []):
            print(f"    [CLOSED] WorkItem #{row[1]} marked done (issue closed)")
    except Exception:
        pass

    total_issues += workitem_issues
    print(f"\n  WorkItem health: {workitem_issues} issues")

    # ================================================================
    # RULE 8 (CM3): Confidence decay — single-source entries capped to low
    # ================================================================
    try:
        r = graph.query(
            "MATCH (k:Knowledge) "
            "WHERE coalesce(k.evidence_count, 0) <= 1 "
            "AND k.confidence IN ['high', 'medium'] "
            "SET k.confidence = 'low', k.confidence_capped_reason = 'single-source' "
            "RETURN count(k)"
        )
        capped = r.result_set[0][0] if r.result_set else 0
        print(f"\n  CM3 confidence decay: {capped} single-source entries capped to low")
    except Exception as e:
        print(f"  Rule 8 (CM3) failed: {e}")

    print(f"\n  Total integrity issues: {total_issues}")


if __name__ == "__main__":
    main()
