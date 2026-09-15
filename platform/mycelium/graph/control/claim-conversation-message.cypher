// Claim one authenticated direction for external Delta delivery.
// Message text is untrusted content and does not convey authority.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'conversation.deliver' IN g.permissions
  AND (g.expires_at IS NULL OR g.expires_at>datetime())
MATCH (c:ScopedConversation {scope_id:$scope})-[:HAS_MESSAGE]->
      (m:ConversationMessage {node_id:$message_id,status:'queued'})
WHERE c.originator=m.originator AND size($delivery_attempt)>=8 AND size($delivery_attempt)<=128
WITH DISTINCT c,m
SET m._lock=coalesce(m._lock,0)+1
WITH c,m WHERE m.status='queued'
SET m.status='delivering',m.delivery_attempt=$delivery_attempt,
    m.delivery_lease_until=datetime()+duration('PT2M'),m.delivery_started_at=datetime(),
    m.updated_at=datetime()
CREATE (s:Signal {node_id:'delivery-claim-'+$delivery_attempt,scope_id:$scope,
    issuer:$actor,type:'conversation_delivery_claimed',status:'accepted',created_at:datetime(),
    message_id:m.node_id,originator:m.originator,sequence:m.sequence})
CREATE (s)-[:TARGETS]->(m)
RETURN m.node_id AS message_id,m.originator AS originator,m.recipient AS recipient,
       m.sequence AS sequence,m.text AS text,m.request_hash AS request_hash,
       m.created_at AS created_at,
       m.delivery_attempt AS delivery_attempt,m.delivery_lease_until AS lease_until
