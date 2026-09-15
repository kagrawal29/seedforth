MERGE (d:Decision {node_id:'decision-legacy-schedule-fence-20260906'})
ON CREATE SET d.scope_id='seedforth-platform',d.status='accepted',
d.authority='owner-delegated-upgrade-operator',d.created_at=datetime(),
d.summary='Fence duplicate root heartbeat and legacy dream/deep/long execution pending governed replacement. Preserve supported heartbeat, source ingestion and customer transports.',
d.target='root-crontab',d.expected_before_hash='39cb16e88c7383e3fd694fd1835f865c33dd2bed00c9b49e28512527d9e50dd0',
d.line_hashes=['98665e2207d0fd162857234bba181828f3d2b2fecbc418d530ee475addb9e4b1',
'6cf638d89b37e182f757f0fc199712c899a9a5fa117ccb46ccf17d9b5f08c7d6',
'224a4f37c521d7e3227a342e831ee62f8f20a9f8d5b78dec32dad2e6c4ec890b',
'0bd754dce25e2d2a49a3aaa5eb74b7605dbd5e1d0bfa2df09151c87dba924951'],
d.replacement_required=true,d.completion_claim='legacy_entrypoints_fenced_not_governed_cadence_complete'
WITH d
UNWIND [{key:'root-heartbeat',cadence:'heartbeat',reason:'duplicate_of_supported_timer'},
{key:'root-dream',cadence:'dream',reason:'unbounded_legacy_execution'},
{key:'root-deep',cadence:'deep',reason:'explicitly_forbidden_legacy_entrypoint'},
{key:'root-long',cadence:'weekly',reason:'explicitly_forbidden_password_cli_entrypoint'}] AS target
MERGE (s:LegacySchedule {node_id:'legacy-schedule-'+target.key})
ON CREATE SET s.scope_id='seedforth-platform',s.cadence=target.cadence,
s.disposition='fence_authorized_not_verified',s.reason=target.reason,s.observed_at=datetime()
MERGE (d)-[:DIRECTS]->(s)
WITH DISTINCT d
MATCH (w:WorkItem {node_id:'wi-upgrade-W07',scope_id:'seedforth-platform'})
MERGE (d)-[:INFORMS]->(w);
