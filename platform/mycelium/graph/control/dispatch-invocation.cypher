MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'work.execute' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (:ControlScope {node_id:scope,work_enabled:true})
MATCH (i:Invocation {node_id:$invocation,scope_id:scope,actor:$actor,status:'admitted'})-[:FOR_ATTEMPT]->(e:ExecutionSession {status:'running'})-[:EXECUTES]->(w:WorkItem {scope_id:scope})
MATCH (i)-[:AUTHORIZED_BY]->(m:Mandate {node_id:e.mandate_id,scope_id:scope,enabled:true})
MATCH (c:Capability {node_id:i.capability,enabled:true,policy_generation:i.policy_generation})
SET w._lock=coalesce(w._lock,0)+1,i._lock=coalesce(i._lock,0)+1
WITH i,e,w,m,c WHERE i.status='admitted' AND i.params_hash=$params_hash
AND w.status='in_progress' AND w.hold=false AND i.fence=w.fence AND e.fence=w.fence
AND w.lease_until>datetime() AND m.expires_at>datetime() AND m.version=i.mandate_version
AND w.mandate_id=e.mandate_id
AND i.capability IN m.allowed_capabilities
AND c.cost_units=i.reserved_units AND c.max_seconds=i.max_seconds
AND w.lease_until>datetime()+duration({seconds:i.max_seconds})
AND m.expires_at>datetime()+duration({seconds:i.max_seconds})
SET i.status='dispatching',i.dispatched_at=datetime()
RETURN i.node_id AS id,i.status AS status
