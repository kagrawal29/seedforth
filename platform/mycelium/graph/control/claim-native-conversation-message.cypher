// Bind one delivered board direction to the native adapter's next turn.
// This is consumption evidence, not provider/action evidence.
MATCH (p:Principal {node_id:$worker_id,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE (('conversation.consume' IN g.permissions) OR ('conversation.deliver' IN g.permissions))
  AND (g.expires_at IS NULL OR g.expires_at>datetime())
MATCH (w:WorkItem {node_id:$workitem_id})-[:HAS_MESSAGE]->
      (m:ConversationMessage {node_id:$message_id,scope_id:$scope,status:'delivered'})
MATCH (c:ScopedConversation {scope_id:$scope})-[:HAS_MESSAGE]->(m)
WHERE coalesce(w.scope_id,w.project)=$scope AND c.originator=m.originator
  AND m.execution_state IN ['received_by_delta','acknowledged','not_started','consumed_by_native_adapter']
  AND size($attempt_id)>=8 AND size($attempt_id)<=256
WITH p,g,w,m
MERGE (c:ConversationConsumption {node_id:'consumption-'+$message_id+'-'+$attempt_id})
ON CREATE SET c.scope_id=$scope,c.message_id=m.node_id,c.workitem_id=w.node_id,
    c.attempt_id=$attempt_id,c.worker_id=p.node_id,c.status='consumed',
    c.created_at=datetime(),c.authority='native_adapter_graph_pull'
WITH w,m,c
SET m.execution_state='consumed_by_native_adapter',m.consumed_at=coalesce(m.consumed_at,datetime()),
    m.consumed_attempt_id=$attempt_id,m.updated_at=datetime()
MERGE (c)-[:CONSUMES]->(m)
MERGE (c)-[:TARGETS]->(w)
RETURN m.node_id AS message_id,m.scope_id AS scope_id,m.text AS text,
       m.request_hash AS request_hash,m.sequence AS sequence,
       c.node_id AS conversation_id,w.node_id AS workitem_id,
       c.node_id AS consumption_id,c.status AS consumption_status
