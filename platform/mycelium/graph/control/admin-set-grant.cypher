MATCH (owner:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(owner_grant:Grant {scope:'seedforth-platform',revoked:false})
WHERE 'work.control' IN owner_grant.permissions
  AND $target_scope IN ['flowing-indian','cajon-sensei']
MATCH (:Principal {node_id:$principal})-[:HAS_GRANT]->(g:Grant {scope:$target_scope})
SET g.revoked=$revoked,g.updated_at=datetime(),g.authority='owner-admin'
RETURN $principal AS principal,g.scope AS scope,g.permissions AS permissions,g.revoked AS revoked
