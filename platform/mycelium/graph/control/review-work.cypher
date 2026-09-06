MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'work.review' IN grant.permissions AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
WITH DISTINCT grant.scope AS scope
MATCH (w:WorkItem {node_id:$id,scope_id:scope})
MATCH (e:ExecutionSession {scope_id:scope,status:'succeeded'})-[:EXECUTES]->(w)
MATCH (e)-[:PRODUCED]->(r:Receipt {node_id:$receipt,artifact_hash:$artifact_hash})
OPTIONAL MATCH (v:TestRun {node_id:$test_run,scope_id:scope,status:'passed'})-[:VERIFIES]->(r)
WITH w,e,r,v
WHERE $actor<>e.actor AND ($accept=false OR (v IS NOT NULL AND
v.artifact_hash=r.artifact_hash AND v.finished_at>datetime()-duration('PT1H') AND v.runner<>e.actor))
SET w._lock=coalesce(w._lock,0)+1
WITH w,e,r,v WHERE w.status='review' AND w.state_version=$version AND w.hold=false
AND $accept IN [true,false]
SET w.status=CASE WHEN $accept THEN 'done' ELSE 'proposed' END,
w.verification_status=CASE WHEN $accept THEN 'verified' ELSE 'rejected' END,
w.state_version=w.state_version+1,w.updated_at=datetime()
CREATE (d:Decision {node_id:$event_id,scope_id:$scope,actor:$actor,outcome:CASE WHEN $accept THEN 'approved' ELSE 'rejected' END,
created_at:datetime(),artifact_hash:$artifact_hash})
CREATE (d)-[:REVIEWS]->(r)
CREATE (d)-[:CONCERNS]->(w)
CREATE (t:StateTransition {node_id:$event_id+':transition',scope_id:$scope,actor:$actor,
from_state:'review',to_state:w.status,created_at:datetime()})
CREATE (t)-[:CHANGED]->(w)
CREATE (t)-[:AUTHORIZED_BY]->(d)
FOREACH (_ IN CASE WHEN $accept THEN [1] ELSE [] END |
CREATE (pe:ProgressEvent {node_id:$event_id+':progress',scope_id:$scope,project:$scope,
created_at:datetime(),kind:'accepted_artifact',verification_status:'verified'})
CREATE (pe)-[:EVIDENCE]->(r)
CREATE (pe)-[:ADVANCES_WORK]->(w))
RETURN w.node_id AS id,w.status AS status,w.state_version AS version
