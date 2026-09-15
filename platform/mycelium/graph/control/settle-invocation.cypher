// Broker evidence admission remains possible after worker revocation or a hold.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'invocation.settle' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (i:Invocation {node_id:$invocation,scope_id:scope})-[:RESERVES_FROM]->(b:Budget {scope_id:scope})
SET b._lock=coalesce(b._lock,0)+1,i._lock=coalesce(i._lock,0)+1
WITH i,b WHERE (i.status IN ['dispatching','unknown'] AND $outcome IN ['succeeded','failed','unknown'])
OR (i.status='admitted' AND $outcome='cancelled')
FOREACH (_ IN CASE WHEN $outcome<>'unknown' THEN [1] ELSE [] END |
SET b.reserved_units=b.reserved_units-i.reserved_units,
b.spent_units=b.spent_units+CASE WHEN $outcome='cancelled' THEN 0 ELSE i.reserved_units END)
SET i.status=$outcome,i.updated_at=datetime(),i.result_hash=$result_hash,
i.artifact_hash=$artifact_hash,i.artifact_ref=$artifact_ref,
i.finished_at=CASE WHEN $outcome='unknown' THEN null ELSE datetime() END
CREATE (r:InvocationResult {node_id:$event_id,scope_id:$scope,actor:$actor,outcome:$outcome,
result_hash:$result_hash,artifact_hash:$artifact_hash,artifact_ref:$artifact_ref,created_at:datetime()})
CREATE (r)-[:REPORTS]->(i)
RETURN i.node_id AS id,i.status AS status,b.reserved_units AS budget_reserved,b.spent_units AS budget_spent
