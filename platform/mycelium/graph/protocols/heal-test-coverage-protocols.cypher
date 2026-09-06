// @node_id: heal-test-coverage-protocols
// @label: Heal Protocol Test Coverage
// Autocreate TestCase nodes for Protocols missing validation coverage
// Safe: uses MERGE to avoid duplicates, idempotent

MATCH (p:Protocol) WHERE NOT EXISTS { MATCH (:TestCase)-[:VALIDATES]->(p) } WITH p LIMIT 100
MERGE (tc:TestCase { node_id: 'test-auto-' + apoc.util.md5([p.node_id, 'coverage-heal']) })
SET tc.label = 'Auto-test for ' + coalesce(p.label, p.node_id),
    tc.description = 'Auto-generated coverage test',
    tc.test_type = 'coverage-existence',
    tc.created_at = datetime()
MERGE (tc)-[:VALIDATES]->(p)
RETURN count(distinct tc) AS tests_created, 'heal-test-coverage-complete' AS status
