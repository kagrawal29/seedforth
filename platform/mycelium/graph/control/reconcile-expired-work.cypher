MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'work.reconcile' IN grant.permissions AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
WITH DISTINCT grant.scope AS scope
MATCH (e:ExecutionSession {scope_id:scope,status:'running'})-[:EXECUTES]->(w:WorkItem {scope_id:scope})
WHERE w.lease_until<=datetime()
WITH e,w ORDER BY w.node_id LIMIT 100
SET w._lock=coalesce(w._lock,0)+1
WITH e,w WHERE e.status='running' AND w.status='in_progress'
AND e.fence=w.fence AND w.lease_until<=datetime()
SET e.status='unknown',e.reconciled_at=datetime(),e.error_code='lease_expired',
w.status='blocked',w.hold=true,w.blocked_reason='attempt_outcome_unknown',
w.state_version=w.state_version+1,w.fence=w.fence+1,w.lease_until=null,w.updated_at=datetime()
CREATE (t:StateTransition {node_id:randomUUID(),scope_id:$scope,actor:$actor,
from_state:'in_progress',to_state:'blocked',reason:'lease_expired',created_at:datetime()})
CREATE (t)-[:CHANGED]->(w)
CREATE (t)-[:RECONCILES]->(e)
RETURN w.node_id AS id,e.node_id AS attempt,e.status AS attempt_status,w.state_version AS version
