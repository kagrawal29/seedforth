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
        "atom-progress-classify-deploys",
        "Deploy signals score 1.2 (live URL confirmed)",
        "MATCH (s:DeploySignal) WHERE s.classified IS NULL "
        "SET s.is_real = true, s.weight = 1.2, s.classified = true",
    ),
    (
        "atom-progress-classify-outcomes",
        "Outcome signals score by magnitude: base 2.0, +0.2 per lead, capped at 5.0",
        "MATCH (s:OutcomeSignal) WHERE s.classified IS NULL "
        "WITH s, CASE "
        "WHEN s.kind = 'lead' THEN 2.0 + 0.2 * coalesce(toFloat(s.count), 1.0) "
        "WHEN s.kind = 'deal' THEN 3.0 + 0.1 * coalesce(toFloat(s.count), 1.0) "
        "WHEN s.kind = 'revenue' THEN 3.0 "
        "WHEN s.kind = 'sales' THEN 3.0 "
        "ELSE 2.0 END AS weight "
        "SET s.is_real = true, s.weight = CASE WHEN weight > 5.0 THEN 5.0 ELSE weight END, "
        "s.classified = true",
    ),
    (
        "atom-progress-promote-events",
        "Promote weighted classified signals to ProgressEvent nodes",
        "MATCH (s) WHERE (s:CommitSignal OR s:OutboxSignal OR s:ArtifactSignal "
        "OR s:DeploySignal OR s:OutcomeSignal) "
        "AND s.classified = true AND s.weight > 0 AND NOT ((s)-[:EVIDENCE]->()) "
        "CREATE (pe:ProgressEvent {node_id: 'pe-' + s.entity + '-' + s.node_id, "
        "entity: s.entity, marker: labels(s)[0], "
        "evidence: coalesce(s.message, s.text_preview, s.path, s.url), "
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
        "f.updated_at = datetime(), f.project = entity "
        "WITH f MATCH (p:Project {node_id: 'project-' + f.entity}) "
        "MERGE (f)-[:ASSESSES {decay_protected:true}]->(p)",
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
        "MATCH (p:Project {lifecycle_state: 'active'})-[:HAS_AGENT]->() "
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
        "MATCH (p:Project {lifecycle_state: 'active'})-[:HAS_AGENT]->() "
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
    (
        "atom-goal-lifecycle",
        "Mark EntityGoals done when their project reaches complete state",
        "MATCH (g:EntityGoal {status: 'active'}) "
        "MATCH (p:Project {name: g.project, lifecycle_state: 'complete'}) "
        "SET g.status = 'done', g.completed_at = datetime() "
        "CREATE (ge:GoalEvent {node_id: 'ge-' + g.node_id + '-' + toString(timestamp()), "
        "entity: g.project, goal: g.goal, from_status: 'active', to_status: 'done', "
        "reason: 'Project reached complete lifecycle state', "
        "triggered_by: 'auto-rule', created_at: datetime(), project: g.project}) "
        "MERGE (ge)-[:GOAL_TRANSITION {decay_protected:true}]->(g)",
    ),
]

DIRECTION_ATOMS = [
    (
        "atom-dir-link-events",
        "Link recent ProgressEvents to EntityGoals via LLM semantic matching",
        "EXTERNAL:/opt/delta/tools/direction-linker.py",
    ),
    (
        "atom-dir-goal-progress",
        "Goal progress component: share of goals with directed evidence in 30d",
        "MATCH (g:EntityGoal) "
        "OPTIONAL MATCH (g)<-[:DIRECTED]-(pe:ProgressEvent) "
        "WHERE pe.created_at > datetime() - duration({days: 30}) "
        "WITH g, count(pe) AS directed_events "
        "WITH g.project AS entity, count(g) AS total, "
        "sum(CASE WHEN directed_events > 0 THEN 1.0 ELSE 0.0 END) AS progressed "
        "MERGE (d:DirectionScore {entity: entity, node_id: 'ds-' + entity}) "
        "SET d.project = entity, "
        "d.goal_progress = CASE WHEN total > 0 THEN progressed / total ELSE 0.0 END, "
        "d.updated_at = datetime() "
        "WITH d MATCH (p:Project {node_id: 'project-' + d.entity}) "
        "MERGE (d)-[:ASSESSES {decay_protected:true}]->(p)",
    ),
    (
        "atom-dir-alignment",
        "Alignment component: share of recent events that map to a declared goal",
        "MATCH (pe:ProgressEvent) "
        "WHERE pe.created_at > datetime() - duration({days: 30}) "
        "WITH pe.entity AS entity, count(pe) AS total, "
        "sum(CASE WHEN (pe)-[:DIRECTED]->() THEN 1.0 ELSE 0.0 END) AS aligned "
        "MERGE (d:DirectionScore {entity: entity, node_id: 'ds-' + entity}) "
        "SET d.project = entity, "
        "d.alignment = CASE WHEN total > 0 THEN aligned / total ELSE 0.0 END, "
        "d.updated_at = datetime()",
    ),
    (
        "atom-dir-focus",
        "Focus component: even spread across goals lowers the score",
        "MATCH (g:EntityGoal) "
        "OPTIONAL MATCH (g)<-[:DIRECTED]-(pe:ProgressEvent) "
        "WHERE pe.created_at > datetime() - duration({days: 30}) "
        "WITH g, count(pe) AS events_per_goal "
        "WITH g.project AS entity, sum(events_per_goal) AS total, "
        "sum(events_per_goal * events_per_goal) AS sumsq "
        "MERGE (d:DirectionScore {entity: entity, node_id: 'ds-' + entity}) "
        "SET d.project = entity, "
        "d.focus = CASE WHEN total > 0 THEN sumsq / (total * total) ELSE 0.0 END, "
        "d.updated_at = datetime()",
    ),
    (
        "atom-dir-composite",
        "Composite DirectionScore: 0.4 goal_progress + 0.3 alignment + 0.3 focus",
        "MATCH (d:DirectionScore) "
        "WITH d, round(1000 * "
        "(0.4 * coalesce(d.goal_progress, 0) + "
        "0.3 * coalesce(d.alignment, 0) + "
        "0.3 * coalesce(d.focus, 0))) / 1000.0 AS sc "
        "SET d.direction_score = sc, "
        "d.direction_label = CASE "
        "WHEN sc >= 0.7 THEN 'aligned' "
        "WHEN sc >= 0.4 THEN 'developing' "
        "WHEN sc >= 0.15 THEN 'drifting' "
        "ELSE 'stalled' END, "
        "d.updated_at = datetime()",
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
        if cypher.startswith("EXTERNAL:"):
            script = cypher.split("EXTERNAL:", 1)[1]
            q_strict(
                "MERGE (a:ExternalAtom {node_id:$aid}) SET a.semantic=$sem, "
                "a.script=$script, a.project='system', a.updated_at=datetime()",
                {"aid": atom_id, "sem": semantic, "script": script},
            )
        else:
            q_strict(
                "MERGE (a:CypherAtom {node_id:$aid}) SET a.semantic=$sem, a.cypher=$c, "
                "a.project='system', a.updated_at=datetime()",
                {"aid": atom_id, "sem": semantic, "c": cypher},
            )
        atom_ids.append(atom_id)
        if i > 0:
            q_strict(
                "MATCH (a1) WHERE (a1:CypherAtom OR a1:ExternalAtom) AND a1.node_id=$a1 "
                "MATCH (a2) WHERE (a2:CypherAtom OR a2:ExternalAtom) AND a2.node_id=$a2 "
                "MERGE (a1)-[:FOLLOWS {decay_protected:true}]->(a2)",
                {"a1": atom_ids[i - 1], "a2": atom_id},
            )
    q_strict(
        "MATCH (p:Protocol {node_id:$pid})-[r:FIRST_ATOM]->(old) DELETE r",
        {"pid": protocol_id},
    )
    q_strict(
        "MATCH (p:Protocol {node_id:$pid}) "
        "MATCH (a) WHERE (a:CypherAtom OR a:ExternalAtom) AND a.node_id=$aid "
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
    seed_protocol(
        "protocol-direction",
        "Direction - goal progress, alignment, focus -> DirectionScore",
        DIRECTION_ATOMS, "deep",
    )
    print("=== Complete ===")


if __name__ == "__main__":
    main()
