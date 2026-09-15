MERGE (p:NetworkPolicy {node_id:'network-policy-remote-tls-v1'})
ON CREATE SET p.scope_id='seedforth-platform',p.version=1,p.status='approved',
p.created_at=datetime(),p.authority='owner-delegated-upgrade-operator',
p.address='185.192.96.100',p.ports=[80,443],
p.intent='Serve ACME HTTP challenges and trusted HTTPS. Application routes remain closed until the real scoped identity boundary is qualified.',
p.certificate_profile='shortlived',p.renewal_interval_hours=6,
p.public_application_enabled=false,p.oauth_qualified=false,
p.enforcement='root-controlled-nginx-and-systemd-external-io'
WITH p
MATCH (w:WorkItem {node_id:'wi-upgrade-W15',scope_id:'seedforth-platform'})
MERGE (p)-[:INFORMS]->(w);
