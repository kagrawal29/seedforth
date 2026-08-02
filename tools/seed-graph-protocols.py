#!/usr/bin/env python3
"""Seed graph-native protocols (progress-score, lifecycle) into the graph.

The reasoning lives IN the graph as CypherAtom chains. This loader writes
them once (idempotent). After seeding, the protocols run via graph-runner
reading from the graph — not from this file.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from neo4j_helper import q_strict

PROGRESS_ATOMS = [
    (
        "atom-progress-classify-commits",
        "Classify commit signals: noise scores 0, real work scores 1.0",
        "MATCH (s:CommitSignal) WHERE s.classified IS NULL "
        "WITH s, CASE "
        "WHEN toLower(s.message) STARTS WITH 'auto' THEN 0.0 "
        "WHEN toLower(s.message) STARTS WITH 'sync' THEN 0.0 "
        "WHEN toLower(s.message) STARTS WITH 'ci' THEN 0.0 "
        "WHEN toLower(s.message) STARTS WITH 'chore' THEN 0.0 "
        "WHEN toLower(s.message) STARTS WITH 'wip' THEN 0.0 "
        "WHEN toLower(s.message) STARTS WITH 'update' THEN 0.0 "
        "WHEN toLower(s.message) STARTS WITH 'minor' THEN 0.0 "
        "WHEN size(s.message) < 15 THEN 0.0 "
        "WHEN toLower(s.message) CONTAINS 'feat:' THEN 1.0 "
        "WHEN toLower(s.message) CONTAINS 'fix:' THEN 1.0 "
        "WHEN toLower(s.message) CONTAINS 'build:' THEN 1.0 "
        "WHEN toLower(s.message) CONTAINS 'deploy:' THEN 1.0 "
        "WHEN toLower(s.message) CONTAINS 'design:' THEN 1.0 "
        "WHEN toLower(s.message) CONTAINS 'learn:' THEN 1.0 "
        "WHEN toLower(s.message) CONTAINS 'report:' THEN 1.0 "
        "WHEN toLower(s.message) CONTAINS 'docs:' THEN 1.0 "
        "WHEN toLower(s.message) CONTAINS 'refactor:' THEN 1.0 "
        "ELSE 0.3 END AS weight "
        "SET s.is_real = weight > 0, s.weight = weight, s.classified = true",
    ),
    (
        "atom-progress-classify-outbox",
        "Classify outbox signals: artifact 0.8, embed+numbers 0.7, text+numbers 0.5",
        "MATCH (s:OutboxSignal) WHERE s.classified IS NULL "
        "WITH s, CASE "
        "WHEN s.has_file = true THEN 0.8 "
        "WHEN s.has_embed = true AND s.has_numbers = true THEN 0.7 "
        "WHEN s.length > 80 AND s.has_numbers = true THEN 0.5 "
        "ELSE 0.0 END AS weight "
        "SET s.is_real = weight > 0, s.weight = weight, s.classified = true",
    ),
    (
        "atom-progress-classify-artifacts",
        "Artifact signals score 0.4",
        "MATCH (s:ArtifactSignal) WHERE s.classified IS NULL "
        "SET s.is_real = true, s.weight = 0.4, s.classified = true",
    ),
    (
        "atom-progress-promote-events",
        "Promote weighted classified signals to ProgressEvent nodes",
        "MATCH (s) WHERE (s:CommitSignal OR s:OutboxSignal OR s:ArtifactSignal) "
        "AND s.classified = true AND s.weight > 0 AND NOT ((s)-[:EVIDENCE]->()) "
        "CREATE (pe:ProgressEvent {node_id: 'pe-' + s.entity + '-' + s.node_id, "
        "entity: s.entity, marker: labels(s)[0], "
        "evidence: coalesce(s.message, s.text_preview, s.path), "
        "weight: s.weight, created_at: s.created_at, project: s.entity}) "
        "MERGE (s)-[:EVIDENCE {decay_protected:true}]->(pe)",
    ),
    (
        "atom-progress-compute-status",
        "Compute producing flag: weight >= 1.0 in last 7 days",
        "MATCH (pe:ProgressEvent) "
        "WHERE pe.created_at > datetime() - duration({days:7}) "
        "WITH pe.entity AS entity, sum(pe.weight) AS total_weight "
        "MERGE (f:FleetProgress {entity: entity, node_id: 'fp-' + entity}) "
        "SET f.producing = total_weight >= 1.0, f.total_weight = total_weight, "
        "f.updated_at = datetime(), f.project = entity",
    ),
]

LIFECYCLE_ATOMS = [
    (
        "atom-lifecycle-seed",
        "Seed lifecycle_state from runtime status",
        "MATCH (p:Project) WHERE p.lifecycle_state IS NULL AND p.status IS NOT NULL "
        "WITH p, CASE "
        "WHEN p.status IN ['hibernated','hibernating','config-only'] THEN 'dormant' "
        "WHEN p.status = 'built' THEN 'complete' "
        "ELSE 'seed' END AS st "
        "SET p.lifecycle_state = st",
    ),
    (
        "atom-lifecycle-active-to-stalled",
        "Flag active projects with no producing progress as stalled",
        "MATCH (p:Project {lifecycle_state: 'active'}) "
        "OPTIONAL MATCH (fp:FleetProgress {entity: p.name}) WHERE fp.producing = true "
        "WITH p, fp WHERE fp IS NULL "
        "CREATE (le:LifecycleEvent {node_id: 'le-' + p.name + '-' + toString(timestamp()), "
        "entity: p.name, from_state: 'active', to_state: 'stalled', "
        "reason: 'No real progress (weight < 1.0) in 7 days', "
        "triggered_by: 'auto-rule', created_at: datetime(), project: p.name}) "
        "MERGE (le)-[:TRANSITIONS {decay_protected:true}]->(p) "
        "SET p.lifecycle_state = 'stalled', p.updated_at = datetime() "
        "WITH p "
        "MERGE (ap:ActionProposal {node_id: 'ap-lifecycle-' + p.name + '-' + toString(date())}) "
        "ON CREATE SET ap.type = 'ConfirmLifecycle', ap.entity = p.name, "
        "ap.description = 'Auto-flagged ' + p.name + ' as stalled (no real progress). Confirm or rescue.', "
        "ap.status = 'pending', ap.confidence = 0.85, "
        "ap.generated_at = datetime(), ap.project = p.name",
    ),
    (
        "atom-lifecycle-stalled-to-active",
        "Restore stalled projects that resumed progress",
        "MATCH (p:Project {lifecycle_state: 'stalled'}) "
        "MATCH (fp:FleetProgress {entity: p.name}) WHERE fp.producing = true "
        "CREATE (le:LifecycleEvent {node_id: 'le-' + p.name + '-' + toString(timestamp()), "
        "entity: p.name, from_state: 'stalled', to_state: 'active', "
        "reason: 'Real progress resumed (weight >= 1.0)', "
        "triggered_by: 'auto-rule', created_at: datetime(), project: p.name}) "
        "MERGE (le)-[:TRANSITIONS {decay_protected:true}]->(p) "
        "SET p.lifecycle_state = 'active', p.updated_at = datetime()",
    ),
    (
        "atom-lifecycle-active-to-complete",
        "Propose complete for active projects with no open goals and no progress",
        "MATCH (p:Project {lifecycle_state: 'active'}) "
        "OPTIONAL MATCH (g:EntityGoal {project: p.name, status: 'active'}) "
        "WITH p, count(g) AS open_goals "
        "OPTIONAL MATCH (fp:FleetProgress {entity: p.name}) WHERE fp.producing = true "
        "WITH p, open_goals, fp WHERE open_goals = 0 AND fp IS NULL "
        "MERGE (ap:ActionProposal {node_id: 'ap-complete-' + p.name + '-' + toString(date())}) "
        "ON CREATE SET ap.type = 'ConfirmLifecycle', ap.entity = p.name, "
        "ap.description = p.name + ' has no open goals and no progress. Propose complete/maintenance.', "
        "ap.status = 'pending', ap.confidence = 0.9, "
        "ap.generated_at = datetime(), ap.project = p.name",
    ),
]


def seed_protocol(protocol_id, label, atoms, cadence):
    print(f"  seeding {protocol_id}...")
    q_strict(
        "MERGE (p:Protocol {node_id:$pid}) SET p.label=$label, p.cadence=$cadence, "
        "p.enabled=true, p.project='system'",
        {"pid": protocol_id, "label": label, "cadence": cadence},
    )
    atom_ids = []
    for i, (atom_id, semantic, cypher) in enumerate(atoms):
        q_strict(
            "MERGE (a:CypherAtom {node_id:$aid}) SET a.semantic=$sem, a.cypher=$c, "
            "a.project='system', a.updated_at=datetime()",
            {"aid": atom_id, "sem": semantic, "c": cypher},
        )
        atom_ids.append(atom_id)
        if i > 0:
            q_strict(
                "MATCH (a1:CypherAtom {node_id:$a1}) MATCH (a2:CypherAtom {node_id:$a2}) "
                "MERGE (a1)-[:FOLLOWS {decay_protected:true}]->(a2)",
                {"a1": atom_ids[i - 1], "a2": atom_id},
            )
    q_strict(
        "MATCH (p:Protocol {node_id:$pid})-[r:FIRST_ATOM]->(old) DELETE r",
        {"pid": protocol_id},
    )
    q_strict(
        "MATCH (p:Protocol {node_id:$pid}) MATCH (a:CypherAtom {node_id:$aid}) "
        "MERGE (p)-[:FIRST_ATOM {decay_protected:true}]->(a)",
        {"pid": protocol_id, "aid": atom_ids[0]},
    )
    print(f"  done: {protocol_id} ({len(atoms)} atoms)")


def main():
    print("=== Seeding graph-native protocols ===")
    seed_protocol(
        "protocol-progress-score",
        "Progress Score - classify signals, produce weighted ProgressEvents",
        PROGRESS_ATOMS, "deep",
    )
    seed_protocol(
        "protocol-lifecycle",
        "Lifecycle - detect stalled/active/complete transitions",
        LIFECYCLE_ATOMS, "deep",
    )
    print("=== Complete ===")


if __name__ == "__main__":
    main()
