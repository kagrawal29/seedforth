// Phase 1 — enact the 4 pending invariant proposals as live Invariants (2026-08-20)
// Each becomes an :Invariant with check_cypher + heal_protocol, and the proposal is
// marked enacted. The immune system (run-invariants.py) then enforces them.

// ---- 1. Metric sanity -------------------------------------------------------
MERGE (i:Invariant {node_id: 'inv-metric-sanity'})
SET i.label = 'Metric sanity - active agents must report real spend',
    i.severity = 'medium',
    i.project = 'system',
    i.check_cypher = 'MATCH (sa:SubAgent {status:"active"}) WHERE NOT EXISTS { MATCH (sa)<-[:HAS_AGENT]-(p:Project) MATCH (m:Metric {agent: sa.name, metric:"cost_usd"}) WHERE m.value > 0 AND m.created_at > datetime() - duration({days: 3}) } RETURN sa.name AS agent_without_metrics',
    i.heal_protocol = 'MATCH (sa:SubAgent {status:"active"}) WHERE NOT EXISTS { MATCH (sa)<-[:HAS_AGENT]-(p:Project) MATCH (m:Metric {agent: sa.name, metric:"cost_usd"}) WHERE m.value > 0 AND m.created_at > datetime() - duration({days: 3}) } MERGE (ap:ActionProposal {node_id: "ap-metric-gap-" + sa.name}) SET ap.type="metric_gap", ap.description="Agent " + sa.name + " has no real spend in 3 days - investigate idle vs broken collector", ap.status="pending", ap.project="system", ap.generated_at=datetime() RETURN count(sa) AS flagged';

MATCH (ip:InvariantProposal {node_id: 'proposal-metric-sanity---active-agents-must-report-real-s'}) SET ip.status = 'enacted';

// ---- 2. Hebbian activity ----------------------------------------------------
MERGE (i:Invariant {node_id: 'inv-hebbian-activity'})
SET i.label = 'Hebbian activity - agents must query the graph weekly',
    i.severity = 'medium',
    i.project = 'system',
    i.check_cypher = 'MATCH (qt:QueryTrace) WHERE qt.created_at > datetime() - duration({days: 7}) WITH count(qt) AS reads_last_week RETURN CASE WHEN reads_last_week < 10 THEN 10 - reads_last_week ELSE 0 END AS violations',
    i.heal_protocol = 'MERGE (ap:ActionProposal {node_id: "ap-hebbian-nudge"}) SET ap.type="hebbian_low", ap.description="Graph reads below threshold this week - agents must ground from the graph before responding", ap.status="pending", ap.project="system", ap.generated_at=datetime() RETURN 1';

MATCH (ip:InvariantProposal {node_id: 'proposal-hebbian-activity---agents-must-query-the-graph-w'}) SET ip.status = 'enacted';

// ---- 3. Fatal agent quarantine ----------------------------------------------
MERGE (i:Invariant {node_id: 'inv-fatal-agent-quarantine'})
SET i.label = 'Fatal agent quarantine - crash-loops stop nagging after 2 days',
    i.severity = 'high',
    i.project = 'system',
    i.check_cypher = 'MATCH (ap:ActionProposal {type:"agent_fatal", status:"pending"}) WHERE ap.generated_at < datetime() - duration({days: 2}) RETURN count(ap) AS stale_fatal_proposals',
    i.heal_protocol = 'MATCH (ap:ActionProposal {type:"agent_fatal", status:"pending"}) WHERE ap.generated_at < datetime() - duration({days: 2}) SET ap.status="quarantined", ap.escalated_at=datetime() RETURN count(ap) AS quarantined';

MATCH (ip:InvariantProposal {node_id: 'proposal-fatal-agent-quarantine---crash-loops-stop-naggin'}) SET ip.status = 'enacted';

// ---- 4. Telemetry hygiene (already approved, now enacted) -------------------
MERGE (i:Invariant {node_id: 'inv-telemetry-hygiene'})
SET i.label = 'Telemetry hygiene - expire stale alerts and redundant snapshots',
    i.severity = 'low',
    i.project = 'system',
    i.check_cypher = 'MATCH (l:LivenessAlert) WHERE l.detected_at < datetime() - duration({days: 2}) WITH count(l) AS stale_alerts MATCH (s:Snapshot) WHERE s.created_at < datetime() - duration({days: 2}) WITH stale_alerts, count(s) AS old_snapshots RETURN stale_alerts + old_snapshots AS violations',
    i.heal_protocol = 'MATCH (l:LivenessAlert) WHERE l.detected_at < datetime() - duration({days: 2}) WITH count(l) AS removed MATCH (s:Snapshot) WHERE s.created_at < datetime() - duration({days: 2}) WITH removed, s ORDER BY s.created_at DESC WITH removed, collect(s)[0] AS keep, collect(s)[1..] AS drop FOREACH (s IN drop | DETACH DELETE s) RETURN removed AS deleted_alerts';

MATCH (ip:InvariantProposal {node_id: 'proposal-telemetry-hygiene---expire-stale-alerts-and-redu'}) SET ip.status = 'enacted';
