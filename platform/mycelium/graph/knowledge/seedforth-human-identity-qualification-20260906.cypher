MERGE (k:Knowledge {node_id:'knowledge-human-identity-qualification-20260906'})
ON CREATE SET k.scope_id='seedforth-platform',k.created_at=datetime(),
k.observed_at=datetime('2026-09-06T17:51:14Z'),
k.source_revision='58040afe7325d98b63f8208a529bf9c6d1f2ae68',
k.summary='Human MFA enrollment, login, scoped consent, recovery and revocation passed exact-source Playwright into OAuth and MCP against disposable graph. Synthetic identities only. Production deployment and legacy credential isolation remain required.',
k.qualification_tests=140,k.junit_sha256='2ff204266a6596893c3ed5837577e96d396c83641be7437adce7c041b81e1de6',
k.playwright_status='passed_synthetic_human_actual_disposable_graph',
k.playwright_source_sha256='a42d366d8b06da922afee5ee0b72619a78786f7d1a4afb7db5efbe59bb88d502',
k.mobile_screenshot_sha256='1654eb8283734d80448e7d3560f3175a6ffc817bff62ec7888364fe51fa2a21f',
k.graph_outage_evidence='injected_read_failure_not_database_shutdown',
k.public_identity_deployed=false,k.owner_credentials_created=false,
k.legacy_credentials_isolated=false,k.delta_processor_qualified=false,
k.trust='delegated_operator_verified_test_evidence'
WITH k
MATCH (w:WorkItem {node_id:'wi-upgrade-W15',scope_id:'seedforth-platform'})
MERGE (k)-[:INFORMS]->(w);
