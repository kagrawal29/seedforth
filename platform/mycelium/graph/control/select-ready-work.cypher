MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'work.execute' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (s:ControlScope {node_id:scope,work_enabled:true})
MATCH (:Principal {node_id:$actor})-[:REPRESENTS]->(agent:SubAgent)
MATCH (w:WorkItem {scope_id:scope,status:'ready',hold:false})
MATCH (w)-[:AUTHORIZED_BY]->(m:Mandate {node_id:w.mandate_id,scope_id:scope,enabled:true})
WHERE m.expires_at>datetime()
AND NOT EXISTS { MATCH (w)-[:DEPENDS_ON]->(d) WHERE coalesce(d.status,'unknown')<>'done' OR coalesce(d.hold,false)=true }
AND COUNT { MATCH (other:ExecutionSession {scope_id:scope,status:'running'}) } < coalesce(s.max_parallel_attempts,1)
RETURN w.node_id AS id,w.title AS title,w.state_version AS version,w.updated_at AS updated_at,
w.execution_capability AS capability,m.node_id AS mandate_id,m.version AS mandate_version
ORDER BY w.updated_at ASC,w.node_id ASC LIMIT 10
