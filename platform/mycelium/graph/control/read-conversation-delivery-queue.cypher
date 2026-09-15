// Read only identifiers for queued direction. Content is fetched by a claim.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'conversation.deliver' IN g.permissions
  AND (g.expires_at IS NULL OR g.expires_at>datetime())
MATCH (c:ScopedConversation {scope_id:$scope})-[:HAS_MESSAGE]->
      (m:ConversationMessage {scope_id:$scope,status:'queued'})
WHERE c.originator=m.originator
RETURN m.node_id AS message_id,m.sequence AS sequence,m.created_at AS created_at
ORDER BY m.sequence ASC,m.node_id ASC LIMIT 20
