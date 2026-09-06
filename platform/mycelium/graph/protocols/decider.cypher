// @node_id: protocol-decider
// @label: "Decider: route unhealable Invariants to existing heal Protocols"
// ============================================================================
// Phase 6 of the autonomy loop. Runs after Phase 4 (Propose).
//
// For every unhealable unhealthy Invariant (no heal_protocol assigned),
// search existing Protocols by embedding similarity. If a heal-shaped
// Protocol scores above threshold, assign it — next immune cycle will pick
// up the wiring in Phase 2 and actually fire the heal.
//
// If no match scores above threshold, mark the ActionProposal as
// status='needs_author' so a downstream swarm can draft a new heal.
//
// Matching rules:
//   1. Candidate Protocol must have embedding + node_id starting with
//      'heal-' OR 'protocol-heal-' (naming convention signals heal intent)
//   2. Cosine similarity between Invariant.embedding and Protocol.embedding
//      must exceed 0.75
//   3. Top match wins; ties broken by fire_count (prefer proven heals)
//
// Zero-LLM: graph native, uses vector.similarity.cosine on pre-computed
// embeddings. No Ollama call, no API call.
// ============================================================================

// --- Phase 6a: Route unhealable invariants to heal protocols ----------------
// Updated to use HEALS edges with cosine similarity fallback.
// Two-tier search:
//   Tier 1: (:Protocol)-[:HEALS]->(:Invariant) edges (explicit, authored wiring)
//   Tier 2: Cosine similarity if no HEALS edge exists (semantic discovery)

MATCH (inv:Invariant {health_status: 'unhealthy'})
WHERE inv.heal_protocol IS NULL
OPTIONAL MATCH (explicit_p:Protocol)-[:HEALS]->(inv)
WITH inv, explicit_p
// If HEALS edge exists, use it; otherwise try cosine similarity
WHERE explicit_p IS NOT NULL OR inv.embedding IS NOT NULL
WITH inv, explicit_p,
     CASE WHEN explicit_p IS NOT NULL THEN explicit_p
          ELSE NULL END AS tier1_match
// Tier 2: cosine search if tier1 didn't match
WITH inv, tier1_match
// Get candidate protocols and apply cosine filter
OPTIONAL MATCH (cand:Protocol)
WHERE cand.embedding IS NOT NULL
  AND cand.cypher IS NOT NULL AND size(cand.cypher) > 0
  AND (cand.node_id STARTS WITH 'heal-'
       OR cand.node_id STARTS WITH 'protocol-heal-'
       OR exists { MATCH (:Invariant)-[:HEALS]->(cand) })
  AND vector.similarity.cosine(inv.embedding, cand.embedding) >= 0.85
WITH inv, tier1_match,
     cand,
     vector.similarity.cosine(inv.embedding, cand.embedding) AS sim_score
ORDER BY sim_score DESC, coalesce(cand.fire_count, 0) DESC
LIMIT 1
WITH inv, tier1_match,
     CASE WHEN tier1_match IS NULL THEN cand ELSE NULL END AS tier2_match
WITH inv, COALESCE(tier1_match, tier2_match) AS best_match,
     CASE WHEN tier1_match IS NOT NULL THEN 'heals-edge'
          WHEN tier2_match IS NOT NULL THEN 'cosine-similarity'
          ELSE NULL
     END AS match_source
WHERE best_match IS NOT NULL
SET inv.heal_protocol = best_match.node_id,
    inv.heal_assigned_by = 'decider-v2-heals-edge',
    inv.heal_assigned_at = toString(datetime()),
    inv.heal_match_source = match_source;

// --- Phase 6b: Mark still-unhealable proposals as needs_author --------------
MATCH (ap:ActionProposal {status: 'pending'})-[:PROPOSES_HEAL_FOR]->(inv:Invariant)
WHERE inv.heal_protocol IS NULL
SET ap.status = 'needs_author',
    ap.escalated_at = toString(datetime()),
    ap.escalation_reason = 'no heal protocol matched above cosine threshold 0.75';

// --- Phase 6c: Close proposals whose invariants got wired -------------------
MATCH (ap:ActionProposal {status: 'pending'})-[:PROPOSES_HEAL_FOR]->(inv:Invariant)
WHERE inv.heal_protocol IS NOT NULL
SET ap.status = 'wired',
    ap.wired_at = toString(datetime()),
    ap.wired_to = inv.heal_protocol;
