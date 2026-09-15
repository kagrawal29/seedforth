MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'read' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (w:WorkItem {node_id:$id,scope_id:scope})
CALL {
  WITH w
  MATCH (v:TestRun {scope_id:w.scope_id})-[:INFORMS]->(w)
  RETURN v.node_id AS id,'release_qualification' AS kind,v.status AS status,
  v.source_revision AS revision,v.artifact_hash AS artifact_hash,v.tests_passed AS tests_passed,v.finished_at AS recorded_at
  UNION ALL
  WITH w
  MATCH (e:ExecutionSession {scope_id:w.scope_id})-[:EXECUTES]->(w)
  MATCH (e)-[:PRODUCED]->(r:Receipt {scope_id:w.scope_id})
  RETURN r.node_id AS id,'execution_receipt' AS kind,r.outcome AS status,
  e.source_revision AS revision,r.artifact_hash AS artifact_hash,null AS tests_passed,r.created_at AS recorded_at
}
RETURN id,kind,status,revision,artifact_hash,tests_passed,recorded_at ORDER BY recorded_at DESC LIMIT 100
