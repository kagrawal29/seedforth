// Owner-only preparation for one short-lived Flowing Indian candidate run.
// Creates authority and held work only; it never enables the scope or deploys code.
MATCH (owner:Principal {node_id:$actor,enabled:true})
WHERE $actor='principal-seedforth-owner'
MATCH (owner)-[:HAS_GRANT]->(control:Grant {scope:'flowing-indian',revoked:false})
WHERE 'work.control' IN control.permissions
  AND (control.expires_at IS NULL OR control.expires_at>datetime())
MATCH (s:ControlScope {node_id:'flowing-indian',work_enabled:false})
      -[:MAPS_PROJECT]->(p:Project {node_id:'project-flowing-indian',portfolio_state:'active',new_work:'held'})
WHERE size($run_id)>=8 AND size($run_id)<=96
  AND size($work_id)>=8 AND size($work_id)<=128
  AND size($arguments_json)>=2 AND size($arguments_json)<=28000
  AND datetime($expires_at)>datetime()
  AND datetime($expires_at)<=datetime()+duration('PT1H')
MERGE (worker:Principal {node_id:'principal-flowing-upgrade-worker'})
ON CREATE SET worker.kind='isolated_worker',worker.enabled=true,worker.created_at=datetime()
MERGE (agent:SubAgent {node_id:'agent-flowing-upgrade-worker'})
ON CREATE SET agent.project='flowing-indian',agent.role='bounded_code_proposal',agent.status='provisioned_not_running'
MERGE (worker)-[:REPRESENTS]->(agent)
MERGE (grant:Grant {node_id:'grant-flowing-bounded-'+$run_id})
ON CREATE SET grant.scope='flowing-indian',grant.permissions=['read','work.execute'],
    grant.revoked=false,grant.created_at=datetime(),grant.expires_at=datetime($expires_at),
    grant.authority='owner-bounded-run'
MERGE (mandate:Mandate {node_id:'mandate-flowing-bounded-'+$run_id})
ON CREATE SET mandate.scope_id='flowing-indian',mandate.enabled=true,mandate.version=1,
    mandate.expires_at=datetime($expires_at),mandate.budget_id='budget-flowing-bounded-'+$run_id,
    mandate.allowed_capabilities=['capability-code-proposal-v1'],
    mandate.authority='owner-bounded-run',mandate.created_at=datetime()
MERGE (budget:Budget {node_id:'budget-flowing-bounded-'+$run_id})
ON CREATE SET budget.scope_id='flowing-indian',budget.total_units=1,budget.reserved_units=0,
    budget.spent_units=0,budget.unit='bounded_candidate_invocation',budget.monetary_spend_authorized=false
MERGE (mandate)-[:HAS_BUDGET]->(budget)
MERGE (w:WorkItem {node_id:$work_id})
ON CREATE SET w.scope_id='flowing-indian',w.project='flowing-indian',w.title=$title,
    w.acceptance=$acceptance,w.status='proposed',w.hold=true,w.state_version=0,
    w.verification_status='unverified',w.execution_capability='capability-code-proposal-v1',
    w.execution_arguments=$arguments_json,w.assignee_id=agent.node_id,w.created_at=datetime(),
    w.updated_at=datetime(),w.authority='owner-bounded-run'
WITH s,w,mandate,grant
WHERE w.scope_id='flowing-indian' AND w.status='proposed' AND w.hold=true
  AND w.state_version=0 AND w.execution_capability='capability-code-proposal-v1'
SET w.mandate_id=mandate.node_id
MERGE (w)-[:AUTHORIZED_BY]->(mandate)
CREATE (signal:Signal {node_id:'signal-flowing-bounded-'+$run_id,scope_id:'flowing-indian',
    issuer:$actor,type:'bounded_run_authorized',status:'accepted',created_at:datetime(),
    result:'held_candidate_work_prepared',work_id:w.node_id,mandate_id:mandate.node_id})
CREATE (signal)-[:TARGETS]->(w)
RETURN w.node_id AS work_id,mandate.node_id AS mandate_id,grant.node_id AS grant_id,
       w.status AS status,w.hold AS hold
