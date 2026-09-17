// ============================================================================
// AUTONOMY CONTRACTS — System-level graph-native state machine
// Deployed as CypherAtoms. Each atom defines AND enforces one transition.
// ============================================================================

// ---------------------------------------------------------------------------
// CONTRACT 1: WORK LIFECYCLE — the WorkItem state machine
// ---------------------------------------------------------------------------

// atom: admit-work-to-ready
MERGE (a:CypherAtom {node_id: 'atom-admit-work-to-ready'})
SET a.semantic = 'Admit a proposed WorkItem to ready when all preconditions pass',
    a.cypher = 'MATCH (w:WorkItem {status: "proposed"}) WHERE coalesce(w.execution_eligible, true)=true AND coalesce(w.operational_status, "active")="active" WITH w OPTIONAL MATCH (w)-[:DEPENDS_ON|MAP_DEPENDS_ON]->(dep:WorkItem) WITH w, collect(dep) AS deps WHERE all(d IN deps WHERE d.status="done") SET w.status="ready", w.admitted_at=datetime(), w.updated_at=datetime(), w.state_version=coalesce(w.state_version,0)+1 CREATE (st:StateTransition {node_id: "st-admit-"+w.node_id+"-"+toString(timestamp()), from_state:"proposed", to_state:"ready", object_type:"WorkItem", object_id:w.node_id, created_at:datetime()}) MERGE (w)-[:HAS_EVENT]->(st) RETURN count(w) AS admitted',
    a.project = 'mycelium',
    a.fire_count = 0;

// atom: claim-work
MERGE (a:CypherAtom {node_id: 'atom-claim-work'})
SET a.semantic = 'Atomically claim a ready WorkItem for execution — sets in_progress, records lease epoch',
    a.cypher = 'MATCH (w:WorkItem {status: "ready"}) WHERE coalesce(w.execution_eligible, true)=true WITH w OPTIONAL MATCH (w)-[:HAS_ATTEMPT]->(ra:RunAttempt) WHERE ra.status IN ["queued","starting","running"] WITH w, count(ra) AS active WHERE active=0 SET w.status="in_progress", w.claimed_at=datetime(), w.updated_at=datetime(), w.state_version=coalesce(w.state_version,0)+1 CREATE (st:StateTransition {node_id: "st-claim-"+w.node_id+"-"+toString(timestamp()), from_state:"ready", to_state:"in_progress", object_type:"WorkItem", object_id:w.node_id, created_at:datetime()}) MERGE (w)-[:HAS_EVENT]->(st) RETURN w.node_id AS workitem, w.status AS new_status ORDER BY w.priority LIMIT 1',
    a.project = 'mycelium',
    a.fire_count = 0;

// atom: finish-work-success
MERGE (a:CypherAtom {node_id: 'atom-finish-work-success'})
SET a.semantic = 'Transition a WorkItem to done when evidence and attempt confirm success',
    a.cypher = 'MATCH (w:WorkItem) WHERE w.status IN ["in_progress","review"] WITH w MATCH (w)-[:HAS_EVIDENCE]->(e:Evidence) WHERE e.result="passed" AND coalesce(e.tests_passed,true)=true AND coalesce(e.policy_passed,true)=true AND coalesce(e.invariants_passed,true)=true WITH w MATCH (w)-[:HAS_ATTEMPT]->(ra:RunAttempt {status: "succeeded"}) WITH w SET w.status="done", w.finished_at=datetime(), w.updated_at=datetime(), w.state_version=coalesce(w.state_version,0)+1 CREATE (st:StateTransition {node_id: "st-done-"+w.node_id+"-"+toString(timestamp()), from_state:w.status, to_state:"done", object_type:"WorkItem", object_id:w.node_id, created_at:datetime()}) MERGE (w)-[:HAS_EVENT]->(st) RETURN count(w) AS completed',
    a.project = 'mycelium',
    a.fire_count = 0;

// atom: block-work-retry-exhausted
MERGE (a:CypherAtom {node_id: 'atom-block-work-retry-exhausted'})
SET a.semantic = 'Block a WorkItem when all retries are exhausted — records escalation_reason',
    a.cypher = 'MATCH (w:WorkItem) WHERE w.status IN ["in_progress","ready"] WITH w OPTIONAL MATCH (w)-[:HAS_ATTEMPT]->(ra:RunAttempt) WITH w, count(ra) AS total, count(CASE WHEN ra.status IN ["failed","timed_out"] THEN 1 END) AS failures WHERE failures >= coalesce(w.max_attempts,3) SET w.status="blocked", w.escalation_reason="retry_limit_exceeded", w.blocked_at=datetime(), w.updated_at=datetime(), w.state_version=coalesce(w.state_version,0)+1 CREATE (st:StateTransition {node_id: "st-block-"+w.node_id+"-"+toString(timestamp()), from_state:"in_progress", to_state:"blocked", object_type:"WorkItem", object_id:w.node_id, reason:"retry_limit_exceeded", created_at:datetime()}) MERGE (w)-[:HAS_EVENT]->(st) RETURN count(w) AS blocked',
    a.project = 'mycelium',
    a.fire_count = 0;

// atom: recover-work-to-ready
MERGE (a:CypherAtom {node_id: 'atom-recover-work-to-ready'})
SET a.semantic = 'Recover stalled or blocked work back to ready when retries remain',
    a.cypher = 'MATCH (w:WorkItem) WHERE w.status IN ["blocked","in_progress"] WITH w OPTIONAL MATCH (w)-[:HAS_ATTEMPT]->(ra:RunAttempt) WHERE ra.status IN ["queued","starting","running"] WITH w, count(ra) AS active WHERE active=0 WITH w OPTIONAL MATCH (w)-[:HAS_ATTEMPT]->(ra2:RunAttempt) WITH w, count(CASE WHEN ra2.status IN ["failed","timed_out"] THEN 1 END) AS failures WHERE failures < coalesce(w.max_attempts,3) SET w.status="ready", w.recovery_count=coalesce(w.recovery_count,0)+1, w.recovered_at=datetime(), w.updated_at=datetime(), w.state_version=coalesce(w.state_version,0)+1 CREATE (st:StateTransition {node_id: "st-recover-"+w.node_id+"-"+toString(timestamp()), from_state:"blocked", to_state:"ready", object_type:"WorkItem", object_id:w.node_id, created_at:datetime()}) MERGE (w)-[:HAS_EVENT]->(st) RETURN count(w) AS recovered',
    a.project = 'mycelium',
    a.fire_count = 0;

// atom: reconcile-stale-inprogress
MERGE (a:CypherAtom {node_id: 'atom-reconcile-stale-inprogress'})
SET a.semantic = 'Reconcile WorkItems stuck in in_progress — return to ready if no active attempts',
    a.cypher = 'MATCH (w:WorkItem {status: "in_progress"}) WHERE coalesce(w.execution_eligible,true)=true AND coalesce(w.operational_status,"active")="active" WITH w OPTIONAL MATCH (w)-[:HAS_ATTEMPT]->(ra:RunAttempt) WHERE ra.status IN ["queued","starting","running"] WITH w, count(ra) AS active WHERE active=0 WITH w OPTIONAL MATCH (w)-[:HAS_ATTEMPT]->(ra2:RunAttempt) WITH w, count(CASE WHEN ra2.status IN ["failed","timed_out"] THEN 1 END) AS failures SET w.status=CASE WHEN failures >= coalesce(w.max_attempts,3) THEN "blocked" ELSE "ready" END, w.escalation_reason=CASE WHEN failures >= coalesce(w.max_attempts,3) THEN "retry_limit_exceeded" ELSE w.escalation_reason END, w.recovery_count=coalesce(w.recovery_count,0)+1, w.recovered_at=datetime(), w.updated_at=datetime() RETURN count(w) AS reconciled',
    a.project = 'mycelium',
    a.fire_count = 0;

// atom: diagnose-blocked-no-reason
MERGE (a:CypherAtom {node_id: 'atom-diagnose-blocked-no-reason'})
SET a.semantic = 'Diagnose WorkItems blocked with no escalation_reason — surface as GapSignal',
    a.cypher = 'MATCH (w:WorkItem {status: "blocked"}) WHERE w.escalation_reason IS NULL OR w.retry_count IS NULL WITH w MERGE (gs:GapSignal {node_id: "gap-zombie-block-"+w.node_id}) SET gs.project=coalesce(w.project,w.scope_id), gs.workitem_id=w.node_id, gs.severity="warning", gs.description="WorkItem blocked with no escalation reason or retry count", gs.detected_at=datetime(), gs.status="open", gs.gap_type="zombie_block" MERGE (w)-[:HAS_DIAGNOSIS]->(gs) RETURN count(gs) AS gaps_found',
    a.project = 'mycelium',
    a.fire_count = 0;

// atom: diagnose-orphaned-workitems
MERGE (a:CypherAtom {node_id: 'atom-diagnose-orphaned-workitems'})
SET a.semantic = 'Diagnose WorkItems with no goal connection — surface as GapSignal',
    a.cypher = 'MATCH (w:WorkItem) WHERE NOT (w)-[:SERVES]->(:EntityGoal) AND NOT (w)-[:PART_OF]->(:Workstream) AND w.status <> "archived" WITH w MERGE (gs:GapSignal {node_id: "gap-orphan-"+w.node_id}) SET gs.project=coalesce(w.project,w.scope_id), gs.workitem_id=w.node_id, gs.severity="warning", gs.description="WorkItem has no goal or workstream connection", gs.detected_at=datetime(), gs.status="open", gs.gap_type="orphaned_workitem" MERGE (w)-[:HAS_DIAGNOSIS]->(gs) RETURN count(gs) AS gaps_found',
    a.project = 'mycelium',
    a.fire_count = 0;

// atom: diagnose-stale-proposed
MERGE (a:CypherAtom {node_id: 'atom-diagnose-stale-proposed'})
SET a.semantic = 'Diagnose WorkItems stuck in proposed despite having succeeded attempts',
    a.cypher = 'MATCH (w:WorkItem {status: "proposed"})-[:HAS_ATTEMPT]->(ra:RunAttempt {status: "succeeded"}) WITH w, count(ra) AS successes WHERE successes > 0 WITH w MERGE (gs:GapSignal {node_id: "gap-stale-proposed-"+w.node_id}) SET gs.project=coalesce(w.project,w.scope_id), gs.workitem_id=w.node_id, gs.severity="warning", gs.description="WorkItem stuck in proposed with succeeded attempts — state machine deadlock", gs.detected_at=datetime(), gs.status="open", gs.gap_type="stale_proposed" MERGE (w)-[:HAS_DIAGNOSIS]->(gs) RETURN count(gs) AS gaps_found',
    a.project = 'mycelium',
    a.fire_count = 0;

// ---------------------------------------------------------------------------
// CONTRACT 2: ATTEMPT — leasing, fencing, expiry, recovery
// ---------------------------------------------------------------------------

// atom: expire-stale-attempts
MERGE (a:CypherAtom {node_id: 'atom-expire-stale-attempts'})
SET a.semantic = 'Expire stale attempts — cancel running attempts with no recent event',
    a.cypher = 'MATCH (a:RunAttempt) WHERE a.status IN ["queued","starting","running"] AND coalesce(a.control_state,"") <> "paused" WITH a WHERE coalesce(a.last_event_at, a.started_at, a.created_at) < datetime() - duration({minutes: 15}) SET a.status="cancelled", a.cancel_reason="stale_attempt", a.finished_at=datetime(), a.last_event_at=datetime() RETURN count(a) AS expired_attempts',
    a.project = 'mycelium',
    a.fire_count = 0;

// atom: diagnose-attempt-no-failure-reason
MERGE (a:CypherAtom {node_id: 'atom-diagnose-attempt-no-failure-reason'})
SET a.semantic = 'Diagnose failed attempts with no failure_reason — missing diagnostics gap',
    a.cypher = 'MATCH (a:RunAttempt) WHERE a.status IN ["failed","timed_out"] AND (a.failure_reason IS NULL OR a.failure_reason="") AND a.error IS NULL RETURN count(a) AS undiagnosed_failures',
    a.project = 'mycelium',
    a.fire_count = 0;

// ---------------------------------------------------------------------------
// CONTRACT 3: EVIDENCE — criteria evaluation
// ---------------------------------------------------------------------------

// atom: evaluate-evidence-for-workitem
MERGE (a:CypherAtom {node_id: 'atom-evaluate-evidence-for-workitem'})
SET a.semantic = 'Evaluate whether a WorkItem has sufficient evidence to transition to done',
    a.cypher = 'MATCH (w:WorkItem) WHERE w.status IN ["in_progress","review"] WITH w MATCH (w)-[:HAS_EVIDENCE]->(e:Evidence) WHERE e.result="passed" AND coalesce(e.tests_passed,true)=true AND coalesce(e.policy_passed,true)=true AND coalesce(e.invariants_passed,true)=true WITH w, count(e) AS evidence_count WHERE evidence_count > 0 RETURN w.node_id AS workitem, w.title AS title, evidence_count AS passing_evidence',
    a.project = 'mycelium',
    a.fire_count = 0;

// atom: diagnose-missing-evidence
MERGE (a:CypherAtom {node_id: 'atom-diagnose-missing-evidence'})
SET a.semantic = 'Diagnose WorkItems with succeeded attempts but no Evidence nodes',
    a.cypher = 'MATCH (w:WorkItem)-[:HAS_ATTEMPT]->(ra:RunAttempt {status: "succeeded"}) WHERE NOT (w)-[:HAS_EVIDENCE]->(:Evidence) WITH DISTINCT w RETURN w.node_id AS workitem, w.status AS status, w.project AS project',
    a.project = 'mycelium',
    a.fire_count = 0;

// ---------------------------------------------------------------------------
// CONTRACT 4: GOAL — progress evaluation
// ---------------------------------------------------------------------------

// atom: evaluate-goal-progress
MERGE (a:CypherAtom {node_id: 'atom-evaluate-goal-progress'})
SET a.semantic = 'Evaluate goal progress — count done WorkItems vs total and update DirectionScore',
    a.cypher = 'MATCH (g:EntityGoal)-[:HAS_WORK_ITEM]->(w:WorkItem) WHERE g.status IN ["active","in_review"] WITH g, count(w) AS total, count(CASE WHEN w.status="done" THEN 1 END) AS completed WITH g, total, completed WHERE total > 0 SET g.progress_pct=round(100.0*completed/total,1), g.completed_items=completed, g.total_items=total, g.evaluated_at=datetime() RETURN g.node_id AS goal, g.goal AS goal_text, g.progress_pct AS progress, completed, total',
    a.project = 'mycelium',
    a.fire_count = 0;

// atom: diagnose-goal-no-workitems
MERGE (a:CypherAtom {node_id: 'atom-diagnose-goal-no-workitems'})
SET a.semantic = 'Diagnose active goals that have no WorkItems — planning gap',
    a.cypher = 'MATCH (g:EntityGoal {status: "active"}) WHERE NOT (g)-[:HAS_WORK_ITEM]->(:WorkItem) WITH g MERGE (gs:GapSignal {node_id: "gap-goal-no-items-"+g.node_id}) SET gs.project=coalesce(g.project,g.scope_id), gs.goal_id=g.node_id, gs.severity="warning", gs.description="Active goal has no WorkItems — no decomposition exists", gs.detected_at=datetime(), gs.status="open", gs.gap_type="goal_no_workitems" RETURN count(gs) AS gaps_found',
    a.project = 'mycelium',
    a.fire_count = 0;

// atom: wire-workitem-to-goal
MERGE (a:CypherAtom {node_id: 'atom-wire-workitem-to-goal'})
SET a.semantic = 'Heal orphaned WorkItems — wire them to matching goals by project scope',
    a.cypher = 'MATCH (w:WorkItem) WHERE NOT (w)-[:SERVES]->(:EntityGoal) AND NOT (w)-[:PART_OF]->(:Workstream) AND w.status <> "archived" WITH w MATCH (g:EntityGoal) WHERE g.project = coalesce(w.project, w.scope_id) AND g.status IN ["active","in_review"] WITH w, g ORDER BY g.created_at LIMIT 1 MERGE (w)-[:SERVES]->(g) SET w.updated_at=datetime() RETURN count(w) AS wired',
    a.project = 'mycelium',
    a.fire_count = 0;

// ---------------------------------------------------------------------------
// CONTRACT 5: FLEET DIAGNOSTICS — health check
// ---------------------------------------------------------------------------

// atom: fleet-health-summary
MERGE (a:CypherAtom {node_id: 'atom-fleet-health-summary'})
SET a.semantic = 'Fleet-wide autonomy health summary — all breakages in one view',
    a.cypher = 'OPTIONAL MATCH (w1:WorkItem {status:"blocked"}) WHERE w1.escalation_reason IS NULL WITH count(w1) AS zombie_blocks OPTIONAL MATCH (w2:WorkItem {status:"proposed"})-[:HAS_ATTEMPT]->(:RunAttempt {status:"succeeded"}) WITH zombie_blocks, count(DISTINCT w2) AS stale_proposed OPTIONAL MATCH (w3:WorkItem {status:"in_progress"}) WHERE NOT (w3)-[:HAS_ATTEMPT]->(:RunAttempt) OR NOT ((w3)-[:HAS_ATTEMPT]->(:RunAttempt {status:"running"}) OR (w3)-[:HAS_ATTEMPT]->(:RunAttempt {status:"queued"}) OR (w3)-[:HAS_ATTEMPT]->(:RunAttempt {status:"starting"})) WITH zombie_blocks, stale_proposed, count(DISTINCT w3) AS stalled_inprogress OPTIONAL MATCH (w4:WorkItem) WHERE NOT (w4)-[:SERVES]->(:EntityGoal) AND w4.status <> "archived" WITH zombie_blocks, stale_proposed, stalled_inprogress, count(DISTINCT w4) AS orphaned OPTIONAL MATCH (a:RunAttempt {status:"failed"}) WHERE a.failure_reason IS NULL WITH zombie_blocks, stale_proposed, stalled_inprogress, orphaned, count(a) AS undiagnosed_failures OPTIONAL MATCH (g:EntityGoal {status:"active"}) WHERE NOT (g)-[:HAS_WORK_ITEM]->(:WorkItem) RETURN zombie_blocks, stale_proposed, stalled_inprogress, orphaned, undiagnosed_failures, count(g) AS goals_without_work',
    a.project = 'mycelium',
    a.fire_count = 0;

// ---------------------------------------------------------------------------
// Wire the diagnostics protocol — runs on heartbeat to detect + report
// ---------------------------------------------------------------------------
MERGE (p:Protocol {node_id: 'protocol-autonomy-diagnostics'})
SET p.label = 'Autonomy Contract Diagnostics — fleet health scan',
    p.cadence = 'heartbeat',
    p.enabled = true,
    p.protocol_type = 'diagnostic',
    p.project = 'mycelium',
    p.description = 'Scans all WorkItems, attempts, evidence, and goals for structural breakages. Creates GapSignal nodes for each detected issue. Non-mutating on work state.';

MATCH (p:Protocol {node_id: 'protocol-autonomy-diagnostics'}),
      (a1:CypherAtom {node_id: 'atom-wire-workitem-to-goal'}),
      (a2:CypherAtom {node_id: 'atom-reconcile-stale-inprogress'}),
      (a3:CypherAtom {node_id: 'atom-block-work-retry-exhausted'}),
      (a4:CypherAtom {node_id: 'atom-finish-work-success'}),
      (a5:CypherAtom {node_id: 'atom-diagnose-blocked-no-reason'}),
      (a6:CypherAtom {node_id: 'atom-diagnose-orphaned-workitems'}),
      (a7:CypherAtom {node_id: 'atom-diagnose-stale-proposed'}),
      (a8:CypherAtom {node_id: 'atom-diagnose-attempt-no-failure-reason'}),
      (a9:CypherAtom {node_id: 'atom-diagnose-goal-no-workitems'}),
      (a10:CypherAtom {node_id: 'atom-fleet-health-summary'})
MERGE (p)-[:FIRST_ATOM]->(a1)
MERGE (a1)-[:FOLLOWS]->(a2)
MERGE (a2)-[:FOLLOWS]->(a3)
MERGE (a3)-[:FOLLOWS]->(a4)
MERGE (a4)-[:FOLLOWS]->(a5)
MERGE (a5)-[:FOLLOWS]->(a6)
MERGE (a6)-[:FOLLOWS]->(a7)
MERGE (a7)-[:FOLLOWS]->(a8)
MERGE (a8)-[:FOLLOWS]->(a9)
MERGE (a9)-[:FOLLOWS]->(a10);

RETURN 'Autonomy contracts deployed: 10 atoms wired as 1 heartbeat protocol' AS result;