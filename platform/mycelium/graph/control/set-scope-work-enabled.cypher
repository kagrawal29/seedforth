// Versioned scope gate used by the board/operator. Enabling does not claim or
// execute work; disabling prevents new claims while preserving active receipts.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'work.control' IN grant.permissions
  AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
WITH DISTINCT grant
MATCH (s:ControlScope {node_id:$scope})
SET s._lock=coalesce(s._lock,0)+1
WITH s WHERE s.state_version=$version AND $enabled IN [true,false]
SET s.work_enabled=$enabled,s.state_version=s.state_version+1,
    s.hold_reason=CASE WHEN $enabled THEN 'operator_enabled_bounded_scope' ELSE $reason END,
    s.updated_at=datetime()
WITH s, CASE WHEN $enabled THEN 'resume' ELSE 'pause' END AS signal_type
CREATE (signal:Signal {node_id:$event_id,scope_id:$scope,issuer:$actor,
    type:signal_type,status:'accepted',
    created_at:datetime(),result:'scope_work_gate_changed',enabled:$enabled})
CREATE (signal)-[:TARGETS]->(s)
RETURN s.node_id AS scope,s.work_enabled AS enabled,s.state_version AS version,
       s.hold_reason AS reason
