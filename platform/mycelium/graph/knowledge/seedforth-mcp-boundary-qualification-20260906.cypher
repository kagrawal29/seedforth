MERGE (k:Knowledge {node_id:'knowledge-mcp-boundary-qualification-20260906'})
ON CREATE SET k.scope_id='seedforth-platform',k.created_at=datetime(),
k.source='architecture/upgrade/execution-ledger.md',k.source_revision='2aed97e3ced22735f8281d24d6c866daeba044c1',
k.trust='operator_release_and_actual_sdk_http_qualification',
k.summary='Scoped graph/conversation boundary deployed in control release 2aed97e. Official MCP SDK2.1.1 client passed private HTTP discovery, scoped reads, durable reconnect and revocation. No public MCP server, OAuth authorization server or governed Delta processor is deployed by this release.',
k.public_mcp_deployed=false,k.oauth_login_qualified=false,k.delta_processor_qualified=false,
k.release_tests_passed=123,k.coverage='boundary_qualification_not_full_remote_experience'
WITH k
MATCH (w:WorkItem {node_id:'wi-upgrade-W15',scope_id:'seedforth-platform'})
MERGE (k)-[:INFORMS]->(w);
