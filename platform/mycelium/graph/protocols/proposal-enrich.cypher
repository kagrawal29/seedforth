// @node_id: protocol-proposal-enrich
// @label: "Enrich ActionProposal with neighbor context (Phase 4.5)"
// ============================================================================
// Protocol: Proposal Enrichment — metadata for Decider routing
// ============================================================================
// Phase 4.5 (between Propose and Decider):
// For each pending/needs_author ActionProposal, attach:
//   - invariant_node_id (already linked, extract for convenience)
//   - neighbor_invariants (list of other invariants in similar health/scale)
//   - similar_successful_heals (top-3 Protocol node_ids by cosine similarity,
//     filtered to those with prior successful fires)
//   - subsystem (the domain the invariant belongs to, inferred from context)
//   - last_check_output (snippet from the failing invariant's last check)
//   - enrichment_at (timestamp)
//
// This enriched data flows into Phase 6 (Decider) for better routing.
// ============================================================================

MATCH (ap:ActionProposal)
WHERE ap.status IN ['pending', 'needs_author']
  AND ap.invariant IS NOT NULL

// Get the invariant this proposal is about
MATCH (inv:Invariant {node_id: ap.invariant})

// Extract invariant details
WITH ap, inv,
     inv.node_id AS inv_node_id,
     inv.label AS inv_label,
     inv.health_status AS inv_health,
     inv.embedding AS inv_embedding,
     inv.check_cypher AS check_cypher,
     inv.subsystem AS current_subsystem

// Find neighbor invariants in same scale or health context
OPTIONAL MATCH (neighbor:Invariant)
WHERE neighbor.node_id <> inv.node_id
  AND (
    neighbor.health_status = inv_health
    OR (neighbor.subsystem = current_subsystem AND current_subsystem IS NOT NULL)
  )
WITH ap, inv, inv_node_id, inv_label, inv_health, inv_embedding,
     check_cypher, current_subsystem,
     collect(DISTINCT neighbor.node_id) AS neighbor_invariants

// Find similar healing protocols (by embedding cosine similarity, if embedding exists)
// Filter to those with prior successful fires (fire_count > 0)
WITH ap, inv, inv_node_id, inv_label, inv_health, inv_embedding,
     check_cypher, current_subsystem, neighbor_invariants,
     CASE WHEN inv_embedding IS NOT NULL THEN true ELSE false END as has_embedding
OPTIONAL MATCH (heal:Protocol)
WHERE heal.cypher IS NOT NULL
  AND heal.fire_count > 0
  AND heal.embedding IS NOT NULL
  AND has_embedding = true
WITH ap, inv, inv_node_id, inv_label, inv_health, inv_embedding,
     check_cypher, current_subsystem, neighbor_invariants,
     heal,
     vector.similarity.cosine(inv_embedding, heal.embedding) AS sim_score
ORDER BY sim_score DESC
LIMIT 3
WITH ap, inv, inv_node_id, inv_label, inv_health, inv_embedding,
     check_cypher, current_subsystem, neighbor_invariants,
     collect(heal.node_id) AS similar_successful_heals

// Infer subsystem from invariant context if not set
WITH ap, inv, inv_node_id, inv_label, inv_health, inv_embedding,
     check_cypher, current_subsystem, neighbor_invariants, similar_successful_heals,
     CASE
       WHEN current_subsystem IS NOT NULL THEN current_subsystem
       WHEN inv_label CONTAINS 'health' THEN 'core-health'
       WHEN inv_label CONTAINS 'heal' THEN 'sub-healing'
       WHEN inv_label CONTAINS 'measure' OR inv_label CONTAINS 'metric' THEN 'sub-measurement'
       ELSE 'core-general'
     END AS inferred_subsystem

// Enrich the ActionProposal node
SET ap.invariant_node_id = inv_node_id,
    ap.neighbor_invariants = neighbor_invariants,
    ap.similar_successful_heals = similar_successful_heals,
    ap.subsystem = inferred_subsystem,
    ap.last_check_output = coalesce(ap.last_check_output, 'check_cypher: ' + substring(check_cypher, 0, 80)),
    ap.enrichment_at = toString(datetime())

// Return summary for trace
RETURN ap.node_id,
       ap.status,
       ap.subsystem,
       size(neighbor_invariants) AS neighbor_count,
       size(similar_successful_heals) AS heal_protocol_count;
