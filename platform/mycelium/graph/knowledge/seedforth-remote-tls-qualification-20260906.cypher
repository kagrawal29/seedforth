MATCH (p:NetworkPolicy {node_id:'network-policy-remote-tls-v1',status:'approved'})
MERGE (o:Observation {node_id:'observation-remote-tls-qualification-20260906'})
ON CREATE SET o.scope_id='seedforth-platform',o.observed_at=datetime('2026-09-06T17:22:53Z'),
o.received_at=datetime(),o.status='trusted_closed_ingress_qualified',
o.source_revision='2fb1a5fc023a4edb4ca9aa0014ffd59259ac5843',
o.endpoint='https://185.192.96.100',o.certificate_not_after=datetime('2026-09-13T08:21:27Z'),
o.certificate_sha256='100602d53854e1c4687981e6136cec6e378b12b8d8d01b5cb8f504ae391717d5',
o.external_test_count=14,o.external_test_status='passed',
o.junit_sha256='4cb15978c9143bbd63543e19cc703b5fd5ce100834a248fdae825054ff2444f1',
o.playwright_tls_check='passed_no_trust_bypass',o.renewal_dryrun='passed_staging_webroot_and_mandatory_reload',
o.production_renewal_observed=false,o.reboot_drill_observed=false,
o.recurring_expiry_sensing_installed=false,o.public_application_enabled=false,
o.coverage='One-time external IPv4 TLS and closed-route verification. No OAuth, authenticated application, public IPv6 or unattended-availability claim.'
MERGE (o)-[:OBSERVES_POLICY]->(p)
SET p.deployed_revision=o.source_revision,p.last_qualified_at=o.observed_at
WITH o
MATCH (w:WorkItem {node_id:'wi-upgrade-W15',scope_id:'seedforth-platform'})
MERGE (o)-[:INFORMS]->(w);
