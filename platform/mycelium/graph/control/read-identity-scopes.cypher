MATCH (principal:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {revoked:false})
WHERE 'read' IN grant.permissions AND (grant.expires_at IS NULL OR grant.expires_at > datetime())
MATCH (scope:ControlScope {node_id:grant.scope})
RETURN DISTINCT scope.node_id AS scope
ORDER BY scope
