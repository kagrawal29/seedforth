MATCH (principal:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'work.execute' IN grant.permissions AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
WITH DISTINCT principal,grant.scope AS scope
MATCH (s:ControlScope {node_id:scope,work_enabled:true})
MATCH (principal)-[:REPRESENTS]->(agent:SubAgent)
MATCH (w:WorkItem {node_id:$id,scope_id:scope})
MATCH (w)-[:AUTHORIZED_BY]->(m:Mandate {node_id:w.mandate_id,scope_id:scope,enabled:true})
SET s._lock=coalesce(s._lock,0)+1,w._lock=coalesce(w._lock,0)+1
WITH w,agent,m,s WHERE s.work_enabled=true AND w.status='ready' AND w.hold=false AND w.state_version=$version
AND m.expires_at>datetime()
AND COUNT { MATCH (other:ExecutionSession {scope_id:$scope,status:'running'}) } < coalesce(s.max_parallel_attempts,1)
AND NOT EXISTS { MATCH (w)-[:DEPENDS_ON]->(d) WHERE coalesce(d.status,'unknown')<>'done' OR coalesce(d.hold,false)=true }
SET w.status='in_progress',w.state_version=w.state_version+1,w.updated_at=datetime(),
w.fence=coalesce(w.fence,0)+1,w.lease_until=datetime()+duration({seconds:90}),w.assignee_id=agent.node_id
CREATE (e:ExecutionSession {node_id:$attempt,scope_id:$scope,project:$scope,actor:$actor,
status:'running',started_at:datetime(),fence:w.fence,work_version:w.state_version,mandate_version:m.version,mandate_id:m.node_id})
CREATE (e)-[:EXECUTES]->(w)
CREATE (e)-[:PERFORMED_BY]->(agent)
MERGE (w)-[:ASSIGNED_TO]->(agent)
CREATE (t:StateTransition {node_id:$event_id,scope_id:$scope,actor:$actor,from_state:'ready',to_state:'in_progress',created_at:datetime()})
CREATE (t)-[:CHANGED]->(w)
RETURN w.node_id AS id,e.node_id AS attempt,w.fence AS fence,w.state_version AS version,w.lease_until AS lease_until
