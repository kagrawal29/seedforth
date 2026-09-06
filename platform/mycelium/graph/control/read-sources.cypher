MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'read' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (s:SourceStream {scope_id:scope})
RETURN s.node_id AS id,s.adapter AS adapter,s.enabled AS enabled,
s.path AS path,s.coverage AS coverage,s.repository_revision AS repository_revision,
s.committed_hash AS committed_hash,s.working_hash AS working_hash,
s.last_attempt_at AS last_attempt_at,s.last_attempt_status AS last_attempt_status,
s.last_success_at AS last_success_at,s.latest_observation AS evidence,
CASE WHEN s.last_success_at IS NULL THEN 'unknown'
WHEN s.last_success_at+duration({seconds:s.freshness_seconds})<datetime() THEN 'stale'
WHEN s.last_attempt_status='collection_failed' THEN 'degraded' ELSE 'fresh' END AS evidence_status,
CASE WHEN s.last_success_at IS NULL OR s.last_success_at+duration({seconds:s.freshness_seconds})<datetime()
THEN 'unknown' ELSE s.process_status END AS process_status,
CASE WHEN s.last_success_at IS NULL OR s.last_success_at+duration({seconds:s.freshness_seconds})<datetime()
THEN 'unknown' ELSE s.code_status END AS code_status
ORDER BY id LIMIT 100
