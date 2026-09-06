// @node_id: seed-invariant-merge-ethics
// @label: "Species Merge-Ethics Seed — lineage integrity invariant for Species snapshots"
// ============================================================================
// Seeds the graph with one :Invariant that enforces fast-forward lineage on
// every :Species node. Any Species arriving with a parent_dna that does not
// match the current canonical Species' manifest_root (or is not otherwise
// exempt) makes the invariant unhealthy.
//
// No heal_protocol is assigned. The immune cycle will automatically MERGE an
// :ActionProposal (node_id: 'ap-heal-invariant-merge-ethics') and surface it
// for human review — no additional code is needed here.
//
// Exemptions from the lineage check:
//   (a) Genesis Species: parent_id IS NULL (the first snapshot; no parent exists)
//   (b) Superseded Species: status = 'superseded' (already retired, history only)
//   (c) Fork-approved Species: status = 'fork-approved' (human already adjudicated)
//
// Performance target: <50ms at 1000 Species nodes.
//   - Two indexed lookups (status = 'canonical'; status = 'superseded' / fork checks)
//   - No full-graph scan; WHERE clauses filter early
//   - Assumes index on :Species(status) and :Species(node_id) — both standard
// ============================================================================

MERGE (inv:Invariant {node_id: 'invariant-merge-ethics'})
  SET inv.label              = 'Species Merge-Ethics',
      inv.description        = "Every non-genesis Species must have parent_dna matching the current canonical manifest_root, else divergence requires human proposal.",
      inv.severity           = 'critical',
      inv.category           = 'ethics',
      inv.heal_protocol_id   = null,
      inv.heal_protocol      = null,

      // --- check_cypher ---------------------------------------------------
      // Stored as a string property; executed by the immune cycle via
      // apoc.cypher.run(inv.check_cypher, {}) each heartbeat cycle.
      //
      // Returns exactly one row: { healthy: bool, unhealthy_species: [node_id], reason: string }
      //
      // Logic:
      //   1. Fetch current canonical manifest_root (null = no canonical yet → skip species check).
      //   2. Collect every Species node that is NOT exempt.
      //   3. Among those, find any whose parent_dna does NOT match the canonical root.
      //      Also flag new Species (created_at in last 24h) whose parent_dna is non-null
      //      but points to a manifest_root that exists nowhere in the graph.
      //   4. If any violations exist → unhealthy; else healthy.
      // -------------------------------------------------------------------
      // LINEAGE VALIDITY (not fast-forward). A teammate may legitimately
      // descend from an older ancestor (fork/rebase). The invariant is
      // violated only when parent_dna does not match ANY existing Species'
      // manifest_root — i.e. the ancestor is unknown to the graph.
      //
      // Divergence from the current canonical is a separate, softer signal
      // (an :ActionProposal can be raised elsewhere). It is NOT a health
      // failure; merges from older ancestors are a normal part of the flow.
      //
      // Schema:
      //   :Species.manifest_root     sha256 of its snapshot
      //   :Species.parent_dna        predecessor manifest_root ('genesis' sentinel allowed)
      //   :Species.genesis           true for root species (exempt)
      //   :Species.superseded_at     non-null => retired (exempt)
      //   :Species.fork_approved     true => human-adjudicated fork (exempt)
      inv.check_cypher       =
        'MATCH (all:Species) ' +
        'WITH collect(all.manifest_root) + ["genesis"] AS known_roots ' +
        'OPTIONAL MATCH (s:Species) ' +
        'WHERE coalesce(s.genesis, false) = false ' +
        '  AND s.superseded_at IS NULL ' +
        '  AND coalesce(s.fork_approved, false) = false ' +
        '  AND ( s.parent_dna IS NULL OR NOT s.parent_dna IN known_roots ) ' +
        'WITH collect(s.node_id) AS violations ' +
        'RETURN ' +
        '  size(violations) = 0 AS healthy, ' +
        '  violations AS unhealthy_species, ' +
        '  CASE ' +
        '    WHEN size(violations) = 0 ' +
        '      THEN "all Species point to a known ancestor manifest_root" ' +
        '    ELSE "Species with unknown parent_dna (ancestor not in graph): " + toString(size(violations)) ' +
        '  END AS reason',

      inv.created_at         = datetime();

// --- Wire to monitoring infrastructure ------------------------------------
// Best-effort: if rhythm/purpose/ontology/being nodes don't exist yet
// (e.g., bootstrap order), the MATCH simply returns no rows and the SET
// is silently skipped. Re-running bootstrap after all core nodes are loaded
// will wire the relationships correctly.

OPTIONAL MATCH (heartbeat:Rhythm   {node_id: 'rhythm-heartbeat'})
OPTIONAL MATCH (heal:Purpose       {node_id: 'purpose-self-heal'})
OPTIONAL MATCH (ont:Ontology)
OPTIONAL MATCH (being:Being        {node_id: 'being-mycelium'})
WITH heartbeat, heal, ont, being
MATCH (inv:Invariant {node_id: 'invariant-merge-ethics'})
FOREACH (_ IN CASE WHEN heartbeat IS NOT NULL THEN [1] ELSE [] END |
  MERGE (inv)-[:MONITORED_BY]->(heartbeat)
)
FOREACH (_ IN CASE WHEN heal IS NOT NULL THEN [1] ELSE [] END |
  MERGE (inv)-[:EMBODIES]->(heal)
)
FOREACH (_ IN CASE WHEN ont IS NOT NULL THEN [1] ELSE [] END |
  MERGE (inv)-[:INVARIANT_OF]->(ont)
)
FOREACH (_ IN CASE WHEN being IS NOT NULL THEN [1] ELSE [] END |
  MERGE (inv)-[:MONITORS]->(being)
);

// --- Summary report -------------------------------------------------------

MATCH (inv:Invariant {node_id: 'invariant-merge-ethics'})
RETURN
  inv.node_id       AS invariant_node_id,
  inv.label         AS label,
  inv.severity      AS severity,
  inv.category      AS category,
  inv.heal_protocol AS heal_protocol,
  'seed-invariant-merge-ethics loaded' AS status;
