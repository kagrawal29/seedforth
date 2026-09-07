// Record Delta's receipt/classification without granting authority or claiming
// that requested work happened. The acknowledgement is an observation.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'conversation.deliver' IN g.permissions
  AND (g.expires_at IS NULL OR g.expires_at>datetime())
MATCH (m:ConversationMessage {node_id:$message_id,scope_id:$scope,status:'delivered'})
WHERE $ack_status IN ['received','needs_review','rejected']
  AND size($ack_id)>=8 AND size($ack_id)<=128
  AND size($summary)>=1 AND size($summary)<=2000
MERGE (a:ConversationAcknowledgement {node_id:$ack_id})
ON CREATE SET a.scope_id=$scope,a.message_id=m.node_id,a.status=$ack_status,
    a.summary=$summary,a.created_at=datetime(),a.source='delta',
    a.authority='observed_delta_acknowledgement'
WITH a,m
WHERE a.scope_id=$scope AND a.message_id=m.node_id AND a.status IN ['received','needs_review','rejected']
SET m.execution_state=CASE WHEN a.status='received' THEN 'acknowledged' ELSE 'requires_review' END,
    m.acknowledged_at=coalesce(m.acknowledged_at,a.created_at),m.ack_status=a.status,
    m.ack_id=a.node_id,m.updated_at=datetime()
MERGE (a)-[:ACKNOWLEDGES]->(m)
RETURN m.node_id AS message_id,m.execution_state AS execution_state,
       a.node_id AS ack_id,a.status AS ack_status
