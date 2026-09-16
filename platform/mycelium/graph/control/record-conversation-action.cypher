// Record worker evidence separately from delivery and acknowledgement.
MATCH (m:ConversationMessage {node_id:$message_id,scope_id:$scope,status:'delivered'})
WHERE size($action_id)>=8 AND size($action_id)<=256
  AND size($wakeup_id)>=1 AND size($worker_id)>=1
  AND $action_status='completed' AND size($result)<=2000
OPTIONAL MATCH (w:WorkItem {node_id:$workitem_id})
WHERE w IS NULL OR w.scope_id=$scope OR w.project=$scope
MERGE (e:WorkerActionEvidence {node_id:$action_id})
ON CREATE SET e.scope_id=$scope,e.message_id=m.node_id,e.workitem_id=$workitem_id,
    e.wakeup_id=$wakeup_id,e.worker_id=$worker_id,e.status=$action_status,
    e.result=$result,e.created_at=datetime(),e.authority='observed_delta_worker_evidence'
MERGE (e)-[:TARGETS]->(m)
FOREACH (item IN CASE WHEN w IS NULL THEN [] ELSE [w] END |
  MERGE (item)-[:HAS_EVIDENCE]->(e))
SET m.execution_state='action_evidenced',m.action_evidence_id=e.node_id,
    m.updated_at=datetime()
RETURN e.node_id AS action_id,m.execution_state AS execution_state
