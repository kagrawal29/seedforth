MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'work.execute' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (e:ExecutionSession {node_id:$attempt,scope_id:scope,actor:$actor})-[:EXECUTES]->(w:WorkItem {scope_id:scope})
RETURN e.node_id AS attempt,e.status AS status,e.fence AS fence,w.node_id AS work_id,
w.lease_until AS lease_until,w.state_version AS work_version,w.hold AS hold
