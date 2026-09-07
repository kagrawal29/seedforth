// Portfolio home projection. Platform-scoped read is required; project members
// remain restricted to read-scope/read-work for their granted project.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:'seedforth-platform',revoked:false})
WHERE 'read' IN grant.permissions AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
MATCH (s:ControlScope)
OPTIONAL MATCH (s)-[:MAPS_PROJECT]->(p:Project)
CALL {
  WITH s
  OPTIONAL MATCH (w:WorkItem {scope_id:s.node_id})
  RETURN count(w) AS work_count,
         count(CASE WHEN w.hold=true OR w.status IN ['blocked','review'] THEN w END) AS attention_count
}
CALL {
  WITH s
  OPTIONAL MATCH (o:Observation {scope_id:s.node_id})
  RETURN max(o.observed_at) AS latest_observation_at
}
RETURN s.node_id AS scope,s.name AS name,s.portfolio_state AS portfolio_state,
       s.work_enabled AS work_enabled,s.state_version AS state_version,
       s.hold_reason AS hold_reason,p.node_id AS project_id,
       p.status AS historical_status,work_count,attention_count,
       latest_observation_at
ORDER BY CASE WHEN s.portfolio_state='active' THEN 0 ELSE 1 END,name
