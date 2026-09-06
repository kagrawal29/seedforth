MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'work.control' IN grant.permissions AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
WITH DISTINCT grant.scope AS scope
MATCH (w:WorkItem {node_id:$id,scope_id:scope})
SET w._lock=coalesce(w._lock,0)+1
WITH w WHERE w.state_version=$version AND NOT w.status IN ['done','cancelled']
SET w.hold=$hold,w.state_version=w.state_version+1,w.updated_at=datetime()
CREATE (s:Signal {node_id:$event_id,scope_id:$scope,issuer:$actor,type:CASE WHEN $hold THEN 'pause' ELSE 'resume' END,
status:'accepted',created_at:datetime(),result:'dispatch_hold_changed'})
CREATE (s)-[:TARGETS]->(w)
RETURN w.node_id AS id,w.status AS status,w.state_version AS version,w.hold AS hold
