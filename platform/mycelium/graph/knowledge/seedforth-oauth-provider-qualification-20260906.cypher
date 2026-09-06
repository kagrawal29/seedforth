MERGE (k:Knowledge {node_id:'knowledge-oauth-provider-qualification-20260906'})
ON CREATE SET k.scope_id='seedforth-platform',k.created_at=datetime(),
k.source_revision='c38bb809fde4f207246f20b5f748e168ba677928',
k.summary='Durable scoped OAuth provider qualified through actual HTTP and official MCP client into disposable graph. Human consent is an internal synthetic fixture. Real enrollment, login, consent UI, recovery and public deployment remain required.',
k.qualification_tests=134,k.oauth_specific_tests=11,
k.junit_sha256='28f5746cd337e01f48d564ba48c7dcb440f3d643c8adaefa7c4949c06cde0b19',
k.public_oauth_deployed=false,k.human_login_qualified=false,k.playwright_login_qualified=false,
k.delta_processor_qualified=false,k.trust='delegated_operator_verified_test_evidence'
WITH k
MATCH (w:WorkItem {node_id:'wi-upgrade-W15',scope_id:'seedforth-platform'})
MERGE (k)-[:INFORMS]->(w);
