// @node_id: protocol-mint-if-dirty
// @label: "Conditional Species Mint on Graph Mutation"
// ============================================================================
// Protocol: Checks for pending mutations (dirty flag) and mints a new Species
// if conditions are met. Runs on heartbeat cadence.
//
// Decision tree:
//   1. Check if DirtyState.dirty = true (mutations observed since last mint)
//   2. Check settle window: at least N seconds since DirtyState.touched_at
//      (default 60s, prevents minting mid-bootstrap)
//   3. Check graph health: autonomous_score = 100 AND no unhealed invariants
//   4. If all pass: invoke existing mint machinery to create new Species
//   5. Clear dirty flag atomically (CAS via OPTIONAL MATCH ... SET ... RETURN)
//   6. Emit MintLog for observability
//
// If graph is unhealthy, do nothing. The immune cycle will heal first.
// If settle window not elapsed, do nothing. Retry next heartbeat.
//
// Settle window: configurable per Being (default 60 seconds)
// ============================================================================

// Configuration (query Being for override)
MATCH (b:Being {node_id: 'being-mycelium'})
WITH b, coalesce(b.mint_settle_window_sec, 60) AS settle_window
OPTIONAL MATCH (ds:DirtyState {node_id: 'dirty-state-mint-trigger'})
WITH b, ds, settle_window,
     CASE
       WHEN ds IS NULL THEN false
       WHEN ds.dirty = false THEN false
       WHEN ds.touched_at IS NULL THEN false
       WHEN duration.inSeconds(ds.touched_at, datetime()).seconds < settle_window
         THEN false
       ELSE true
     END AS settle_window_elapsed

// Check graph health
WITH b, ds, settle_window, settle_window_elapsed
WITH b, ds, settle_window, settle_window_elapsed,
     coalesce(b.autonomous_score, 0) = 100 AS is_healthy

// Check for unhealed invariants
WITH b, ds, settle_window, settle_window_elapsed, is_healthy
OPTIONAL MATCH (inv:Invariant {health_status: 'unhealthy'})
WITH b, ds, settle_window, settle_window_elapsed, is_healthy,
     COUNT(inv) AS unhealthy_invariant_count

// Decision gate
WITH b, ds, settle_window, settle_window_elapsed, is_healthy,
     unhealthy_invariant_count,
     (settle_window_elapsed AND
      is_healthy AND
      unhealthy_invariant_count = 0) AS should_mint

OPTIONAL MATCH (current:Species)<-[:CURRENT_SPECIES]-(b)
WITH b, ds, settle_window, settle_window_elapsed, is_healthy,
     unhealthy_invariant_count, should_mint, current

// --- Mint phase (only if should_mint = true) -----
CALL apoc.do.when(
  should_mint,
  // True branch: mint new Species
  '
    MATCH (b:Being {node_id: "being-mycelium"})
    MATCH (current:Species)<-[:CURRENT_SPECIES]-(b)
    WITH b, current, current.manifest_root AS parent_dna
    // Create new Species node (digest of current state)
    MERGE (new:Species {node_id: "species-" + apoc.text.random(8)})
    ON CREATE SET
      new:CanonicalSpecies,
      new.label = "Species " + toString(datetime()),
      new.algorithm = "phase-b-v1",
      new.genesis = false,
      new.canonical = true,
      new.signed = false,
      new.parent_dna = parent_dna,
      new.manifest_root = b.root_hash,
      new.quorum_required = 1,
      new.git_branch = "species/" + apoc.text.random(8),
      new.minted_at = toString(datetime()),
      new.minted_from = "protocol-mint-if-dirty",
      new.file_type = "species",
      new.description = "Auto-minted Species from mutation detection (dirty flag settle window elapsed)"
    // Advance :CURRENT_SPECIES edge
    WITH b, current, new
    MATCH (b)-[old:CURRENT_SPECIES]->(current)
    DELETE old
    MERGE (b)-[:CURRENT_SPECIES]->(new)
    // Link via :BEGETS for lineage
    MERGE (current)-[:BEGETS]->(new)
    RETURN new.node_id AS minted_species_id, new.manifest_root AS manifest_root, "minted" AS action
  ',
  // False branch: do nothing
  'RETURN "no_mint" AS action'
) YIELD value AS mint_result

// --- Clear dirty flag (if mint succeeded) -----
WITH b, ds, settle_window_elapsed, is_healthy, unhealthy_invariant_count,
     should_mint, mint_result
OPTIONAL MATCH (ds_check:DirtyState {node_id: 'dirty-state-mint-trigger', dirty: true})
SET ds_check.dirty = false,
    ds_check.last_cleared_at = datetime(),
    ds_check.last_cleared_reason = CASE
      WHEN should_mint THEN "species_minted"
      WHEN NOT settle_window_elapsed THEN "settle_window_not_elapsed"
      WHEN NOT is_healthy THEN "graph_unhealthy"
      WHEN unhealthy_invariant_count > 0 THEN "unhealed_invariants"
      ELSE "unknown"
    END

// --- Emit MintLog for observability -----
WITH b, ds, mint_result, settle_window_elapsed, is_healthy, unhealthy_invariant_count
MERGE (log:MintLog {timestamp: datetime()})
SET log.settle_window_elapsed = settle_window_elapsed,
    log.is_healthy = is_healthy,
    log.unhealthy_invariant_count = unhealthy_invariant_count,
    log.mint_result = mint_result.action,
    log.minted_species_id = mint_result.minted_species_id // null if no mint
MERGE (b)-[:RECORDED_MINT_LOG]->(log)

// --- Summary -----
RETURN
  settle_window_elapsed AS settle_window_elapsed,
  is_healthy AS graph_healthy,
  unhealthy_invariant_count AS unhealthy_count,
  mint_result.action AS mint_action,
  mint_result.minted_species_id AS new_species_id;
