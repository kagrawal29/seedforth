MATCH (owner:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(owner_grant:Grant {scope:'seedforth-platform',revoked:false})
WHERE 'work.control' IN owner_grant.permissions
  AND $principal =~ 'principal-human-[a-z0-9-]{1,48}'
  AND $target_scope IN ['flowing-indian','cajon-sensei']
MERGE (p:Principal {node_id:$principal})
ON CREATE SET p.kind='human',p.created_at=datetime()
SET p.enabled=true
MERGE (g:Grant {node_id:'grant-'+$principal+'-'+$target_scope})
SET g.scope=$target_scope,g.revoked=false,g.permissions=['read','conversation.read','conversation.send'],
    g.authority='owner-admin',g.updated_at=datetime()
MERGE (p)-[:HAS_GRANT]->(g)
RETURN p.node_id AS principal,g.scope AS scope,g.permissions AS permissions,g.revoked AS revoked
