MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'work.execute' IN g.permissions AND 'read' IN g.permissions
AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (i:Invocation {node_id:$invocation,scope_id:scope,actor:$actor,status:'succeeded'})
WHERE i.artifact_hash IS NOT NULL AND i.artifact_ref IS NOT NULL
RETURN i.node_id AS id,i.capability AS capability,i.artifact_hash AS artifact_hash,i.artifact_ref AS artifact_ref
