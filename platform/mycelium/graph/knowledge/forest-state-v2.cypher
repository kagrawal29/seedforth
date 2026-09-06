// @node_id: forest-state-v2
// @label: "Forest state v2 — fractal primitives added to the promise"
// @kind: knowledge
//
// v2 extends the Forest Promise's allowed bridges with the three edges needed
// for fractal manifestation: REFLECTS, ECHOES_AT_SCALE, MANIFESTS_PATTERN.
// Adds the invariant that enforces fractality: every :FractalEcho must witness
// >=2 distinct scales. Adds :ScaleMarker seeds for the 7 canonical scales.
//
// Idempotent. Safe to re-run. Requires v1 to already exist.
// ============================================================================

// ----------------------------------------------------------------------------
// 1. Extend allowed_bridges on the no-silent-cross-writes rule
// ----------------------------------------------------------------------------
MATCH (r:SovereigntyRule {node_id: 'rule-no-silent-cross-writes'})
SET r.allowed_bridges = apoc.coll.toSet(r.allowed_bridges + [
  'REFLECTS',             // any node ↔ any node, same pattern at different positions
  'ECHOES_AT_SCALE',      // :FractalEcho → witness node at a named scale
  'MANIFESTS_PATTERN',    // :FractalEcho → :Pattern node describing the shape
  'RESONATES',            // cross-agent finding feedback (unlock #9)
  'WITNESSES',            // :FractalEcho → evidence node
  'FIRED_WITH',           // Hebbian co-firing between cross-subgraph nodes
  'HEARD_FROM'            // :PanelSession → node that resonated during panel
]);

// ----------------------------------------------------------------------------
// 2. New invariant: every :FractalEcho has >=2 scales
// ----------------------------------------------------------------------------
MERGE (inv:Invariant {node_id: 'invariant-fractal-echo-multi-scale'})
SET inv.label = 'Every :FractalEcho witnesses >=2 distinct scales',
    inv.project = 'mycelium',
    inv.severity = 'warning',
    inv.fsd_layer = 'shared',
    inv.scope = 'forest-wide',
    inv.enforced_by = 'forest-promise-sovereignty',
    inv.check_cypher =
      'MATCH (e:FractalEcho) OPTIONAL MATCH (e)-[r:ECHOES_AT_SCALE]->() ' +
      'WITH e, count(DISTINCT r.scale) AS scales WHERE scales < 2 ' +
      'RETURN count(e) AS violations',
    inv.heal_protocol = 'protocol-prune-solo-scale-echoes';

MATCH (promise:ForestPromise {node_id:'forest-promise-sovereignty'}),
      (inv:Invariant {node_id:'invariant-fractal-echo-multi-scale'})
MERGE (promise)-[:DECLARES]->(inv);

// ----------------------------------------------------------------------------
// 3. :ScaleMarker seeds — the 7 canonical scales
// ----------------------------------------------------------------------------
UNWIND [
  {id: 'scale-atom',         name: 'atom',         note: 'smallest executable unit: CypherAtom, CodeConst, File line'},
  {id: 'scale-protocol',     name: 'protocol',     note: 'composed behavior: Protocol, CodeFunction, RecipeCard'},
  {id: 'scale-conversation', name: 'conversation', note: 'discourse unit: QueryTrace, ConversationTrace, ThreadNode'},
  {id: 'scale-commit',       name: 'commit',       note: 'history unit: Commit, GitCommit, PR, Migration'},
  {id: 'scale-being',        name: 'being',        note: 'metabolic center: one per sovereign subgraph'},
  {id: 'scale-project',      name: 'project',      note: 'sovereign namespace: :Project {name:X}'},
  {id: 'scale-forest',       name: 'forest',       note: 'all projects together under one Promise'}
] AS s
MERGE (m:ScaleMarker {node_id: s.id})
SET m.project = 'mycelium',
    m.name = s.name,
    m.note = s.note,
    m.declared_at = coalesce(m.declared_at, datetime());

// ----------------------------------------------------------------------------
// 4. Connect ScaleMarkers to the Promise so they're discoverable
// ----------------------------------------------------------------------------
MATCH (promise:ForestPromise {node_id:'forest-promise-sovereignty'}),
      (m:ScaleMarker)
MERGE (promise)-[:SCOPES_TO]->(m);

RETURN 'Forest state v2: fractal bridges allowed, multi-scale invariant declared, 7 ScaleMarkers seeded.' AS checkpoint;
