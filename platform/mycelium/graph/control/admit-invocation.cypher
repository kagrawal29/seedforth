MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'work.execute' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (:ControlScope {node_id:scope,work_enabled:true})
MATCH (e:ExecutionSession {node_id:$attempt,scope_id:scope,actor:$actor,status:'running'})-[:EXECUTES]->(w:WorkItem {scope_id:scope})
MATCH (w)-[:AUTHORIZED_BY]->(m:Mandate {node_id:e.mandate_id,scope_id:scope,enabled:true})-[:HAS_BUDGET]->(b:Budget {node_id:m.budget_id,scope_id:scope})
MATCH (c:Capability {node_id:$capability,enabled:true,policy_generation:$generation})
SET b._lock=coalesce(b._lock,0)+1,w._lock=coalesce(w._lock,0)+1
WITH e,w,m,b,c WHERE w.status='in_progress' AND w.hold=false AND e.fence=w.fence AND w.fence=$fence
AND w.lease_until>datetime() AND m.expires_at>datetime() AND m.version=e.mandate_version
AND w.mandate_id=e.mandate_id
AND c.node_id IN m.allowed_capabilities AND c.cost_units>0
AND c.cost_units=$cost_units AND c.max_seconds=$max_seconds AND c.max_seconds>0
AND w.lease_until>datetime()+duration({seconds:c.max_seconds})
AND m.expires_at>datetime()+duration({seconds:c.max_seconds})
OPTIONAL MATCH (old:Invocation {node_id:$invocation})
WITH e,w,m,b,c,old WHERE old IS NOT NULL OR b.total_units-b.reserved_units-b.spent_units>=c.cost_units
MERGE (i:Invocation {node_id:$invocation})
ON CREATE SET i.scope_id=$scope,i.actor=$actor,i.attempt_id=$attempt,i.capability=$capability,
i.policy_generation=$generation,i.params_hash=$params_hash,i.status='admitted',i.fence=$fence,
i.reserved_units=c.cost_units,i.max_seconds=c.max_seconds,i.created_at=datetime(),i.new_admission=true,i.mandate_version=m.version
WITH i,e,w,m,b,c WHERE i.scope_id=$scope AND i.actor=$actor AND i.attempt_id=$attempt
AND i.capability=$capability AND i.policy_generation=$generation AND i.params_hash=$params_hash
FOREACH (_ IN CASE WHEN i.new_admission=true THEN [1] ELSE [] END |
SET b.reserved_units=b.reserved_units+c.cost_units)
SET i.new_admission=null
MERGE (i)-[:FOR_ATTEMPT]->(e)
MERGE (i)-[:RESERVES_FROM]->(b)
MERGE (i)-[:AUTHORIZED_BY]->(m)
RETURN i.node_id AS id,i.status AS status,i.reserved_units AS reserved_units
