MERGE (k:Knowledge {node_id:'knowledge-writer-census-20260906'})
ON CREATE SET k.scope_id='seedforth-platform',k.created_at=datetime(),
k.observed_at=datetime('2026-09-06T16:40:00Z'),k.trust='operator_metadata_inspection',
k.source='architecture/upgrade/writer-census-20260906.md',k.coverage='partial_host_scheduler_service_process_metadata',
k.summary='Six root cron jobs observed. Four exact legacy execution entries fenced with separate verified Decision. Eight old opencode processes retain broad provider credential environment keys. Application schedulers, credential fencing and public exposure remain unresolved.',
k.complete_inventory=false,k.security_isolation_verified=false,
k.secret_values_collected=false,k.legacy_agent_process_count=8
WITH k
MATCH (w:WorkItem {node_id:'wi-upgrade-W00',scope_id:'seedforth-platform'})
MERGE (k)-[:INFORMS]->(w)
WITH k
MATCH (d:Decision {node_id:'decision-legacy-schedule-fence-20260906'})
MERGE (k)-[:CONTEXT_FOR]->(d);
