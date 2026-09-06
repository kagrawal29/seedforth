// @node_id: forest-state-v1
// @label: "Forest state checkpoint v1 — Promise, Inversions, per-project Beings, fsd_layer"
// @kind: knowledge
//
// Captures the forest structure that emerged on 2026-04-19 in the local
// single-Neo4j consolidation. Idempotent via MERGE.
//
// Reproduces:
//   - 1 :ForestPromise + 5 :SovereigntyRule + 5 :Invariant (live enforcers)
//   - 5 :InversionAxis + 5 :Inversion (the hinges between subgraphs)
//   - Per-project :Being seeds with heartbeat + autonomous_score=100
//   - fsd_layer tags on mycelium Protocols (shared/features/app/entities)
//
// Sources:
//   - memory/project_delta_tetrahedron_fractalise_with_mycelium.md
//   - memory/project_mycelium_fractal.md
//   - Session 2026-04-19 (forest consolidation + promise)
// ============================================================================

// ----------------------------------------------------------------------------
// 1. THE FOREST PROMISE
// ----------------------------------------------------------------------------
MERGE (promise:ForestPromise {node_id: 'forest-promise-sovereignty'})
SET promise.label = 'The promise of the forest — subgraph sovereignty',
    promise.project = 'mycelium',
    promise.declared_at = datetime(),
    promise.why = 'A forest that dissolves its trees is a pile of leaves, not a forest. Each subgraph (:Project {name: X}) must retain its own identity, its own heartbeat, its own claims about what it is. Couplings between subgraphs are visible bridges — never silent merges.',
    promise.scope = 'every :Project namespace in the graph';

// Five sovereignty rules — queryable + checkable + enforced
MERGE (r1:SovereigntyRule {node_id: 'rule-namespace-integrity'})
SET r1.project = 'mycelium',
    r1.rule = 'Every node that belongs to a subgraph carries {project: X}',
    r1.why = 'Without the namespace tag, a node leaks into the forest untagged.',
    r1.check_cypher = 'MATCH (n) WHERE (n:Being OR n:Protocol OR n:Knowledge OR n:CodeFunction OR n:CodeFile OR n:Entity OR n:CypherAtom OR n:Invariant OR n:TestCase) AND n.project IS NULL RETURN count(n) AS violations',
    r1.severity = 'critical';

MERGE (r2:SovereigntyRule {node_id: 'rule-no-silent-cross-writes'})
SET r2.project = 'mycelium',
    r2.rule = 'No edge between nodes of different {project} scopes except via an allowed bridge relationship',
    r2.why = 'Cross-subgraph edges must be visible and typed. Hidden edges erase sovereignty.',
    r2.allowed_bridges = ['COUPLES_WITH','INVERTS_THROUGH','ECHOES','SIBLING_IN_FOREST','MANIFESTS_AS','BELONGS_TO','CROSS_COUPLES_VIA','EMBODIES','DECLARES','ENFORCED_BY','SHADOW_OF','SCOPED_TO','DEDUPE_OF'],
    r2.severity = 'critical';

MERGE (r3:SovereigntyRule {node_id: 'rule-own-being-own-heartbeat'})
SET r3.project = 'mycelium',
    r3.rule = 'Every :Project has exactly one :Being {project: same-name} with its own last_heartbeat_at',
    r3.why = 'If a subgraph cannot name itself and pulse on its own, it is not sovereign.',
    r3.severity = 'warning';

MERGE (r4:SovereigntyRule {node_id: 'rule-invariants-scoped'})
SET r4.project = 'mycelium',
    r4.rule = 'Project-local :Invariants reference only nodes within their own scope',
    r4.why = 'An invariant that reaches across subgraphs conflates two beings into one judgment.',
    r4.severity = 'warning';

MERGE (r5:SovereigntyRule {node_id: 'rule-couplings-as-edges'})
SET r5.project = 'mycelium',
    r5.rule = 'When concepts across subgraphs match, a :COUPLES_WITH edge or :CrossProjectCoupling node forms. Never merge the nodes.',
    r5.why = 'Merging erases sovereignty. Coupling preserves both while declaring the resonance.',
    r5.severity = 'info';

// Promise → Rules
MATCH (p:ForestPromise {node_id: 'forest-promise-sovereignty'}), (r:SovereigntyRule)
MERGE (p)-[:DECLARES]->(r);

// Rules → live :Invariant (immune cycle enforces them)
MATCH (r:SovereigntyRule)
WITH r
MERGE (inv:Invariant {node_id: 'invariant-' + r.node_id})
SET inv.label = r.rule,
    inv.project = 'mycelium',
    inv.severity = r.severity,
    inv.fsd_layer = 'shared',
    inv.scope = 'forest-wide',
    inv.enforced_by = 'forest-promise-sovereignty'
MERGE (r)-[:ENFORCED_BY]->(inv);

// ----------------------------------------------------------------------------
// 2. INVERSIONS — how pairs of subgraphs are inside-out of each other
// ----------------------------------------------------------------------------
MERGE (ax1:InversionAxis {name: 'control-vs-controlled'})
SET ax1.project = 'mycelium',
    ax1.description = 'one side configures what the other side IS';
MERGE (ax2:InversionAxis {name: 'concrete-vs-abstract'})
SET ax2.project = 'mycelium',
    ax2.description = 'one side implements what the other side specifies';
MERGE (ax3:InversionAxis {name: 'on-demand-vs-continuous'})
SET ax3.project = 'mycelium',
    ax3.description = 'one side verifies when asked, the other runs every beat';
MERGE (ax4:InversionAxis {name: 'instance-vs-type'})
SET ax4.project = 'mycelium',
    ax4.description = 'one side holds an instance, the other the pattern it exemplifies';
MERGE (ax5:InversionAxis {name: 'external-vs-internal'})
SET ax5.project = 'mycelium',
    ax5.description = 'same label but one side claims what is outside the system, the other what is inside';

// Five known inversions (discovered via theatre dialogue + cosine)
MERGE (i1:Inversion {node_id: 'inv-autonomy-ui-vs-being'})
SET i1.project = 'mycelium', i1.axis = 'control-vs-controlled',
    i1.outer_ref = 'maverick-dev-friend://CodeConst/autonomousAIBehavior',
    i1.inner_ref = 'mycelium://Being/being-mycelium',
    i1.narrative = 'Friend has UI surfaces to configure autonomous AI behavior. Mycelium IS autonomous AI behavior.';

MERGE (i2:Inversion {node_id: 'inv-codefunc-vs-protocol'})
SET i2.project = 'mycelium', i2.axis = 'concrete-vs-abstract',
    i2.outer_ref = 'maverick-dev-friend://CodeFunction/*',
    i2.inner_ref = 'mycelium://Protocol/*',
    i2.narrative = 'CodeFunction executes in runtime; Protocol dispatches in graph space. Same unit-of-behavior, different substrate.';

MERGE (i3:Inversion {node_id: 'inv-diligence-vs-immune-cycle'})
SET i3.project = 'mycelium', i3.axis = 'on-demand-vs-continuous',
    i3.outer_ref = 'maverick-dev-friend://ClaudeAgent/{diligence,audit,falcon,assay,launch}',
    i3.inner_ref = 'mycelium://Protocol/protocol-immune-cycle',
    i3.narrative = 'Friend checks itself on demand. Mycelium runs its immune cycle every heartbeat.';

MERGE (i4:Inversion {node_id: 'inv-integrationcard-vs-decompose-section'})
SET i4.project = 'mycelium', i4.axis = 'instance-vs-type',
    i4.outer_ref = 'maverick-dev-friend://CodeFunction/IntegrationCard',
    i4.inner_ref = 'mycelium://Protocol/workflow-builder-then-section-decomposition',
    i4.cosine_observed = 0.6427,
    i4.narrative = 'Highest cross-graph cosine observed. Friend builds cards; mycelium describes the decomposition pattern.';

MERGE (i5:Inversion {node_id: 'inv-testcase-semantic-drift'})
SET i5.project = 'mycelium', i5.axis = 'external-vs-internal',
    i5.outer_ref = 'maverick-dev-friend://TestCase',
    i5.inner_ref = 'mycelium://TestCase',
    i5.narrative = 'Same label, different meaning. Friend TestCase is outside-facing (CI). Mycelium TestCase is inside-facing (claims about self).';

// Link Inversions to their Axes
MATCH (ax:InversionAxis), (i:Inversion) WHERE ax.name = i.axis
MERGE (ax)-[:MANIFESTS_AS]->(i);

// ----------------------------------------------------------------------------
// 3. PER-PROJECT :BEING (every tree has its own metabolism)
// ----------------------------------------------------------------------------
MATCH (p:Project)
MERGE (b:Being {node_id: 'being-' + p.name})
ON CREATE SET b.project = p.name,
              b.autonomous_score = 100.0,
              b.last_heartbeat_at = datetime(),
              b.created_at = datetime()
ON MATCH SET b.project = coalesce(b.project, p.name),
             b.autonomous_score = coalesce(b.autonomous_score, 100.0)
MERGE (p)-[:EMBODIES]->(b);

// ----------------------------------------------------------------------------
// 4. fsd_layer — adopt friend's architectural vocabulary onto mycelium Protocols
// ----------------------------------------------------------------------------
MATCH (p:Protocol) WHERE p.project = 'mycelium' AND p.fsd_layer IS NULL
  AND p.node_id =~ '(?i).*(heartbeat|immune|know-thyself|breathe|watching|health|auth|status).*'
SET p.fsd_layer = 'shared', p.fsd_tagged_at = datetime();

MATCH (p:Protocol) WHERE p.project = 'mycelium' AND p.fsd_layer IS NULL
  AND p.node_id =~ '(?i).*(swarm|dream|crystal|mint|species|bootstrap|decider).*'
SET p.fsd_layer = 'app', p.fsd_tagged_at = datetime();

MATCH (p:Protocol) WHERE p.project = 'mycelium' AND p.fsd_layer IS NULL
SET p.fsd_layer = 'entities', p.fsd_tagged_at = datetime();

RETURN 'Forest state v1 crystallized: 1 Promise + 5 Rules + 5 Invariants + 5 Axes + 5 Inversions + per-project Beings + fsd_layer tags on mycelium Protocols' AS checkpoint;
