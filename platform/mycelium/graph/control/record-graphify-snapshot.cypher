MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'source.observe' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (s:SourceStream {node_id:'source-graphify-'+scope,scope_id:scope,enabled:true,adapter:'graphify-snapshot-v1'})
WHERE $snapshot_id =~ '[a-f0-9]{64}' AND $content_hash =~ '[a-f0-9]{64}'
AND datetime($captured_at)<=datetime()+duration('PT30S')
MERGE (o:Observation:GraphifySnapshot {node_id:$snapshot_id})
ON CREATE SET o.scope_id=scope,o.source_id=s.node_id,o.observed_at=datetime($captured_at),o.received_at=datetime(),
o.content_hash=$content_hash,o.repository=$repository,o.revision=$revision,o.extractor_revision=$extractor_revision,
o.coverage=$coverage,o.selected_paths=$selected_paths,o.fact_count=$fact_count,o.failure_count=$failure_count,
o.failures=$failures,o.trust='untrusted_extraction_provenance',o.schema_version=1
MERGE (o)-[:OBSERVED_STREAM]->(s)
WITH o,s,scope
FOREACH (fact IN $facts |
  MERGE (f:GraphifyFact {node_id:fact.fact_key})
  ON CREATE SET f.scope_id=scope,f.kind=fact.kind,f.source_path=fact.source_path,
  f.subject_key=fact.subject_key,f.relation=fact.relation,f.object_key=fact.object_key,
  f.snapshot_id=o.node_id,f.created_at=datetime()
  MERGE (o)-[:CONTAINS_FACT]->(f)
)
SET s.last_attempt_at=o.observed_at,s.last_attempt_status=CASE WHEN o.failure_count=0 THEN 'collected' ELSE 'partial' END,
s.last_success_at=CASE WHEN o.failure_count=0 THEN o.observed_at ELSE s.last_success_at END,
s.latest_observation=o.node_id,s.extraction_status=CASE WHEN o.failure_count=0 THEN 'complete' ELSE 'partial' END
RETURN o.node_id AS id,o.fact_count AS facts,o.failure_count AS failures
