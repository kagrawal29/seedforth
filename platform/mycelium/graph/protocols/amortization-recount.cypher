// @node_id: protocol-amortization-recount
// @label: "Amortization Recount (Daily — comprehensive status update)"
// ============================================================================
// Protocol: Amortization Recount (Daily — comprehensive status update)
// ============================================================================
// PROBLEM: Heartbeat Phase 8 only fires every 10th heartbeat, causing stale
// amortization status. Most protocols show no status even with active atoms.
//
// SOLUTION: Every heartbeat, recompute each Protocol's amortization status by:
// 1. Counting CypherAtoms logically linked to the protocol
// 2. Summing their fire_count values
// 3. Setting Protocol.total_fires and amortization_status
// 4. Tracking when the recount happened
//
// ECONOMICS:
// - fire_count = 0: 'dead' (never executed)
// - fire_count 1-9: 'un-amortized' (used but LLM cost not yet recovered)
// - fire_count 10-99: 'amortizing' (on track to break even)
// - fire_count 100+: 'amortized' (LLM cost recovered, pure value)
// ============================================================================

// Step 1: For each Protocol, find all related CypherAtoms and sum their fire_count
// Atoms can be linked via HAS_ATOM, INVOKES, or RESOLVES_TO relationships
MATCH (p:Protocol)
WHERE p.node_id IS NOT NULL
OPTIONAL MATCH (p)-[:HAS_ATOM|INVOKES|RESOLVES_TO]->(atom:CypherAtom)
WITH p,
     collect(distinct atom) AS atoms,
     sum(coalesce(atom.fire_count, 0)) AS total_fires_from_atoms

// Step 2: Also consider fire_count directly on Protocol if it exists
WITH p, atoms, total_fires_from_atoms,
     coalesce(p.fire_count, 0) AS direct_fire_count

// Step 3: Sum both sources (atoms + direct)
WITH p, atoms, total_fires_from_atoms,
     direct_fire_count,
     total_fires_from_atoms + direct_fire_count AS total_fires_combined

// Step 4: Determine amortization status based on fire count
WITH p, atoms, total_fires_combined,
     CASE
       WHEN total_fires_combined = 0 THEN 'dead'
       WHEN total_fires_combined >= 1 AND total_fires_combined <= 9 THEN 'un-amortized'
       WHEN total_fires_combined >= 10 AND total_fires_combined <= 99 THEN 'amortizing'
       WHEN total_fires_combined >= 100 THEN 'amortized'
       ELSE 'unknown'
     END AS new_status

// Step 5: Update Protocol with computed values
SET p.total_fires = total_fires_combined,
    p.amortization_status = new_status,
    p.amortization_recount_at = toString(datetime()),
    p.atom_count = size(atoms)

// Step 6: Return summary for verification
RETURN
  p.name AS protocol_name,
  size(atoms) AS atom_count,
  total_fires_combined AS total_fires,
  new_status AS amortization_status,
  p.enabled AS enabled
ORDER BY total_fires_combined DESC;
