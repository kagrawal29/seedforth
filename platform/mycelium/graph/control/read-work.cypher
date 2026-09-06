MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'read' IN grant.permissions AND (grant.expires_at IS NULL OR grant.expires_at > datetime())
WITH DISTINCT grant.scope AS scope
MATCH (w:WorkItem {scope_id:scope})
OPTIONAL MATCH (agent:SubAgent {node_id:w.assignee_id})
RETURN w.node_id AS id,w.title AS title,w.status AS status,w.state_version AS version,
w.acceptance AS acceptance,w.verification_status AS verification_status,
w.updated_at AS updated_at,w.hold AS hold,agent.node_id AS assignee
ORDER BY updated_at DESC LIMIT 200
