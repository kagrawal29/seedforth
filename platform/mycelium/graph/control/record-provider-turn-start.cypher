// Record that the native adapter's provider accepted one turn.
// This does not claim a provider response, tool action, or goal completion.
MATCH (m:ConversationMessage {node_id:$message_id,scope_id:$scope})
MATCH (w:WorkItem {node_id:$workitem_id})-[:HAS_MESSAGE]->(m)
MATCH (c:ConversationConsumption {message_id:m.node_id,workitem_id:w.node_id,
      attempt_id:$attempt_id,status:'consumed'})-[:CONSUMES]->(m)
WHERE size($turn_id)>=8 AND size($turn_id)<=256
  AND size($provider)>=1 AND size($provider)<=128
  AND size($model)>=1 AND size($model)<=256
MERGE (t:ProviderTurn {node_id:'provider-turn-'+$message_id+'-'+$attempt_id+'-'+$turn_id})
ON CREATE SET t.scope_id=$scope,t.message_id=m.node_id,t.workitem_id=w.node_id,
    t.attempt_id=$attempt_id,t.turn_id=$turn_id,t.provider=$provider,t.model=$model,
    t.status='started',t.started_at=datetime(),t.authority='native_adapter_provider_ack'
MERGE (t)-[:STARTED_FROM]->(c)
MERGE (t)-[:TARGETS]->(m)
MERGE (t)-[:TARGETS]->(w)
SET m.execution_state='provider_turn_started',m.provider_turn_id=t.turn_id,
    m.provider_turn_node_id=t.node_id,m.updated_at=datetime()
RETURN t.node_id AS provider_turn_id,t.status AS provider_turn_status,
       m.execution_state AS execution_state
