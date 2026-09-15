MATCH (owner:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(owner_grant:Grant {scope:'seedforth-platform',revoked:false})
WHERE 'work.control' IN owner_grant.permissions
MATCH (p:Principal)-[:HAS_GRANT]->(g:Grant)
RETURN p.node_id AS principal,p.enabled AS enabled,p.kind AS kind,g.scope AS scope,
       g.revoked AS revoked,g.permissions AS permissions,g.expires_at AS expires_at
ORDER BY principal,scope
