// @node_id: heal-graph-native-auth
// @label: Heal Graph-Native Auth
// Initialize token_hash for Persons without auth bootstrap
// Safe: idempotent, uses MD5 hash of node_id + timestamp

MATCH (p:Person) WHERE p.token_hash IS NULL
SET p.token_hash = apoc.util.md5([p.node_id, timestamp()]),
    p.auth_bootstrap_at = datetime()
WITH count(p) AS persons_authed
MATCH (anyp:Person) WHERE anyp.token_hash IS NOT NULL
RETURN persons_authed, count(anyp) AS total_authenticated, 'auth-bootstrap-complete' AS status
