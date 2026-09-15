MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'read' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (:ControlScope {node_id:scope})-[:MAPS_PROJECT]->(p:Project)
WHERE NOT EXISTS { MATCH (other:Project {name:p.name}) WHERE other<>p }
MATCH (w:WorkItem {project:p.name}) WHERE w.scope_id IS NULL
RETURN w.node_id AS id,w.title AS title,w.status AS legacy_status,
'legacy_needs_triage' AS status,true AS legacy,'unverified' AS verification_status,
'Historical work: verify intent, acceptance, ownership, and evidence before admitting execution.' AS acceptance,
w.updated_at AS updated_at
ORDER BY id LIMIT 200
