// A worker can report completion only from the broker's actual successful result.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'work.execute' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (i:Invocation {node_id:$invocation,scope_id:scope,status:'succeeded'})-[:FOR_ATTEMPT]->(e:ExecutionSession {node_id:$attempt,scope_id:scope,actor:$actor,status:'running'})-[:EXECUTES]->(w:WorkItem {scope_id:scope})
SET w._lock=coalesce(w._lock,0)+1
WITH i,e,w WHERE e.status='running' AND w.status='in_progress' AND w.hold=false
AND e.fence=w.fence AND w.fence=$fence AND w.lease_until>datetime()
AND i.artifact_hash IS NOT NULL AND i.artifact_ref IS NOT NULL
SET e.status='succeeded',e.finished_at=datetime(),w.status='review',w.state_version=w.state_version+1,
w.updated_at=datetime(),w.lease_until=null
CREATE (r:Receipt {node_id:$event_id,scope_id:$scope,actor:$actor,outcome:'succeeded',
artifact_ref:i.artifact_ref,artifact_hash:i.artifact_hash,created_at:datetime(),verification_status:'unverified'})
CREATE (e)-[:PRODUCED]->(r)
CREATE (r)-[:EVIDENCED_BY]->(i)
CREATE (t:StateTransition {node_id:$event_id+':transition',scope_id:$scope,actor:$actor,
from_state:'in_progress',to_state:'review',created_at:datetime()})
CREATE (t)-[:CHANGED]->(w)
RETURN w.node_id AS id,w.status AS status,w.state_version AS version,r.node_id AS receipt
