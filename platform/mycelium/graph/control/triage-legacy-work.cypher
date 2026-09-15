// Bring one legacy work item into the canonical scoped projection without
// admitting it to execution. The legacy state is preserved for reconciliation.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'work.control' IN grant.permissions
  AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
WITH DISTINCT grant.scope AS scope
MATCH (s:ControlScope {node_id:scope})-[:MAPS_PROJECT]->(p:Project)
MATCH (w:WorkItem {node_id:$id})
WHERE w.scope_id IS NULL AND w.project=p.name
SET w._lock=coalesce(w._lock,0)+1
WITH s,p,w,scope WHERE w.scope_id IS NULL AND w.state_version IS NULL
SET w.scope_id=scope,w.project_id=p.node_id,w.legacy_status=w.status,
    w.status='proposed',w.hold=true,w.state_version=0,
    w.verification_status='unverified',w.triage_reason='legacy_needs_review',
    w.updated_at=datetime()
CREATE (t:StateTransition {node_id:$event_id,scope_id:scope,actor:$actor,
    from_state:'legacy',to_state:'proposed',created_at:datetime(),
    legacy_status:w.legacy_status,reason:'legacy_needs_review'})
CREATE (t)-[:CHANGED]->(w)
RETURN w.node_id AS id,w.scope_id AS scope,w.status AS status,w.hold AS hold,
       w.state_version AS version,w.legacy_status AS legacy_status
