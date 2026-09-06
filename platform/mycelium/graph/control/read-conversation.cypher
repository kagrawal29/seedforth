MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'read' IN g.permissions AND 'conversation.read' IN g.permissions
AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (c:ScopedConversation {node_id:$conversation_id,scope_id:scope,originator:$actor})-[:HAS_MESSAGE]->(m:ConversationMessage)
WHERE m.scope_id=scope AND m.sequence>$cursor
RETURN m.node_id AS id,m.sequence AS sequence,m.role AS role,m.text AS text,
m.status AS delivery_state,m.execution_state AS execution_state,m.created_at AS created_at,
m.trust AS trust,c.node_id AS conversation_id
ORDER BY sequence LIMIT 20
