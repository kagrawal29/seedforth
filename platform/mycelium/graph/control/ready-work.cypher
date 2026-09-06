MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'work.schedule' IN grant.permissions AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
WITH DISTINCT grant.scope AS scope
MATCH (s:ControlScope {node_id:scope,work_enabled:true})
MATCH (w:WorkItem {node_id:$id,scope_id:scope})
SET w._lock=coalesce(w._lock,0)+1
WITH w WHERE w.state_version=$version AND w.status='proposed' AND w.hold=false
SET w.status='ready',w.state_version=w.state_version+1,w.updated_at=datetime()
CREATE (t:StateTransition {node_id:$event_id,scope_id:$scope,actor:$actor,from_state:'proposed',to_state:'ready',created_at:datetime()})
CREATE (t)-[:CHANGED]->(w)
RETURN w.node_id AS id,w.status AS status,w.state_version AS version
