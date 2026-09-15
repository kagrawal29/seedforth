// Private code-proposal pilot authority. No scope enablement or task scheduling.
MERGE (p:Principal {node_id:'principal-capability-broker'})
ON CREATE SET p.kind='service',p.enabled=true,p.created_at=datetime()
WITH p
MATCH (s:ControlScope {node_id:'cajon-sensei'})
MERGE (g:Grant {node_id:'grant-capability-broker-cajon'})
ON CREATE SET g.scope=s.node_id,g.permissions=['invocation.settle'],g.revoked=false,g.created_at=datetime()
MERGE (p)-[:HAS_GRANT]->(g);

MERGE (p:Principal {node_id:'principal-cajon-upgrade-worker'})
ON CREATE SET p.kind='isolated_worker',p.enabled=true,p.created_at=datetime()
MERGE (a:SubAgent {node_id:'agent-cajon-upgrade-worker'})
ON CREATE SET a.project='cajon-sensei',a.role='bounded_code_proposal',a.status='provisioned_not_running'
MERGE (p)-[:REPRESENTS]->(a)
MERGE (g:Grant {node_id:'grant-cajon-upgrade-worker'})
ON CREATE SET g.scope='cajon-sensei',g.permissions=['read','work.execute'],g.revoked=false,
g.created_at=datetime(),g.expires_at=datetime($expires_at),g.authority='owner-upgrade-delegation-20260906'
MERGE (p)-[:HAS_GRANT]->(g);

UNWIND $capabilities AS capability
MERGE (c:Capability {node_id:capability.id})
SET c.enabled=true,c.policy_generation=capability.generation,c.cost_units=capability.cost_units,
c.max_seconds=capability.max_seconds,c.updated_at=datetime(),c.effect_class='private_candidate_artifact_only';

MATCH (w:WorkItem {node_id:'wi-cajon-partial-loop-credit',scope_id:'cajon-sensei'})
MERGE (m:Mandate {node_id:'mandate-cajon-candidate-pilot-v1'})
ON CREATE SET m.scope_id='cajon-sensei',m.enabled=true,m.version=1,
m.expires_at=datetime($expires_at),m.budget_id='budget-cajon-candidate-pilot-v1',
m.allowed_capabilities=['capability-code-snapshot-v1','capability-code-proposal-v1'],
m.authority='owner-upgrade-delegation-20260906',m.created_at=datetime()
MERGE (b:Budget {node_id:'budget-cajon-candidate-pilot-v1'})
ON CREATE SET b.scope_id='cajon-sensei',b.total_units=2,b.reserved_units=0,b.spent_units=0,
b.unit='bounded_artifact_invocation',b.monetary_spend_authorized=false
MERGE (m)-[:HAS_BUDGET]->(b)
MERGE (w)-[:AUTHORIZED_BY]->(m)
SET w.mandate_id=m.node_id;
