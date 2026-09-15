// Recover a foundation WorkItem only after a diagnosed bounded-loop failure.
// This is not a generic retry: the failure class and explicit reason are fenced.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'work.schedule' IN grant.permissions
  AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
WITH DISTINCT grant.scope AS scope
MATCH (w:WorkItem {node_id:$id,scope_id:scope})
WHERE w.project='mycelium'
  AND w.workstream_id='workstream-system-awareness-metabolism'
  AND w.status='blocked'
  AND w.last_attempt_error CONTAINS 'tool loop limit exceeded'
SET w._lock=coalesce(w._lock,0)+1
WITH w WHERE w.state_version=$version
SET w.status='ready',
    w.hold=false,
    w.execution_eligible=true,
    w.retry_reason=$reason,
    w.retry_approved_by=$actor,
    w.retry_approved_at=datetime(),
    w.state_version=w.state_version+1,
    w.updated_at=datetime()
CREATE (t:StateTransition {node_id:$event_id,scope_id:$scope,actor:$actor,
    from_state:'blocked',to_state:'ready',created_at=datetime(),
    reason:'diagnosed_tool_loop_recovery'})
CREATE (t)-[:CHANGED]->(w)
RETURN w.node_id AS id,w.status AS status,w.execution_eligible AS execution_eligible,
       w.state_version AS version;
