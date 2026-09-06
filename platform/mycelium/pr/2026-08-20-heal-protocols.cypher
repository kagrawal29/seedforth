// Phase 1 — add heal_protocol to the 7 invariants that lack one (2026-08-20)
// Pattern: heal = surface the violation as an ActionProposal (the immune system
// surfaces, steering-executor/human acts).

MATCH (i:Invariant {node_id: 'invariant-scope-boundary'})
SET i.heal_protocol = 'MATCH (k:Knowledge) WHERE k.agent IS NOT NULL AND k.scope IS NOT NULL AND NOT EXISTS { MATCH (o:Organization {name: k.scope}) } MERGE (ap:ActionProposal {node_id: "ap-scope-" + k.node_id}) SET ap.type="scope_violation", ap.description="Knowledge node " + k.node_id + " has scope " + k.scope + " with no matching Organization", ap.status="pending", ap.project="system", ap.generated_at=datetime() RETURN count(k) AS flagged';

MATCH (i:Invariant {node_id: 'invariant-project-liveness'})
SET i.heal_protocol = 'MATCH (p:Project) WHERE p.last_activity < datetime() - duration({hours:48}) MERGE (ap:ActionProposal {node_id: "ap-project-stale-" + p.name}) SET ap.type="project_stale", ap.description="Project " + p.name + " has no activity in 48h - founder should check it", ap.status="pending", ap.project=p.name, ap.generated_at=datetime() RETURN count(p) AS nudged';

MATCH (i:Invariant {node_id: 'invariant-agent-liveness'})
SET i.heal_protocol = 'MATCH (sa:SubAgent) WHERE sa.status="active" AND (sa.updated_at IS NULL OR sa.updated_at < datetime() - duration({hours:24})) MERGE (ap:ActionProposal {node_id: "ap-agent-dead-" + sa.name}) SET ap.type="agent_stale", ap.description="Agent " + sa.name + " heartbeat is stale - restart or investigate", ap.status="pending", ap.project=sa.name, ap.generated_at=datetime() RETURN count(sa) AS flagged';

MATCH (i:Invariant {node_id: 'invariant-fresh-snapshot'})
SET i.heal_protocol = 'MATCH (f:FleetState) WHERE f.updated_at IS NULL OR f.updated_at < datetime() - duration({hours:24}) MERGE (ap:ActionProposal {node_id: "ap-fleet-stale"}) SET ap.type="fleet_stale", ap.description="FleetState is stale - ingest-fleet-state.py may be down", ap.status="pending", ap.project="system", ap.generated_at=datetime() RETURN count(f) AS flagged';

MATCH (i:Invariant {node_id: 'invariant-protocol-health'})
SET i.heal_protocol = 'MATCH (p:Protocol {enabled: true}) WHERE p.cadence IN ["heartbeat","dream","deep"] AND NOT EXISTS { MATCH (p)<-[:RAN]-(pr:ProtocolRun) WHERE pr.timestamp > datetime() - duration({hours: 24}) AND pr.atoms_ok = pr.atoms_total } MERGE (ap:ActionProposal {node_id: "ap-protocol-unhealthy-" + p.node_id}) SET ap.type="protocol_unhealthy", ap.description="Protocol " + p.node_id + " has no successful run in 24h", ap.status="pending", ap.project="system", ap.generated_at=datetime() RETURN count(p) AS flagged';

MATCH (i:Invariant {node_id: 'invariant-steering-consistency'})
SET i.heal_protocol = 'MATCH (p:Project) WHERE p.status IN ["hibernated","hibernating"] MATCH (pe:ProgressEvent {project: p.name}) WHERE (p.hibernated_at IS NULL AND pe.created_at > datetime() - duration({hours: 48})) OR (p.hibernated_at IS NOT NULL AND pe.created_at > p.hibernated_at) WITH p, sum(pe.weight) AS w WHERE w >= 1.0 MERGE (ap:ActionProposal {node_id: "ap-hibernated-work-" + p.name}) SET ap.type="hibernated_work", ap.description="Hibernated project " + p.name + " produced work - inconsistent steering", ap.status="pending", ap.project=p.name, ap.generated_at=datetime() RETURN count(p) AS flagged';

MATCH (i:Invariant {node_id: 'inv-governance-provenance'})
SET i.heal_protocol = 'MATCH (i:Invariant) WHERE i.governed <> "constitutional" AND NOT EXISTS { MATCH (:InvariantDecision {decision:"approve"})-[:GOVERNS]->(i) } MERGE (ap:ActionProposal {node_id: "ap-ungoverned-" + i.node_id}) SET ap.type="ungoverned_invariant", ap.description="Invariant " + i.node_id + " lacks an approved governance decision", ap.status="pending", ap.project="system", ap.generated_at=datetime() RETURN count(i) AS flagged';
