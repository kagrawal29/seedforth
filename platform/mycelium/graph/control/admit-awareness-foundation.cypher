// Admit one explicitly selected awareness foundation WorkItem.
// This is a governed transition: it never admits dependent work implicitly.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'work.schedule' IN grant.permissions
  AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
WITH DISTINCT grant.scope AS scope
MATCH (w:WorkItem {node_id:$id,scope_id:scope})
WHERE w.project='mycelium'
  AND w.workstream_id='workstream-system-awareness-metabolism'
  AND w.status='proposed'
  AND coalesce(w.hold,false)=false
  AND NOT EXISTS {
    MATCH (w)-[:DEPENDS_ON]->(d:WorkItem)
    WHERE coalesce(d.status,'unknown')<>'done' OR coalesce(d.hold,false)=true
  }
SET w._lock=coalesce(w._lock,0)+1
WITH w WHERE w.state_version=$version
SET w.status='ready',
    w.execution_eligible=true,
    w.program=coalesce(w.program,'mycelium.autonomy_control_plane.v2'),
    w.admission_mode='bounded_foundation',
    w.admitted_by=$actor,
    w.admitted_at=datetime(),
    w.state_version=w.state_version+1,
    w.updated_at=datetime(),
    w.hold_reason=null
CREATE (t:StateTransition {node_id:$event_id,scope_id:$scope,actor:$actor,
    from_state:'proposed',to_state:'ready',created_at:datetime(),
    reason:'awareness_foundation_admission'})
CREATE (t)-[:CHANGED]->(w)
RETURN w.node_id AS id,w.status AS status,w.execution_eligible AS execution_eligible,
       w.state_version AS version;
