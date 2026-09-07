MATCH (principal:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'read' IN grant.permissions AND (grant.expires_at IS NULL OR grant.expires_at > datetime())
WITH DISTINCT principal
MATCH (scope:ControlScope {node_id:$scope})
OPTIONAL MATCH (scope)-[:MAPS_PROJECT]->(project:Project)
RETURN scope.node_id AS scope,scope.name AS name,scope.work_enabled AS work_enabled,
scope.state_version AS state_version,scope.hold_reason AS hold_reason,
scope.portfolio_state AS portfolio_state,project.node_id AS project_id,
project.status AS historical_status,project.portfolio_state AS project_portfolio_state,
project.new_work AS project_new_work,scope.updated_at AS updated_at
