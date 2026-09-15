// Scope-bound awareness projection. Read-only: proposals and signals are
// observations for review, never implicit execution instructions.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'read' IN grant.permissions AND (grant.expires_at IS NULL OR grant.expires_at > datetime())
WITH DISTINCT grant.scope AS scope
MATCH (s:ControlScope {node_id:scope})
OPTIONAL MATCH (s)-[:MAPS_PROJECT]->(project:Project)
CALL {
  WITH scope
  MATCH (ws:Workstream {scope_id:scope})
  CALL {
    WITH ws
    OPTIONAL MATCH (ws)-[:HAS_MILESTONE]->(:Milestone)-[:HAS_WORK_ITEM]->(w:WorkItem)
    RETURN collect(DISTINCT {
      id:w.node_id, title:w.title, status:w.status,
      execution_eligible:coalesce(w.execution_eligible,true),
      hold:coalesce(w.hold,false)
    }) AS workitems
  }
  RETURN collect(DISTINCT {
    id:ws.node_id, name:ws.name, status:ws.status, mode:ws.mode,
    workitems:workitems
  }) AS workstreams
}
CALL {
  WITH scope
  MATCH (p:PriorityProposal)-[:TARGETS]->(:WorkItem {scope_id:scope})
  WHERE p.status='proposed'
  RETURN collect(DISTINCT {
    id:p.node_id, goal_id:p.goal_id, workitem_id:p.workitem_id,
    proposed_by:p.proposed_by, requested_priority:p.requested_priority,
    rationale:p.rationale, evidence:p.evidence, mode:p.mode,
    requires_review:p.requires_review
  }) AS priority_proposals
}
CALL {
  WITH scope
  MATCH (g:GapSignal)-[:AFFECTS]->(:WorkItem {scope_id:scope})
  WHERE g.mode='shadow' AND g.status='advisory'
  RETURN collect(DISTINCT {
    id:g.node_id, kind:g.kind, cause:g.cause, occurrences:g.occurrences,
    affected_workitems:g.affected_workitems, latest_observation:g.latest_observation,
    mode:g.mode, intervention_enabled:coalesce(g.intervention_enabled,false)
  }) AS shadow_signals
}
RETURN s.node_id AS scope, project.node_id AS project_id,
       workstreams, priority_proposals, shadow_signals,
       datetime() AS as_of;
