// @node_id: seedforth-ecosystem-fixes-v1
// @label: "Fixes for failing invariants — charlie-server services + missing repo links"
// @kind: knowledge

// --- Charlie-server services ---
MERGE (s1:Service {node_id: 'svc-audioworld'})
SET s1.project = 'audioworld', s1.name = 'audioworld', s1.description = 'LinkedIn outreach agent system running on charlie-server', s1.health = 'active', s1.last_checked_at = datetime();

MERGE (s2:Service {node_id: 'svc-charlie-nginx'})
SET s2.project = 'seedforth', s2.name = 'nginx', s2.description = 'Web server / reverse proxy on charlie-server', s2.health = 'active', s2.last_checked_at = datetime();

MATCH (cs:Server {node_id: 'server-charlie'}), (s1:Service {node_id: 'svc-audioworld'}) MERGE (cs)-[:HAS_SERVICE]->(s1);
MATCH (cs:Server {node_id: 'server-charlie'}), (s2:Service {node_id: 'svc-charlie-nginx'}) MERGE (cs)-[:HAS_SERVICE]->(s2);

// --- Missing repos (need to create Repository nodes first for projects not yet mapped) ---
MERGE (r1:Repository {node_id: 'repo-pulse-dashboard'})
SET r1.project = 'seedforth', r1.full_name = 'kagrawal29/pulse-dashboard', r1.org = 'kagrawal29', r1.name = 'pulse-dashboard', r1.description = 'Next.js dashboard', r1.visibility = 'private', r1.url = 'https://github.com/kagrawal29/pulse-dashboard';

MERGE (r2:Repository {node_id: 'repo-news-commodity-link'})
SET r2.project = 'seedforth', r2.full_name = 'kagrawal29/news-commodity-link', r2.org = 'kagrawal29', r2.name = 'news-commodity-link', r2.description = 'News/commodity correlation research', r2.visibility = 'private', r2.url = 'https://github.com/kagrawal29/news-commodity-link';

MERGE (r3:Repository {node_id: 'repo-ai-product-quotes'})
SET r3.project = 'seedforth', r3.full_name = 'kagrawal29/ai-product-quotes', r3.org = 'kagrawal29', r3.name = 'ai-product-quotes', r3.description = 'Client brief-to-proposal pipeline', r3.visibility = 'private', r3.url = 'https://github.com/kagrawal29/ai-product-quotes';

MERGE (r4:Repository {node_id: 'repo-ojas-life'})
SET r4.project = 'seedforth', r4.full_name = 'kagrawal29/ojas-life', r4.org = 'kagrawal29', r4.name = 'ojas-life', r4.description = 'Brand identity and business docs', r4.visibility = 'private', r4.url = 'https://github.com/kagrawal29/ojas-life';

MERGE (r5:Repository {node_id: 'repo-perf-marketing'})
SET r5.project = 'seedforth', r5.full_name = 'kagrawal29/performance-marketing-dashboard', r5.org = 'kagrawal29', r5.name = 'performance-marketing-dashboard', r5.description = 'Marketing dashboard mockup', r5.visibility = 'private', r5.url = 'https://github.com/kagrawal29/performance-marketing-dashboard';

MERGE (r6:Repository {node_id: 'repo-sports-corridor'})
SET r6.project = 'seedforth', r6.full_name = 'kagrawal29/sports-corridor', r6.org = 'kagrawal29', r6.name = 'sports-corridor', r6.description = 'Sports business plans', r6.visibility = 'private', r6.url = 'https://github.com/kagrawal29/sports-corridor';

MATCH (p:Project {node_id: 'proj-pulse-dashboard'}), (r:Repository {node_id: 'repo-pulse-dashboard'}) MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-news-commodity-link'}), (r:Repository {node_id: 'repo-news-commodity-link'}) MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-AI-product-quotes'}), (r:Repository {node_id: 'repo-ai-product-quotes'}) MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-ojas-life'}), (r:Repository {node_id: 'repo-ojas-life'}) MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-performance-marketing'}), (r:Repository {node_id: 'repo-perf-marketing'}) MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-sports-corridor'}), (r:Repository {node_id: 'repo-sports-corridor'}) MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-agent-vinod'}), (r:Repository {node_id: 'repo-agent-vinod'}) MERGE (p)-[:HAS_REPO]->(r);

RETURN 'Fixes applied: charlie-server now has 2 services, 7 missing repo links created' AS result;
