MATCH (p:Principal {node_id:'principal-seedforth-owner',enabled:true})
UNWIND ['seedforth-platform','flowing-indian','cajon-sensei'] AS scope
MATCH (:ControlScope {node_id:scope})
MERGE (g:Grant {node_id:'grant-owner-conversation-'+scope})
ON CREATE SET g.scope=scope,g.revoked=false,g.permissions=['read','conversation.read','conversation.send'],
g.authority='owner-delegated-upgrade-operator',g.created_at=datetime()
MERGE (p)-[:HAS_GRANT]->(g)
MERGE (d:Decision {node_id:'decision-owner-conversation-intake-v1'})
ON CREATE SET d.scope_id='seedforth-platform',d.status='accepted',d.created_at=datetime(),
d.authority='owner-delegated-upgrade-operator',
d.summary='Permit owner-scoped durable conversation intake and private readback. This grants no execution, spend, model call or public access.'
MERGE (d)-[:AUTHORIZES]->(g);
