MERGE (p:DeploymentPolicy {node_id:'deployment-policy-human-identity-v1'})
ON CREATE SET p.scope_id='seedforth-platform',p.version=1,p.status='approved',
p.authority='owner-delegated-upgrade-operator',p.created_at=datetime(),
p.issuer='https://185.192.96.100/',p.resource='https://185.192.96.100/mcp',
p.project_scopes=['seedforth-platform','flowing-indian','cajon-sensei'],
p.bind_host='127.0.0.1',p.bind_port=8788,p.public_ingress_enabled=false,
p.operator_transport='unix_socket_kernel_uid0',p.credential_state='private_external_sqlite',
p.intent='Deploy the qualified human identity and scoped OAuth component privately. Preserve graph grants and keep public routing closed pending legacy credential isolation.'
WITH p
MATCH (w:WorkItem {node_id:'wi-upgrade-W15',scope_id:'seedforth-platform'})
MERGE (p)-[:INFORMS]->(w);
