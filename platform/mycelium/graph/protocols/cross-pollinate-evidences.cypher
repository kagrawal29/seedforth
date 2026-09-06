// @node_id: protocol-cross-pollinate-evidences
// @label: "Cross-Pollinate EVIDENCES — Commits to Knowledge"
// ============================================================================
// Protocol: Cross-Pollinate EVIDENCES — Commits to Knowledge
// ============================================================================
// Bridges Commits (672 nodes, dense artifact pool) to Knowledge (301 nodes,
// sparse concept pool) via transitive closure through CodeCypher.
//
// Pattern: Commit ─[IN_REPO]→ CodeCypher ─[RELATES_TO]→ Knowledge
// Creates: Commit ─[EVIDENCES]→ Knowledge
//
// Intent: Make Commits first-class evidence for Knowledge concepts. A Commit
// that modifies code implementing a Knowledge idea should point at the idea.
// This surface "show me commits that prove this concept works" queries.
//
// Density impact:
//   - Bridges sparse (Knowledge: 301) and dense (Commit: 672) pools
//   - Creates ~150–250 new typed edges (Commit → Knowledge)
//   - Zero duplicates (MERGE is idempotent on 3-node triplet)
//
// Edge shape:
//   (commit:Commit)-[:EVIDENCES {
//     evidenced_at,
//     evidenced_via: 'cross-pollinate-evidences.cypher',
//     via_cypher_count (how many CodeCypthers mediate the link)
//   }]->(k:Knowledge)
//
// Idempotent: MERGE on (commit, knowledge, EVIDENCES). Re-running updates
// `evidenced_at` + `via_cypher_count`, never creates duplicate edges.
//
// Parameters: none (deterministic, no thresholds).
//
// Dependencies: APOC not required. Assumes Commit, CodeCypher, Knowledge
// nodes exist with appropriate edges (IN_REPO, RELATES_TO).
// ============================================================================

// Step 1: Find all (Commit, Knowledge) pairs connected via CodeCypher
// Pattern: Commit ─[IN_REPO]→ CodeCypher ─[RELATES_TO]→ Knowledge
MATCH (commit:Commit)-[in_repo:IN_REPO]->(cypher:CodeCypher)
MATCH (cypher)-[relates:RELATES_TO]->(knowledge:Knowledge)
WITH
  commit,
  knowledge,
  collect(DISTINCT cypher.node_id) AS mediating_cyphers

// Step 2: Count how many distinct CodeCyphers mediate each (Commit, Knowledge) pair
WITH
  commit,
  knowledge,
  mediating_cyphers,
  size(mediating_cyphers) AS cypher_count

// Step 3: MERGE the EVIDENCES edge (idempotent)
MERGE (commit)-[r:EVIDENCES]->(knowledge)
ON CREATE SET
  r.evidenced_at = toString(datetime()),
  r.evidenced_via = 'cross-pollinate-evidences.cypher',
  r.via_cypher_count = cypher_count,
  r.mediating_cyphers = mediating_cyphers
ON MATCH SET
  r.evidenced_at = toString(datetime()),
  r.via_cypher_count = cypher_count,
  r.mediating_cyphers = mediating_cyphers,
  r.last_updated = toString(datetime())

// Step 4: Summary row
WITH
  count(DISTINCT commit) AS distinct_commits_joined,
  count(DISTINCT knowledge) AS distinct_knowledge_joined,
  count(*) AS edges_created

MATCH (:Commit)-[e:EVIDENCES]->(:Knowledge)
RETURN
  distinct_commits_joined AS nodes_joined,
  count(DISTINCT e) AS edges_created,
  'Commit' AS dense_pool_label,
  'Knowledge' AS sparse_pool_label;
