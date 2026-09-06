// @node_id: protocol-merkle-properties
// @label: "Merkle-as-Properties"
// ============================================================================
// Protocol: Merkle-as-Properties
// ============================================================================
// Replaces the MerkleNode/MerkleTree entity-based integrity structure. Stores
// per-node leaf_hash as a property on every domain node, and a single
// root_hash on the Being singleton.
//
// Why:
//   The old design stored Merkle trees as graph entities. Each compute cycle
//   hashed the whole graph, which included prior MerkleNodes, causing
//   recursive inflation (~3x leaves per pass, 7 generations compounding to
//   546,450 MerkleNodes — 98.95% of the graph). Properties cannot contain
//   themselves, so this class of bug is structurally impossible here.
//
// Idempotent: safe to run repeatedly. Each run recomputes leaf_hash on every
// node and root_hash on Being.
//
// Dependencies: APOC (apoc.util.sha256, apoc.coll.sort, apoc.text.join).
// ============================================================================


// --- Phase 1: purge any legacy Merkle entities --------------------------------
// Idempotent — a clean graph is a no-op.

MATCH (n)
WHERE n:MerkleNode OR n:MerkleTree
DETACH DELETE n;


// --- Phase 2: compute leaf_hash on every domain node -------------------------
// Deterministic serialization: "label|k1=v1;k2=v2;..." sorted by key.
//
// Skip keys are loaded dynamically from SkipKey nodes in the graph (created
// by graph/protocols/skip-keys-init.cypher). Categories include:
//   - merkle-output:    leaf_hash, root_hash, root_hash_computed_at, leaf_count
//   - liveness:         last_heartbeat, last_heartbeat_at, heartbeat_count
//   - phase1-state:     health, last_check, last_result, actual, run_count, etc.
//   - lifecycle:        enabled, deferred_reason, deferred_note
//   - derived-output:   embedding, embedding_for_leaf_hash, embedding_model
//
// Including any of these would break the protocol: merkle-output creates a
// circular dependency, liveness churns root_hash on every heartbeat tick,
// phase1-state churns on every run-invariants/run-tests execution, etc.
//
// Excluded labels: QueryTrace (ephemeral, high volume).
//
// IMPORTANT — two-pass materialization:
// Phase 2 used to be a single `MATCH ... SET` query. That introduced a
// subtle non-determinism: Neo4j's query plan evaluated `keys(n)` / `n[k]`
// for later rows against a partially-updated view of the graph (previous
// rows had their leaf_hash set, which seemed safe because leaf_hash is in
// SkipKey, but something in the lazy-execution path still caused per-node
// hash drift). Observed symptom: stored leaf_hash !=  freshly-recomputed
// leaf_hash for the same serialized input.
//
// Fix: materialize ALL {node, leaf} pairs BEFORE any SET, then UNWIND and
// SET in a second pass. This forces eager evaluation and guarantees every
// leaf is computed against a clean pre-write snapshot.

// Labels excluded from hashing (the "chain layer") — these are the
// data structures that commit TO state, they are not state themselves.
// Including them would cause root_hash to drift every time a species is
// minted, cascading into a runaway mint loop.
//   - Species, LegacySpecies, CanonicalSpecies:  the chain blocks
//   - WitnessSignature, LegacyWitnessSignature:  the consensus votes
//   - Witness:                                    chain participants (heartbeat
//                                                 already SkipKey'd; identity
//                                                 matters but mutates rarely)

// Step 2a: remove stale leaf_hash from chain-layer nodes so Phase 3's
// aggregation doesn't pick them up. Run unconditionally — idempotent.
MATCH (n)
WHERE (n:Species OR n:LegacySpecies OR n:CanonicalSpecies
       OR n:WitnessSignature OR n:LegacyWitnessSignature OR n:Witness)
  AND n.leaf_hash IS NOT NULL
REMOVE n.leaf_hash;

// Step 2b: compute leaf_hash for every non-chain domain node
MATCH (sk:SkipKey)
WITH collect(sk.key) AS skip_keys
MATCH (n)
WHERE n.node_id IS NOT NULL
  AND NOT n:QueryTrace
  AND NOT n:Species
  AND NOT n:LegacySpecies
  AND NOT n:CanonicalSpecies
  AND NOT n:WitnessSignature
  AND NOT n:LegacyWitnessSignature
  AND NOT n:Witness
WITH n, skip_keys,
     labels(n)[0] AS label,
     [k IN keys(n) WHERE NOT k IN skip_keys | k + '=' + apoc.convert.toJson(n[k])] AS raw_pairs
WITH n, label + '|' + apoc.text.join(apoc.coll.sort(raw_pairs), ';') AS serialized
WITH n, apoc.util.sha256([serialized]) AS leaf
WITH collect({n: n, leaf: leaf}) AS all_leaves
UNWIND all_leaves AS row
WITH row
SET row.n.leaf_hash = row.leaf;


// --- Phase 3: compute root_hash from sorted leaf_hashes, set on Being --------
// Root hash = sha256 of concatenated sorted leaf_hashes. Stored as a property
// on the Being singleton (node_id: 'being-mycelium').

MATCH (n) WHERE n.leaf_hash IS NOT NULL
WITH apoc.coll.sort(collect(n.leaf_hash)) AS sorted_hashes
WITH sorted_hashes,
     apoc.util.sha256(sorted_hashes) AS root,
     size(sorted_hashes) AS n_leaves
MERGE (b:Being {node_id: 'being-mycelium'})
SET b.root_hash = root,
    b.leaf_count = n_leaves,
    b.root_hash_computed_at = toString(datetime());


// --- Phase 4: invariant — zero Merkle entities must exist --------------------
// Fails loudly if any MerkleNode or MerkleTree survives. Prevents regression
// to the old recursive design.

MATCH (n)
WHERE n:MerkleNode OR n:MerkleTree
WITH count(n) AS merkle_count
CALL apoc.util.validate(
  merkle_count > 0,
  'Invariant violation: %d MerkleNode/MerkleTree entities exist after protocol run',
  [merkle_count]
)
RETURN merkle_count AS merkle_count_should_be_zero;
