MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE $actor='principal-seedforth-owner' AND $scope='seedforth-platform'
AND 'work.control' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (d:Decision {node_id:'decision-legacy-schedule-fence-20260906',scope_id:scope,status:'accepted'})
WHERE d.expected_before_hash=$before_hash AND $after_hash =~ '[a-f0-9]{64}'
AND $removed_count=size(d.line_hashes) AND $backup STARTS WITH '/opt/seedforth/shared/backups/legacy-schedule-fence-'
AND (d.applied_hash IS NULL OR d.applied_hash=$after_hash)
MERGE (o:Observation {node_id:'observation-legacy-schedule-fence-20260906'})
ON CREATE SET o.scope_id=scope,o.observed_at=datetime(),o.received_at=datetime(),
o.status='verified_fenced',o.before_hash=$before_hash,o.payload_hash=$after_hash,
o.backup_ref=$backup,o.removed_count=$removed_count,o.trust='delegated_operator_readback',
o.coverage='four_exact_root_cron_entries_not_all_legacy_execution'
MERGE (o)-[:VERIFIES]->(d)
SET d.applied_hash=$after_hash,d.applied_at=coalesce(d.applied_at,datetime())
WITH d,o
MATCH (d)-[:DIRECTS]->(s:LegacySchedule)
SET s.disposition='fenced',s.verified_at=o.observed_at,s.evidence_id=o.node_id
RETURN o.node_id AS id,count(s) AS schedules
