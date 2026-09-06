// @node_id: protocol-immune-cycle
// @label: "Immune Cycle — detect, heal, recheck, propose, score (graph-native)"
// ============================================================================
// Protocol: Immune Cycle (cypher-native, closed heal loop)
// ============================================================================
// Replaces graph/runner/immune-cycle.{sh,py} which ran from bash/python
// and had an open loop (marked invariants as needing heal but never dispatched).
//
// Flow (all phases in one cypher invocation via apoc.cypher.runMany):
//   1. DETECT  — apoc.cypher.run(inv.check_cypher) for every enabled invariant,
//                set health_status = healthy | unhealthy
//   2. HEAL    — for unhealthy WITH heal_protocol, apoc.cypher.run(heal.cypher)
//   3. RECHECK — re-run check_cypher after heal, update health_status again
//   4. PROPOSE — for unhealthy WITHOUT heal_protocol, MERGE ActionProposal
//   5. SCORE   — update Being.autonomous_score + roll-up counters
//
// Reading the result after this runs:
//   - every Invariant has a fresh health_status + last_checked
//   - every heal Protocol has bumped fire_count
//   - every unhealable unhealthy invariant has a live ActionProposal
// ============================================================================

// --- PHASE 1: Detect --------------------------------------------------------
// Evaluate each invariant's check_cypher dynamically via APOC.
// Result interpretation:
//   - any row with r = false        -> unhealthy
//   - any row with r IS NULL        -> unhealthy
//   - empty result (no rows)        -> vacuously healthy (no violations found)
//   - all rows truthy               -> healthy
MATCH (inv:Invariant)
WHERE inv.check_cypher IS NOT NULL
  AND inv.node_id IS NOT NULL
  AND coalesce(inv.enabled, true) = true
CALL apoc.cypher.run(inv.check_cypher, {}) YIELD value
WITH inv, value, keys(value)[0] AS result_key
WITH inv, collect(value[result_key]) AS results
WITH inv,
     CASE
       WHEN any(r IN results WHERE r = false) THEN 'unhealthy'
       WHEN any(r IN results WHERE r IS NULL) THEN 'unhealthy'
       ELSE 'healthy'
     END AS new_status
SET inv.health_status = new_status,
    inv.last_checked = toString(datetime());

// --- PHASE 2+3: Heal + Recheck (the critical missing step) ------------------
// For each unhealthy invariant that has a heal_protocol pointing to a
// Protocol with executable cypher, actually run the heal and then recheck.
// If the heal worked, health_status flips back to 'healthy'.
MATCH (inv:Invariant {health_status: 'unhealthy'})
WHERE inv.heal_protocol IS NOT NULL
MATCH (heal:Protocol {node_id: inv.heal_protocol})
WHERE heal.cypher IS NOT NULL AND size(heal.cypher) > 0
CALL apoc.cypher.runMany(heal.cypher, {}) YIELD result AS _heal_result
WITH inv, heal, count(_heal_result) AS _n
SET heal.fire_count = coalesce(heal.fire_count, 0) + 1,
    heal.last_fired_at = toString(datetime())
WITH inv, heal
CALL apoc.cypher.run(inv.check_cypher, {}) YIELD value
WITH inv, heal, value, keys(value)[0] AS result_key
WITH inv, heal, collect(value[result_key]) AS results
WITH inv, heal,
     CASE
       WHEN any(r IN results WHERE r = false) THEN 'unhealthy'
       WHEN any(r IN results WHERE r IS NULL) THEN 'unhealthy'
       ELSE 'healthy'
     END AS post_heal_status
SET inv.health_status = post_heal_status,
    inv.heal_attempted_at = toString(datetime()),
    inv.heal_outcome = post_heal_status,
    inv.healed_by = heal.node_id;

// --- PHASE 4: Propose ActionProposals for unhealable unhealthy --------------
// Invariants without a heal_protocol can't self-heal — surface them to
// humans as ActionProposals so they're visible, actionable work items.
// Link PROPOSES_HEAL_FOR to the invariant so the proposal can be closed
// programmatically when someone assigns a heal_protocol later.
MATCH (inv:Invariant {health_status: 'unhealthy'})
WHERE inv.heal_protocol IS NULL
MERGE (ap:ActionProposal {node_id: 'ap-heal-' + inv.node_id})
  ON CREATE SET ap.created_at = toString(datetime()),
                ap.reason = 'invariant unhealthy, no heal_protocol assigned',
                ap.invariant = inv.node_id,
                ap.invariant_label = coalesce(inv.label, inv.node_id),
                ap.proposed_action = 'assign heal_protocol or resolve manually',
                ap.status = 'pending'
  ON MATCH SET ap.last_seen = toString(datetime()),
               ap.status = coalesce(ap.status, 'pending')
MERGE (ap)-[:PROPOSES_HEAL_FOR]->(inv);

// --- PHASE 4.5: Enrich ActionProposals with neighbor context ---------------
// Delegate to protocol-proposal-enrich for structured metadata attachment
MATCH (enrich:Protocol {node_id: 'protocol-proposal-enrich'})
WHERE enrich.cypher IS NOT NULL AND size(enrich.cypher) > 0
CALL apoc.cypher.runMany(enrich.cypher, {}) YIELD result AS _e
RETURN count(_e) AS _enrich_count;

// --- PHASE 6: Decider — route unhealable invariants to heal protocols -------
// Delegates to protocol-decider. Graph-native, zero-LLM routing via
// vector.similarity.cosine between Invariant and candidate Protocol
// embeddings. Writes are multi-statement so we use runMany.
MATCH (dec:Protocol {node_id: 'protocol-decider'})
WHERE dec.cypher IS NOT NULL AND size(dec.cypher) > 0
CALL apoc.cypher.runMany(dec.cypher, {}) YIELD result AS _d
RETURN count(_d) AS _decider_statements;

// --- PHASE 5: Update autonomous_score on Being ------------------------------
// Fractal rollup — one number summarizing system health.
MATCH (inv:Invariant) WHERE coalesce(inv.enabled, true) = true
WITH count(inv) AS total,
     sum(CASE WHEN inv.health_status = 'healthy' THEN 1 ELSE 0 END) AS healthy,
     sum(CASE WHEN inv.health_status = 'unhealthy' THEN 1 ELSE 0 END) AS unhealthy,
     sum(CASE WHEN inv.health_status = 'unknown' OR inv.health_status IS NULL THEN 1 ELSE 0 END) AS unknown
MATCH (b:Being {node_id: 'being-mycelium'})
SET b.invariants_total = total,
    b.invariants_healthy = healthy,
    b.invariants_unhealthy = unhealthy,
    b.invariants_unknown = unknown,
    b.autonomous_score = CASE WHEN total > 0 THEN (healthy * 100 / total) ELSE 0 END,
    b.last_immune_cycle = toString(datetime());
