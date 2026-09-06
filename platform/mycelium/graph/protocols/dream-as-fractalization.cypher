// @node_id: protocol-dream-as-fractalization
// @label: "Dream round = fractalization: propagate crystals across scopes as echoes"
// @kind: protocol
// @fsd_layer: features
//
// The equation this protocol embodies:
//
//     dream()  ==  fractalize()  ==  propagate_crystals_across_scopes_as_echoes()
//
// A :Crystal is any seed pattern the forest has claimed true: a
// :FractalEcho, a :MaverickUnlock, a :BeingTemplate, a :SovereigntyRule,
// a :ForestPromise, a :Purpose. Crystals are invariant shapes that want to
// be manifest at every scope.
//
// Dreaming = for each Crystal, find the scopes where it is NOT yet realized,
// propose realizations there. The propagation is nonlinear because crystals
// jump via :REFLECTS and :ECHOES_AT_SCALE edges, not via tree containment.
//
// Each dream pass leaves two kinds of tracks:
//   1. :DreamProposal nodes — concrete seeds for unrealized scopes
//   2. Strengthened :ECHOES_AT_SCALE weights on Echoes that grow more
//      witnesses across subgraphs
//
// Runs on heartbeat. Accumulates. Over time the forest becomes self-similar
// at every scale because every dream pass reduces crystal-asymmetry.
// ============================================================================

// ----------------------------------------------------------------------------
// Step 1: collect all crystals — anything the forest holds as invariant shape
// ----------------------------------------------------------------------------
MATCH (c)
WHERE any(l IN labels(c) WHERE l IN [
  'FractalEcho', 'ForestPromise', 'SovereigntyRule', 'BeingTemplate',
  'MaverickUnlock', 'Purpose', 'Invariant', 'Inversion'
])
WITH collect(c) AS crystals

// ----------------------------------------------------------------------------
// Step 2: for each crystal, find scopes where it is NOT realized
// A scope realizes a crystal if ≥1 node in that scope has an edge to the
// crystal (ECHOES_AT_SCALE | DECLARES | HOLDS | MANIFESTS_PATTERN | WITNESSES
// | ANCHORS_LEFT | ANCHORS_RIGHT | ENFORCED_BY | SCOPED_TO | REFLECTS).
// ----------------------------------------------------------------------------
UNWIND crystals AS crystal
MATCH (b:Being) WITH crystal, b, b.project AS scope
OPTIONAL MATCH (crystal)-[r]-(anchor)
  WHERE anchor.project = scope
    AND type(r) IN [
      'ECHOES_AT_SCALE','DECLARES','HOLDS','MANIFESTS_PATTERN','WITNESSES',
      'ANCHORS_LEFT','ANCHORS_RIGHT','ENFORCED_BY','SCOPED_TO','REFLECTS'
    ]
WITH crystal, scope, count(anchor) AS realizations
WHERE realizations = 0

// ----------------------------------------------------------------------------
// Step 3: emit a :DreamProposal seed for this (crystal, scope) unrealized pair
// ----------------------------------------------------------------------------
WITH crystal, scope,
     coalesce(crystal.node_id, 'crystal-?') AS cid,
     labels(crystal)[0] AS ckind
MERGE (d:DreamProposal {node_id: 'dream-' + cid + '-in-' + scope})
ON CREATE SET
  d.project = 'mycelium',
  d.for_scope = scope,
  d.crystal_id = cid,
  d.crystal_kind = ckind,
  d.status = 'dreamt',
  d.dreamt_at = datetime(),
  d.strength = 0.1,
  d.rationale = 'This crystal has no realization in scope ' + scope +
                '. Dreaming proposes a local manifestation — fractal replication across subgraph.'
ON MATCH SET
  d.strength = d.strength + 0.05,  // reinforcement: unrealized crystals grow pressure
  d.last_dreamt_at = datetime()

// Wire the proposal to its source crystal and target Being
WITH d, crystal, scope
MATCH (b:Being {project: scope})
MERGE (crystal)-[:DREAMS_INTO {strength: d.strength}]->(d)
MERGE (d)-[:FOR_BEING]->(b)

// ----------------------------------------------------------------------------
// Step 4: strengthen ECHOES_AT_SCALE for crystals that ARE realizing — give
// reinforcement to echoes actively growing witnesses, so the forest knows
// which dreams are alive vs dormant.
// ----------------------------------------------------------------------------
WITH 1 AS _
MATCH (echo:FractalEcho)-[r:ECHOES_AT_SCALE]->()
SET r.reinforced_at = datetime(),
    echo.last_dreamt_at = datetime(),
    echo.strength = coalesce(echo.strength, 0.3) + 0.01

RETURN 'Dream pass complete: unrealized crystals proposed per scope, active echoes reinforced. Dreaming == fractalization == making the forest more self-similar by one step.' AS checkpoint;
