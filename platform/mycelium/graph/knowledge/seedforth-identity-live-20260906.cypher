MATCH (p:DeploymentPolicy {node_id:'deployment-policy-human-identity-v1'})
MERGE (o:Observation {node_id:'observation-private-identity-deployment-20260906'})
ON CREATE SET o.scope_id='seedforth-platform',o.observed_at=datetime('2026-09-06T18:01:54Z'),
o.received_at=datetime(),o.source_revision='8dd42c0b3b915dd8101e611fcb974842f2617983',
o.operator_revision='d6bf2f82034338a5829d5e12405a1f256dfba7dc',
o.status='private_service_verified',o.bind_host='127.0.0.1',o.bind_port=8788,
o.service_user='seedforth-identity',o.service_uid=997,o.service_gid=984,
o.root_peer_check_verified=true,o.normal_restart_verified=true,o.process_crash_restart_verified=true,
o.bootstrap_saved_privately=true,o.personal_mfa_enrolled=false,o.public_ingress_enabled=false,
o.backup_sha256='63c03c5efff42e4367ef682126a40a3081eea44173047a406f9f44df280e28a4',
o.backup_ref='/opt/seedforth/shared/backups/identity-fe5202c0421a458bb45287c496a61f92.sqlite',
o.coverage='One-time deployment and process recovery checks. Not off-host disaster recovery, recurring sensing or elapsed unattended soak.'
MERGE (o)-[:OBSERVES_POLICY]->(p)
SET p.deployed_revision=o.source_revision,p.deployment_verified_at=o.observed_at
WITH o
MERGE (f:Finding {node_id:'finding-current-graph-credential-project-readable-20260906'})
ON CREATE SET f.scope_id='seedforth-platform',f.status='open',f.severity='critical',f.observed_at=o.observed_at,
f.title='Current graph credential remains readable by active project agent Unix accounts',
f.literal_file_count=12,f.read_checked_uids=[1003,1005],
f.read_checked_path='/opt/delta/tools/neo4j_helper.py',f.credential_value_recorded=false,
f.coverage='Exact current credential match in selected legacy tools and actual project-UID readability. Not a complete credential census.',
f.required_action='Fence legacy model writers, migrate retained consumers and rotate credentials before public scoped launch.'
MERGE (f)-[:GATES]->(o)
WITH o,f
MATCH (w:WorkItem {node_id:'wi-upgrade-W15',scope_id:'seedforth-platform'})
MERGE (o)-[:INFORMS]->(w)
MERGE (f)-[:GATES]->(w);
