// @kind: seed
// ============================================================================
// Protocol: Skip Keys Init
// ============================================================================
// Initializes the SkipKey config nodes that drive merkle-properties.cypher.
// Each SkipKey represents a property name that must NOT contribute to a
// node's leaf_hash computation — either because it's a Merkle output (self-
// reference protection) or because it's a high-churn liveness property that
// would otherwise destroy root_hash stability.
//
// This protocol replaces the hardcoded skip_keys list that used to live
// inside merkle-properties.cypher. Moving config into the graph means:
//   - New skip_keys can be added with one MERGE statement
//   - The active skip-list is queryable (MATCH (sk:SkipKey) RETURN sk.key)
//   - Adding a skip_key is itself a Merkle-visible state change, because
//     the SkipKey nodes contribute their OWN leaf_hashes to the graph root
//
// Idempotent by MERGE on node_id. Safe to re-run.
// ============================================================================

MERGE (sk:SkipKey {node_id: 'skipkey-leaf_hash'})
  SET sk.key = 'leaf_hash',
      sk.category = 'merkle-output',
      sk.reason = 'Self-reference: a leaf_hash is the output of Merkle, cannot depend on itself without recursion';

MERGE (sk:SkipKey {node_id: 'skipkey-root_hash'})
  SET sk.key = 'root_hash',
      sk.category = 'merkle-output',
      sk.reason = 'root_hash lives on Being; including it would feed Being leaves back into the root computation';

MERGE (sk:SkipKey {node_id: 'skipkey-root_hash_computed_at'})
  SET sk.key = 'root_hash_computed_at',
      sk.category = 'merkle-output',
      sk.reason = 'Timestamp of the Merkle run, always changes between runs';

MERGE (sk:SkipKey {node_id: 'skipkey-leaf_count'})
  SET sk.key = 'leaf_count',
      sk.category = 'merkle-output',
      sk.reason = 'Count of leaves, computed by Merkle, lives on Being';

MERGE (sk:SkipKey {node_id: 'skipkey-last_heartbeat'})
  SET sk.key = 'last_heartbeat',
      sk.category = 'liveness',
      sk.reason = 'Liveness counter updated every heartbeat tick — would churn root_hash every beat if included';

MERGE (sk:SkipKey {node_id: 'skipkey-last_heartbeat_at'})
  SET sk.key = 'last_heartbeat_at',
      sk.category = 'liveness',
      sk.reason = 'Liveness timestamp, same rationale as last_heartbeat';

MERGE (sk:SkipKey {node_id: 'skipkey-heartbeat_count'})
  SET sk.key = 'heartbeat_count',
      sk.category = 'liveness',
      sk.reason = 'Monotonic heartbeat counter on Being';

RETURN 'skip-keys-init completed' AS status;
