MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:$scope,revoked:false})
WHERE 'work.create' IN grant.permissions AND (grant.expires_at IS NULL OR grant.expires_at > datetime())
WITH DISTINCT grant.scope AS scope
MATCH (s:ControlScope {node_id:scope})-[:MAPS_PROJECT]->(p:Project)
MATCH (p)-[:HAS_WORKSTREAM]->(:Workstream)-[:HAS_MILESTONE]->(m:Milestone {node_id:$milestone})
WHERE size(trim($title)) > 0 AND size(trim($acceptance)) > 0
MERGE (w:WorkItem {node_id:$id})
ON CREATE SET w.scope_id=scope,w.project=p.name,w.title=$title,w.acceptance=$acceptance,
w.status='proposed',w.state_version=0,w.hold=false,w.verification_status='unverified',
w.created_by=$actor,w.request_hash=$request_hash,w.created_at=datetime(),w.updated_at=datetime()
WITH w,m,scope WHERE w.scope_id=scope AND w.created_by=$actor AND w.request_hash=$request_hash
MERGE (m)-[:HAS_WORK_ITEM]->(w)
RETURN w.node_id AS id,w.status AS status,w.state_version AS version
