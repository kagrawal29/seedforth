// Bootstrap identity bound to the owner's existing administrator access.
// Public identity-provider mapping remains a separate qualified deployment.
MERGE (p:Principal {node_id:'principal-seedforth-owner'})
ON CREATE SET p.enabled=true,p.kind='human',p.identity_binding='owner-admin-bootstrap',p.created_at=datetime()
WITH p
UNWIND ['flowing-indian','cajon-sensei','seedforth-platform'] AS scope
MATCH (:ControlScope {node_id:scope})
MERGE (g:Grant {node_id:'grant-control-owner-'+scope})
ON CREATE SET g.scope=scope,g.revoked=false,g.created_at=datetime(),
g.permissions=['read','work.create','work.schedule','work.control','work.review','work.reconcile'],
g.authority='owner-upgrade-delegation-20260906'
MERGE (p)-[:HAS_GRANT]->(g);
