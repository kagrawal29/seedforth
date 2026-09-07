// Expired delivery leases may be retried because the external destination is
// deterministic (message_id). The prior attempt remains in the signal trail.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'conversation.reconcile' IN g.permissions
  AND (g.expires_at IS NULL OR g.expires_at>datetime())
MATCH (m:ConversationMessage {node_id:$message_id,scope_id:$scope,status:'delivering'})
WHERE m.delivery_lease_until<=datetime()
WITH m
SET m.status='queued',m.delivery_recovery_at=datetime(),m.delivery_lease_until=null,
    m.updated_at=datetime(),m.delivery_recovery_count=coalesce(m.delivery_recovery_count,0)+1
CREATE (s:Signal {node_id:'delivery-recover-'+$message_id+':'+toString(m.delivery_recovery_count),
    scope_id:$scope,issuer:$actor,type:'conversation_delivery_reconciled',status:'accepted',
    created_at:datetime(),message_id:m.node_id,recovery_count:m.delivery_recovery_count})
CREATE (s)-[:TARGETS]->(m)
RETURN m.node_id AS message_id,m.status AS delivery_state,m.delivery_recovery_count AS recovery_count
