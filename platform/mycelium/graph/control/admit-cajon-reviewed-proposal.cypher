// Explicit owner-delegated pilot admission, not a worker-exposed operation.
MATCH (s:ControlScope {node_id:'cajon-sensei',work_enabled:false})
MATCH (w:WorkItem {node_id:'wi-cajon-partial-loop-credit',scope_id:s.node_id,status:'proposed',hold:true,state_version:0})
MATCH (w)-[:AUTHORIZED_BY]->(m:Mandate {node_id:'mandate-cajon-candidate-pilot-v1',enabled:true})-[:HAS_BUDGET]->(b:Budget)
MATCH (t:TestRun {node_id:'cajon-candidate-browser-dad62bbc229a',status:'passed',artifact_hash:$expected_hash})
WHERE m.expires_at>datetime()+duration('PT5M') AND b.spent_units=0 AND b.reserved_units=0
AND t.source_revision=$revision AND t.recorded_at>datetime()-duration('PT1H')
SET s.work_enabled=true,s.max_parallel_attempts=1,s.updated_at=datetime(),
w.hold=false,w.state_version=1,w.execution_capability='capability-code-proposal-v1',
w.execution_arguments=$arguments,w.expected_candidate_hash=$expected_hash,w.updated_at=datetime()
CREATE (d:Decision {node_id:'decision-cajon-pilot-admission-v1',scope_id:s.node_id,
actor:'principal-seedforth-owner',authority:'owner-upgrade-delegation-20260906',
outcome:'bounded_candidate_attempt_enabled',created_at:datetime()})
CREATE (d)-[:CONCERNS]->(w)
RETURN w.node_id AS id,w.state_version AS version
