MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'read' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope,
['WorkItem','Workstream','Milestone','EntityGoal','Decision','Receipt','TestRun','SourceStream','Knowledge','Observation'] AS allowed,
['Principal','Grant','CypherAtom','ControlOperation','OperationRevision','NetworkPolicy','ScopedConversation','ConversationMessage'] AS excluded
MATCH (n {scope_id:scope})
WHERE n.node_id IS NOT NULL AND n.node_id>$cursor
AND any(label IN labels(n) WHERE label IN allowed)
AND NOT any(label IN labels(n) WHERE label IN excluded)
WITH scope,allowed,excluded,n ORDER BY n.node_id LIMIT 30
CALL {
  WITH scope,allowed,excluded,n
  MATCH (n)-[r]-(m {scope_id:scope})
  WHERE m.node_id IS NOT NULL AND any(label IN labels(m) WHERE label IN allowed)
  AND NOT any(label IN labels(m) WHERE label IN excluded)
  AND type(r) IN ['HAS_WORKSTREAM','HAS_MILESTONE','HAS_WORK_ITEM','ADVANCES','VERIFIES','INFORMS','CONTEXT_FOR','OBSERVED_STREAM']
  WITH r,m ORDER BY m.node_id,type(r) LIMIT 20
  RETURN collect({type:type(r),from:startNode(r).node_id,to:endNode(r).node_id}) AS edges
}
RETURN n.node_id AS id,[label IN labels(n) WHERE label IN allowed] AS labels,
substring(coalesce(n.title,n.name,n.summary,''),0,1000) AS title,n.status AS status,
n.state_version AS version,n.created_at AS created_at,n.updated_at AS updated_at,
n.trust AS trust,n.verification_status AS verification_status,n.source AS source,
edges,'bounded_scoped_metadata_not_complete_legacy_graph' AS coverage
ORDER BY id
