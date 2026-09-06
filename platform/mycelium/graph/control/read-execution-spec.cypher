MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'work.execute' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (e:ExecutionSession {node_id:$attempt,scope_id:scope,actor:$actor,status:'running'})-[:EXECUTES]->(w:WorkItem {scope_id:scope})
WHERE w.hold=false AND w.fence=e.fence AND w.lease_until>datetime()
RETURN w.execution_capability AS capability,w.execution_arguments AS arguments_json
