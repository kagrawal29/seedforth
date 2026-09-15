// Fence one stale awareness foundation attempt whose owning runtime is gone.
// This is intentionally narrower than generic work reconciliation: it requires
// an exact attempt, an explicit reason, and a stale event watermark.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'work.reconcile' IN grant.permissions
  AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
WITH DISTINCT grant.scope AS scope
MATCH (w:WorkItem {node_id:$id,scope_id:scope})
MATCH (a:RunAttempt {node_id:$attempt,workitem:w.node_id,status:'running'})
WHERE w.project='mycelium'
  AND w.workstream_id='workstream-system-awareness-metabolism'
  AND w.status='in_progress'
  AND a.last_event_at IS NOT NULL
  AND a.last_event_at <= datetime()-duration({seconds:60})
  AND NOT EXISTS {
    MATCH (e:ExecutionSession)-[:EXECUTES]->(w)
    WHERE e.status='running'
  }
SET w._lock=coalesce(w._lock,0)+1
WITH w,a WHERE w.state_version=$version AND a.status='running'
SET a.status='unknown',
    a.reconciled_at=datetime(),
    a.error_code='orphaned_runtime',
    w.status='blocked',
    w.hold=true,
    w.execution_eligible=false,
    w.blocked_reason='orphaned_runtime',
    w.last_attempt_error=$reason,
    w.state_version=w.state_version+1,
    w.fence=coalesce(w.fence,0)+1,
    w.lease_until=null,
    w.updated_at=datetime()
CREATE (t:StateTransition {node_id:$event_id,scope_id:$scope,actor:$actor,
    from_state:'in_progress',to_state:'blocked',created_at:datetime(),
    reason:'awareness_orphan_reconciliation'})
CREATE (t)-[:CHANGED]->(w)
CREATE (t)-[:RECONCILES]->(a)
RETURN w.node_id AS id,a.node_id AS attempt,a.status AS attempt_status,
       w.status AS status,w.state_version AS version;
