MERGE (k:Knowledge {node_id:'knowledge-network-guard-verification-20260906'})
ON CREATE SET k.scope_id='seedforth-platform',k.created_at=datetime(),
k.source='architecture/upgrade/network-guard-20260906.md',
k.trust='operator_external_probe_and_production_readback',
k.summary='External IPv4 TCP access to 6083,7474,7687 changed from connected to explicit refusal. SSH and tunneled Neo4j HTTP still work. IPv6 qualified in actual disposable namespaces and production rule readback, not external IPv6 probe. Retained noVNC HTTP fails and its configured web directory is absent.',
k.external_ipv4_denial_verified=true,k.external_ipv6_probe_verified=false,
k.reboot_drill_verified=false,k.novnc_application_verified=false,
k.local_graph_verified=true,k.projects_preserved=47,
k.coverage='three_ingress_ports_not_system_wide_isolation'
WITH k
MATCH (p:NetworkPolicy {node_id:'network-policy-internal-services-v1'})
MERGE (k)-[:VERIFIES]->(p)
WITH k
MATCH (w:WorkItem {node_id:'wi-upgrade-W12',scope_id:'seedforth-platform'})
MERGE (k)-[:INFORMS]->(w);
