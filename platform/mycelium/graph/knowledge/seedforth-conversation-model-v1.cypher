CREATE CONSTRAINT seedforth_scoped_conversation_id IF NOT EXISTS FOR (n:ScopedConversation) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_conversation_message_id IF NOT EXISTS FOR (n:ConversationMessage) REQUIRE n.node_id IS UNIQUE;
MERGE (s:SchemaContract {node_id:'schema-seedforth-conversation-v1'})
ON CREATE SET s.scope_id='seedforth-platform',s.version='1.0.0',s.created_at=datetime(),
s.source='platform/mycelium/graph/knowledge/seedforth-conversation-model-v1.cypher';
