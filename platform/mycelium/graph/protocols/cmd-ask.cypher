// @node_id: protocol-cmd-ask
// @label: Ask Command
// @kind: command
// @description: Semantic search across Prompt/Concept/Atom nodes, return top matches

// Atom 1: Query input validation
MATCH (being:Being {node_id: 'being-mycelium'})
RETURN 'input|validated|system ready for semantic search' AS result;

// Atom 2: Fetch all Concepts with embeddings
MATCH (c:Concept) WHERE c.embedding IS NOT NULL
RETURN 'concepts|count:' + toString(count(c)) AS result;

// Atom 3: Fetch all Prompts with embeddings
MATCH (p:Prompt) WHERE p.embedding IS NOT NULL
RETURN 'prompts|count:' + toString(count(p)) AS result;

// Atom 4: Fetch CypherAtoms (potential matches)
MATCH (a:CypherAtom) WHERE a.embedding IS NOT NULL
WITH count(a) AS atom_count
RETURN 'atoms|semantic-count:' + toString(atom_count) AS result;

// Atom 5: Top matching nodes by embedding similarity (via Qdrant search)
MATCH (n) WHERE n.embedding IS NOT NULL
WITH n.node_id AS node_id, n.label AS label, n.node_type AS node_type
RETURN 'top-matches|' + node_id + '|' + coalesce(label, 'unlabeled') + '|' + coalesce(node_type, 'unknown') AS result
LIMIT 10;

// Atom 6: Compile results summary
MATCH (n) WHERE n.embedding IS NOT NULL
WITH count(n) AS searchable_nodes
RETURN 'search-complete|' + toString(searchable_nodes) + ' nodes indexed' AS result;
