// Record an external verifier's result against one exact invocation receipt.
// The test runner supplies evidence metadata only; it cannot approve work.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'work.review' IN grant.permissions
  AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
MATCH (r:Receipt {node_id:$receipt,scope_id:$scope,artifact_hash:$artifact_hash})
      <-[:PRODUCED]-(i:Invocation {scope_id:$scope,status:'succeeded'})
      -[:EXECUTES]->(w:WorkItem {scope_id:$scope})
WHERE i.actor<>$actor AND $status='passed' AND size($runner)>=1 AND size($runner)<=256
  AND size($test_run)>=8 AND size($test_run)<=128
MERGE (v:TestRun {node_id:$test_run})
ON CREATE SET v.scope_id=$scope,v.status=$status,v.runner=$runner,
    v.artifact_hash=$artifact_hash,v.finished_at=datetime(),v.created_at=datetime(),
    v.authority='independent_test_observation',v.evidence_ref=$evidence_ref
WITH v,r,w
WHERE v.scope_id=$scope AND v.status='passed' AND v.artifact_hash=$artifact_hash
MERGE (v)-[:VERIFIES]->(r)
MERGE (v)-[:INFORMS]->(w)
RETURN v.node_id AS test_run,v.status AS status,v.artifact_hash AS artifact_hash,
       w.node_id AS work_id
