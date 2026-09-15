CREATE CONSTRAINT seedforth_scoped_conversation_id IF NOT EXISTS FOR (n:ScopedConversation) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_conversation_message_id IF NOT EXISTS FOR (n:ConversationMessage) REQUIRE n.node_id IS UNIQUE;
MERGE (s:SchemaContract {node_id:'schema-seedforth-conversation-v1'})
ON CREATE SET s.scope_id='seedforth-platform',s.version='1.0.0',s.created_at=datetime(),
s.source='platform/mycelium/graph/knowledge/seedforth-conversation-model-v1.cypher';

// Delta may receive authenticated direction only through the governed
// delivery reducer. It receives content, never graph authority.
MERGE (p:Principal {node_id:'principal-delta-conversation-processor'})
ON CREATE SET p.kind='service',p.enabled=true,p.created_at=datetime()
WITH p
UNWIND ['flowing-indian','cajon-sensei','seedforth-platform'] AS scope
MERGE (g:Grant {node_id:'grant-delta-conversation-'+scope})
ON CREATE SET g.scope=scope,g.permissions=['read','conversation.deliver','conversation.reconcile'],
    g.revoked=false,g.authority='owner-upgrade-delegation-20260907',g.created_at=datetime()
MERGE (p)-[:HAS_GRANT]->(g);
