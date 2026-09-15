MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'work.execute' IN grant.permissions AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
WITH DISTINCT grant.scope AS scope
MATCH (e:ExecutionSession {node_id:$attempt,scope_id:scope,actor:$actor,status:'running'})-[:EXECUTES]->(w:WorkItem {scope_id:scope})
SET w._lock=coalesce(w._lock,0)+1
WITH e,w WHERE e.fence=w.fence AND w.fence=$fence AND w.lease_until>datetime()
AND w.hold=false AND $outcome IN ['succeeded','failed','blocked']
SET e.status=CASE WHEN $outcome='blocked' THEN 'failed' ELSE $outcome END,e.finished_at=datetime(),
w.status=CASE WHEN $outcome='succeeded' THEN 'review' ELSE 'blocked' END,
w.state_version=w.state_version+1,w.updated_at=datetime(),w.lease_until=null
CREATE (r:Receipt {node_id:$event_id,scope_id:$scope,actor:$actor,outcome:$outcome,
artifact_ref:$artifact_ref,artifact_hash:$artifact_hash,created_at:datetime(),verification_status:'unverified'})
CREATE (e)-[:PRODUCED]->(r)
CREATE (t:StateTransition {node_id:$event_id+':transition',scope_id:$scope,actor:$actor,
from_state:'in_progress',to_state:w.status,created_at:datetime()})
CREATE (t)-[:CHANGED]->(w)
RETURN w.node_id AS id,w.status AS status,w.state_version AS version,r.node_id AS receipt
