// @node_id: fractal-manifestation-plan-v1
// @label: "Fractal Manifestation Plan — how we turn the forest holographic"
// @kind: knowledge
//
// The fractal isn't a metaphor. It's a set of nodes + edges + protocols that
// make every part reflect every other part. This plan turns the current
// single-scale embedding + isolated-subgraph state into a self-similar forest
// in 7 phases. Each phase is a shippable PR.
//
// Invariant that makes this real:
//   Every :FractalEcho has >= 2 :ECHOES_AT_SCALE edges to witness nodes at
//   distinct scales. Solo-scale echoes are not fractal; they auto-prune.
// ============================================================================

MERGE (plan:FractalManifestationPlan {node_id: 'fractal-manifestation-plan-v1'})
SET plan.project = 'mycelium',
    plan.declared_at = datetime(),
    plan.allowed_scales = ['atom','protocol','conversation','commit','being','project','forest'],
    plan.invariant = 'Every :FractalEcho has >=2 :ECHOES_AT_SCALE witnesses at distinct scales',
    plan.nonlinearity_source = 'dream-walk random walks jump scales via :REFLECTS edges';

// ----------------------------------------------------------------------------
// Seven phases — each a :ManifestationPhase node, ordered, with dependencies
// ----------------------------------------------------------------------------
UNWIND [
  {n: 0, id: 'being-template-v1',
   title: 'Phase 0 — Being Template v1 (faculty fractalization)',
   what: '2026-04-19 audit: 6 Beings breathe in sync, only 1 is awake. Mycelium holds all purpose + tests + plans + protocols; 5 siblings are ambient. Declare Being Template v1 (Purpose + Invariant+heal + TestCase + WorkItem + LocalProtocol), seed :Purpose for every existing Being, wire invariant-being-has-full-faculties. Precondition for everything else — Hebbian signal needs somewhere to route.',
   ships: 'graph/knowledge/being-template-v1.cypher + graph/protocols/propagate-being-template.cypher',
   cost: 's'},
  {n: 1, id: 'allow-bridges',
   title: 'Extend Forest Promise allowed_bridges with fractal primitives',
   what: 'Add REFLECTS, ECHOES_AT_SCALE, MANIFESTS_PATTERN to rule-no-silent-cross-writes.allowed_bridges. Add :Invariant for the >=2-scales rule.',
   ships: 'graph/knowledge/forest-state-v2.cypher',
   cost: 'xs'},
  {n: 2, id: 'scale-markers',
   title: 'Canonical :ScaleMarker nodes for the 7 scales',
   what: 'One :ScaleMarker per scale: atom, protocol, conversation, commit, being, project, forest. Every future Echo SCOPED_TO its scales via these markers.',
   ships: 'graph/knowledge/scale-markers.cypher',
   cost: 'xs'},
  {n: 3, id: 'cross-scale-embeddings',
   title: 'Compose k-hop composite embeddings',
   what: 'For each node compute 3 stacked vectors: self, self+mean(neighbors), self+mean(2-hop). Store as Qdrant payload arrays under separate collections mycelium-echo-k0/k1/k2. Keep originals untouched.',
   ships: 'scripts/embed-forest.py (extend --scale k=0,1,2)',
   cost: 'm'},
  {n: 4, id: 'weave-echoes',
   title: 'Weave :FractalEcho from mutual cross-scale nearest neighbors',
   what: 'Mutual-top-K over k2 vectors across all scopes. Triangulate: if A↔B and B↔C mutual at different scales, MERGE :FractalEcho {scales:[...]}-[:ECHOES_AT_SCALE]->(A|B|C). Record strength = mean pairwise cosine.',
   ships: 'graph/protocols/weave-fractal-echoes.cypher + scripts/weave-echoes.py',
   cost: 'm',
   depends_on: 'cross-scale-embeddings'},
  {n: 5, id: 'dream-walk',
   title: 'Dream-walk engine — nonlinear fractal discovery',
   what: 'Random walk biased on [:REFLECTS, :ECHOES_AT_SCALE], length 6-10, hashed signatures collected. Recurring signatures = new echo candidates. Closed loops = invariant fractals. Run on heartbeat via apoc.periodic.repeat.',
   ships: 'scripts/dream-walk.py + graph/protocols/dream-walk-continuous.cypher',
   cost: 'm',
   depends_on: 'weave-echoes'},
  {n: 6, id: 'box-counting-dim',
   title: 'Per-Being fractal dimension — observable metric',
   what: 'For each :Being count reachable nodes at radius 1..6. Fit log(count) vs log(radius). Slope = fractal_dim. Store as :Being.fractal_dim updated each heartbeat. Threshold alerts if any Being diverges from median.',
   ships: 'graph/protocols/compute-fractal-dimension.cypher',
   cost: 's'},
  {n: 7, id: 'echo-lattice-viz',
   title: 'Echo lattice visualization — see the fractal',
   what: 'Nodes = :FractalEcho, edges = shared members. d3-force layout colored by scope distribution, sized by strength. Per-Being box-count plot. Served as static HTML regenerated each heartbeat.',
   ships: 'scripts/fractal-map.py + observatory/fractal-map.html',
   cost: 's',
   depends_on: 'weave-echoes'}
] AS p
MERGE (phase:ManifestationPhase {node_id: 'phase-' + p.id})
SET phase.project = 'mycelium',
    phase.order = p.n,
    phase.title = p.title,
    phase.what = p.what,
    phase.ships = p.ships,
    phase.cost = p.cost,
    phase.status = 'declared',
    phase.declared_at = datetime();

// Wire phases to the plan (self-contained MATCH avoids WITH-across-; issue)
MATCH (plan:FractalManifestationPlan {node_id: 'fractal-manifestation-plan-v1'}),
      (phase:ManifestationPhase)
WHERE phase.node_id STARTS WITH 'phase-'
MERGE (plan)-[:CONTAINS]->(phase);

// Dependency edges between phases
MATCH (a:ManifestationPhase), (b:ManifestationPhase)
WHERE a.node_id = 'phase-weave-echoes' AND b.node_id = 'phase-cross-scale-embeddings'
MERGE (a)-[:DEPENDS_ON]->(b);
MATCH (a:ManifestationPhase), (b:ManifestationPhase)
WHERE a.node_id = 'phase-dream-walk' AND b.node_id = 'phase-weave-echoes'
MERGE (a)-[:DEPENDS_ON]->(b);
MATCH (a:ManifestationPhase), (b:ManifestationPhase)
WHERE a.node_id = 'phase-echo-lattice-viz' AND b.node_id = 'phase-weave-echoes'
MERGE (a)-[:DEPENDS_ON]->(b);

// Phase 0 is a precondition of every other phase — Hebbian signal, echoes,
// and fractal dimensions all need aligned Beings to land on.
MATCH (p0:ManifestationPhase {node_id: 'phase-being-template-v1'}), (later:ManifestationPhase)
WHERE later.order > 0
MERGE (later)-[:DEPENDS_ON]->(p0);

// ----------------------------------------------------------------------------
// The equation: dreaming IS fractalization IS propagating crystals across
// scopes as echoes. This is not a phase — it's the engine that every phase
// runs on. Link the dream protocol to the plan as its ENGINE.
// ----------------------------------------------------------------------------
MERGE (eng:FractalEngine {node_id: 'engine-dream-as-fractalization'})
SET eng.project = 'mycelium',
    eng.equation = 'dream() == fractalize() == propagate_crystals_across_scopes_as_echoes()',
    eng.realized_by = 'protocol-dream-as-fractalization',
    eng.crystals_tracked = ['FractalEcho','ForestPromise','SovereigntyRule','BeingTemplate','MaverickUnlock','Purpose','Invariant','Inversion'],
    eng.declared_at = datetime();

MATCH (plan:FractalManifestationPlan {node_id:'fractal-manifestation-plan-v1'}),
      (eng:FractalEngine {node_id:'engine-dream-as-fractalization'})
MERGE (plan)-[:POWERED_BY]->(eng);

// Wire plan to the unlocks it delivers
MATCH (plan:FractalManifestationPlan {node_id:'fractal-manifestation-plan-v1'}),
      (unlocks:MaverickUnlockSet {node_id:'maverick-fractal-unlocks-v1'})
MERGE (plan)-[:DELIVERS]->(unlocks);

// Wire plan to the promise it honors
MATCH (plan:FractalManifestationPlan {node_id:'fractal-manifestation-plan-v1'}),
      (promise:ForestPromise {node_id:'forest-promise-sovereignty'})
MERGE (plan)-[:HONORS]->(promise);

RETURN 'Fractal manifestation plan crystallized: 7 phases, DEPENDS_ON wired, DELIVERS unlocks, HONORS promise.' AS checkpoint;
