MERGE (p:NetworkPolicy:Knowledge {node_id:'network-policy-legacy-agent-graph-v1'})
ON CREATE SET p.scope_id='seedforth-platform',p.version=1,
p.uids=[1003,1004,1005,1006,1007,1008,1009,1010],p.ports=[7474,7687],
p.status='approved',p.created_at=datetime(),p.authority='owner-delegated-upgrade-operator',
p.intent='Contain direct graph connections from the eight observed legacy agent UIDs without stopping message transport. No new execution authority.',
p.enforcement='root-protected-offline-kernel-projection',
p.coverage='IPv4 and IPv6 host OUTPUT original TCP graph ports, not proxies or complete credential isolation',
p.limitations='Does not revoke leaked credentials, other provider access, alternate-port proxies, local files, shared browsers or privileged helpers. New UIDs require a reviewed policy update.',
p.source='platform/mycelium/graph/knowledge/seedforth-agent-graph-guard-v1.cypher'
WITH p
MATCH (w:WorkItem {node_id:'wi-upgrade-W15',scope_id:'seedforth-platform'})
MERGE (p)-[:INFORMS]->(w);
