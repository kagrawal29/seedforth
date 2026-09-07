// Commit an external Delta inbox write after deterministic payload hashing.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'conversation.deliver' IN g.permissions
  AND (g.expires_at IS NULL OR g.expires_at>datetime())
MATCH (m:ConversationMessage {node_id:$message_id,scope_id:$scope,status:'delivering',
      delivery_attempt:$delivery_attempt})
WHERE size($delivery_hash)=64 AND size($delivery_ref)>=1 AND size($delivery_ref)<=512
SET m.status='delivered',m.delivery_hash=$delivery_hash,m.delivery_ref=$delivery_ref,
    m.delivered_at=datetime(),m.delivery_lease_until=null,m.updated_at=datetime(),
    m.execution_state='received_by_delta'
CREATE (s:Signal {node_id:'delivery-commit-'+$delivery_attempt,scope_id:$scope,
    issuer:$actor,type:'conversation_delivered_to_delta',status:'accepted',created_at:datetime(),
    message_id:m.node_id,delivery_hash:$delivery_hash,delivery_ref:$delivery_ref})
CREATE (s)-[:TARGETS]->(m)
RETURN m.node_id AS message_id,m.status AS delivery_state,m.delivery_hash AS delivery_hash
