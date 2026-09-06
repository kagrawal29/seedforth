MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'read' IN grant.permissions AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
WITH DISTINCT grant.scope AS scope
MATCH (w:WorkItem {node_id:$id,scope_id:scope})
OPTIONAL MATCH (t:StateTransition {scope_id:scope})-[:CHANGED]->(w)
RETURN t.node_id AS id,t.from_state AS from_state,t.to_state AS to_state,t.actor AS actor,t.created_at AS created_at
ORDER BY created_at DESC LIMIT 100
