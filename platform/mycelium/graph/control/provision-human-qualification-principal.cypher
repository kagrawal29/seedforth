// Owner-only, bounded synthetic identity for private browser qualification.
// It grants read-only access to one approved project and cannot grant execution.
MATCH (owner:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(owner_grant:Grant {scope:'seedforth-platform',revoked:false})
WHERE 'work.control' IN owner_grant.permissions
  AND $principal STARTS WITH 'principal-qualification-'
  AND $principal =~ 'principal-qualification-[a-z0-9-]{1,48}'
  AND $qualification_scope IN ['flowing-indian','cajon-sensei']
  AND $qualification_scope <> 'seedforth-platform'
MATCH (target:ControlScope {node_id:$qualification_scope})
MERGE (p:Principal {node_id:$principal})
ON CREATE SET p.enabled=true,p.kind='human',p.identity_binding='synthetic-qualification',p.created_at=datetime()
SET p.enabled=true,p.qualification=true,p.qualification_expires_at=datetime()+duration({hours:2})
MERGE (g:Grant {node_id:'grant-'+$principal+'-'+$qualification_scope})
ON CREATE SET g.created_at=datetime()
SET g.scope=$qualification_scope,g.revoked=false,g.permissions=['read'],
    g.authority='private-browser-qualification',g.expires_at=datetime()+duration({hours:2})
MERGE (p)-[:HAS_GRANT]->(g)
RETURN p.node_id AS principal,g.scope AS scope,g.permissions AS permissions,g.expires_at AS expires_at
