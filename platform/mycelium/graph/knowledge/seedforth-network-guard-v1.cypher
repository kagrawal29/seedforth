MERGE (p:NetworkPolicy {node_id:'network-policy-internal-services-v1'})
ON CREATE SET p.scope_id='seedforth-platform',p.version=1,p.interface='eth0',
p.ports=[6083,7474,7687],p.status='approved',p.created_at=datetime(),
p.authority='owner-delegated-upgrade-operator',
p.intent='Deny public ingress to graph and shared authenticated browser transport. Preserve local and SSH-tunneled administration, messaging and outbound traffic.',
p.enforcement='root-protected-offline-kernel-projection',p.boot_dependency='docker.service',
p.coverage='three_tcp_ports_on_primary_uplink_not_complete_network_isolation'
WITH p
MATCH (w:WorkItem {node_id:'wi-upgrade-W12',scope_id:'seedforth-platform'})
MERGE (p)-[:INFORMS]->(w);
