MATCH (p:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'conversation.send' IN g.permissions AND 'read' IN g.permissions
AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT p
WHERE size(trim($text))>0 AND size($text)<=8000
SET p._conversation_lock=coalesce(p._conversation_lock,0)+1
WITH p
OPTIONAL MATCH (prior:ConversationMessage {node_id:$message_id})
WITH p,prior WHERE prior IS NULL OR (prior.scope_id=$scope AND prior.originator=$actor AND prior.request_hash=$request_hash)
MERGE (c:ScopedConversation {node_id:$conversation_id})
ON CREATE SET c.scope_id=$scope,c.originator=$actor,c.recipient='delta',c.sequence=0,c.created_at=datetime()
WITH c WHERE c.scope_id=$scope AND c.originator=$actor
MERGE (m:ConversationMessage {node_id:$message_id})
ON CREATE SET m.scope_id=$scope,m.originator=$actor,m.recipient='delta',m.role='direction',
m.text=$text,m.request_hash=$request_hash,m.created_at=datetime(),m.status='queued',
m.trust='authenticated_origin_uninterpreted_content',m.execution_state='not_started',
m.sequence=c.sequence+1,c.sequence=m.sequence,c.updated_at=m.created_at
MERGE (c)-[:HAS_MESSAGE]->(m)
RETURN m.node_id AS id,m.sequence AS sequence,m.status AS delivery_state,
m.execution_state AS execution_state,c.node_id AS conversation_id
