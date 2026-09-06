MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'work.execute' IN grant.permissions AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
WITH DISTINCT grant.scope AS scope
MATCH (:ControlScope {node_id:scope,work_enabled:true})
MATCH (e:ExecutionSession {node_id:$attempt,scope_id:scope,actor:$actor,status:'running'})-[:EXECUTES]->(w:WorkItem {scope_id:scope})
SET w._lock=coalesce(w._lock,0)+1
WITH e,w WHERE w.status='in_progress' AND w.hold=false
AND e.fence=w.fence AND w.fence=$fence AND w.lease_until>datetime()
SET w.lease_until=datetime()+duration({seconds:90}),e.last_heartbeat_at=datetime()
RETURN e.node_id AS attempt,w.fence AS fence,w.lease_until AS lease_until
