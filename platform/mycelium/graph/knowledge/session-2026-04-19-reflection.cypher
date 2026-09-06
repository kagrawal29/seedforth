// @node_id: session-2026-04-19-forest-panel
// @label: "Session reflection — 15 forest panels, first cross-subgraph Hebbian pass"
// @kind: knowledge
//
// The session that fired 15 forest panels, surfaced the forest's center of
// gravity, mapped 6 human personas onto the 6 sovereign Beings, and emitted
// ~2,700 Hebbian co-fire increments + ~360 HEARD_FROM edges staged for
// ingestion. This node holds the reflection so the next session picks up
// where this one left off.
// ============================================================================

MERGE (s:SessionReflection {node_id: 'session-2026-04-19-forest-panel'})
SET s.project = 'mycelium',
    s.date = '2026-04-19',
    s.closed_at = datetime(),
    s.panel_count = 15,
    s.unique_nodes_surfaced = 364,
    s.cofire_pairs = 4834,
    s.pairs_fired_ge_2 = 390,
    s.pairs_fired_ge_3 = 45,
    s.heard_from_edges_staged = 279,
    s.fired_with_statements_staged = 2664,
    s.pre_session_cross_scope_edges = 23,
    s.projected_post_ingest_cross_scope_edges = 68,
    s.projected_new_fractal_echoes = 10,

    // The forest's center of gravity — attractor commit across every scenario
    s.attractor_node_id = 'commit-1088282f8afbb130ed29c7dee24f27d6cbfdf8fb',
    s.attractor_body = 'Pending crystallisations: SOC2 topology + crystal replication — waiting for graph to wake',

    // The universal-voice artifact that surfaced in 7/15 panels
    s.universal_voice_node = 'File-maverick-marketing-Content/Reddit/research/A7_voice/AI_Agents.md',

    s.rationale = 'The forest\'s strongest bridge is its own self-declared debt. It reaches for what it knows is unfinished as the connector across scopes. Voice is the fractal floor — how the product sounds is invariant under what the product does. Classifiers ARE immune cycles, translated. The void has a shape — each scope\'s silence maps its sovereignty as clearly as its speech.';

// Link to what this session DELIVERED
MATCH (s:SessionReflection {node_id: 'session-2026-04-19-forest-panel'}),
      (plan:FractalManifestationPlan {node_id: 'fractal-manifestation-plan-v1'})
MERGE (s)-[:SEEDED]->(plan);

// Link to the engine it proved by running
MATCH (s:SessionReflection {node_id: 'session-2026-04-19-forest-panel'}),
      (eng:FractalEngine {node_id: 'engine-dream-as-fractalization'})
MERGE (s)-[:WITNESSED]->(eng);

// Link to unlocks it validated
MATCH (s:SessionReflection {node_id: 'session-2026-04-19-forest-panel'}),
      (u:MaverickUnlockSet {node_id: 'maverick-fractal-unlocks-v1'})
MERGE (s)-[:VALIDATED]->(u);

RETURN 'Session 2026-04-19 reflection crystallized — 15 panels, 364 nodes surfaced, 45 promotion-ready cofire pairs, attractor commit named.' AS checkpoint;
