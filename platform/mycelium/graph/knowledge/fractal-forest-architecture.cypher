// @node_id: vision-fractal-forest
// @label: "Fractal Forest — Mycelium's next evolution: one graph, many sovereign subgraphs"
// @kind: vision
//
// This file crystallizes Slice H — how Mycelium becomes a forest of subgraphs
// that are the same graph. Self-similar at every scale. One property scope
// ({project: X}), one emergent edge type ([:CROSS_COUPLING]), no forked code.
//
// Sources:
//   - memory/project_delta_tetrahedron_fractalise_with_mycelium.md
//   - memory/project_mycelium_fractal.md
//   - memory/project_mycelium_dreaming_as_fractalisation.md
//   - Session 2026-04-18 (team ship + Slice H roadmap)
//
// Graph-native so every mycelium session can query: `mycelium ask "what is
// the fractal vision" → vision-fractal-forest + its related evolution phases.
// ============================================================================

// 1. Root vision node
MERGE (v:Vision {node_id: 'vision-fractal-forest'})
SET v.label = 'Fractal Forest — Mycelium as a forest of sovereign subgraphs',
    v.description = 'Mycelium evolves from a single graph into a forest of :Project-scoped subgraphs that share identical topology. Every team, agent, project, or environment becomes a subgraph with its own :Being, :Protocol, :Invariant, :TestCase, :Knowledge, :Species — the same organs mycelium core has, replicated under a {project: X} scope. Cross-couplings emerge as a third-class edge type when dream round finds embedding similarity across subgraph boundaries. Nothing merges; sovereignty preserved; couplings are bridges, not absorptions.',
    v.why_it_matters = 'Today mycelium knows only what mycelium sees. After Slice H it knows what ember sees, what arie sees, what tetrahedron sees — and where their knowledge converges or diverges. That cross-subgraph visibility is what makes it a team nervous system instead of a personal database.',
    v.status = 'designed — not yet implemented',
    v.triggered_after = 'first real Qubit Capital teammate onboards and commits via maverick',
    v.updated_at = datetime();

// 2. Fractal invariant — the single rule
MERGE (i:FractalInvariant {node_id: 'fractal-invariant-scale-free'})
SET i.label = 'Scale-free operation rule',
    i.rule = 'For any operation op that works on mycelium core, op works identically on any subgraph by scoping {project: X}. Nothing special-cased per subgraph.',
    i.consequence = 'No forked code paths per project. Same protocol file drives core and every subgraph. The fractal is one property scope, not parallel implementations.',
    i.violation_example = 'Writing ember-specific heartbeat logic instead of reusing heartbeat-core with {project: ember} scope — that is a fractal break.',
    i.updated_at = datetime();

MERGE (v:Vision {node_id: 'vision-fractal-forest'})-[:GOVERNED_BY]->(i);

// 3. Topology metaphor — biology ↔ graph term mapping
MERGE (t:TopologyMap {node_id: 'topology-biology-to-graph'})
SET t.label = 'Biology ↔ Graph metaphor map',
    t.mappings = '
Forest → :Project {name: X}
Tree → :Being {project: X, autonomous_score}
Mycelial strand → :Protocol {project: X, node_id}
Hypha → :CypherAtom {project: X, node_id}
Leaf → :Knowledge {project: X, node_id}
Immune cell → :Invariant {project: X, number}
Proprioceptor → :TestCase {project: X, claim}
Hyphal bridge → [:CROSS_COUPLING] edge (spans projects)
Fruiting body → :Species {project: X, dna}
',
    t.note = 'Every organ mycelium core has, every subgraph has. Fractal = one organ set, repeated at every scale, connected by bridges.',
    t.updated_at = datetime();

MERGE (v:Vision {node_id: 'vision-fractal-forest'})-[:USES_METAPHOR]->(t);

// 4. Six evolution phases — each an :EvolutionPhase node
MERGE (p0:EvolutionPhase {node_id: 'phase-0-foundation'})
SET p0.label = 'Phase 0: :Project namespace foundation',
    p0.ordinal = 0,
    p0.description = 'Define :Project node schema and {project: X} property scope convention. Seed mycelium core as the first :Project {name: mycelium}. Establish the namespace rule: every node that belongs to a subgraph carries {project: X}.',
    p0.deliverable = 'graph/knowledge/project-namespace.cypher + bootstrap sweeps project property into existing nodes.',
    p0.updated_at = datetime();

MERGE (p1:EvolutionPhase {node_id: 'phase-1-webhook-pipeline'})
SET p1.label = 'Phase 1: Ingestion pipeline per repo',
    p1.ordinal = 1,
    p1.description = 'mycelium-ingest service on pulse. GitHub webhook per tracked repo → normalize payload → MERGE Commit/PR/Issue/ReviewComment nodes under correct :Project namespace. Continuous ingestion.',
    p1.deliverable = 'services/mycelium-ingest/ + webhook config per tracked repo.',
    p1.updated_at = datetime();

MERGE (p2:EvolutionPhase {node_id: 'phase-2-code-coupling'})
SET p2.label = 'Phase 2: Code as graph',
    p2.ordinal = 2,
    p2.description = 'mycelium ingest <repo-url> does initial git history + code AST ingest → :CodeUnit + [:CALLS] + [:IMPORTS] edges under {project: X}. Each file, function, class becomes a node.',
    p2.deliverable = 'scripts/ingest-code.py + :CodeUnit schema.',
    p2.updated_at = datetime();

MERGE (p3:EvolutionPhase {node_id: 'phase-3-per-project-being'})
SET p3.label = 'Phase 3: Project-local Being + Invariants',
    p3.ordinal = 3,
    p3.description = 'Each :Project gets a :Being {project: X} with its own autonomous_score and heartbeat. Project-local invariants scoped with {project: X}. Health is sovereign — mycelium core does not dictate what healthy-ember means.',
    p3.deliverable = 'graph/invariants/<project>-*.cypher per project + scoped heartbeat dispatch.',
    p3.updated_at = datetime();

MERGE (p4:EvolutionPhase {node_id: 'phase-4-cross-coupling-dream'})
SET p4.label = 'Phase 4: Cross-subgraph dream round',
    p4.ordinal = 4,
    p4.description = 'Extend dream round to detect (a)-[COUPLING]->(b) where a.project <> b.project and embedding similarity > 0.85. Surface as :CrossProjectCoupling nodes. Both endpoints stay sovereign; coupling is metadata about the bridge.',
    p4.deliverable = 'graph/protocols/dream-cross-project.cypher + :CrossProjectCoupling schema.',
    p4.updated_at = datetime();

MERGE (p5:EvolutionPhase {node_id: 'phase-5-team-dashboard'})
SET p5.label = 'Phase 5: Observatory for the forest',
    p5.ordinal = 5,
    p5.description = 'Observatory dashboard shows every :Project subgraph — its :Being health, its active protocols, its cross-couplings to other subgraphs. Click a subgraph to drill into its local topology. Forest-level and tree-level views.',
    p5.deliverable = 'observatory/ui/forest-view + per-subgraph drill-down.',
    p5.updated_at = datetime();

MERGE (p6:EvolutionPhase {node_id: 'phase-6-graph-native-pr-review'})
SET p6.label = 'Phase 6: Graph-native PR review bot',
    p6.ordinal = 6,
    p6.description = 'PRs in any tracked project get a bot comment citing: this touches concept X which has Y prior decisions across Z projects. Uses :CrossProjectCoupling to surface relevance. Review becomes graph-informed.',
    p6.deliverable = 'github-app/mycelium-reviewer + webhook on pull_request event.',
    p6.updated_at = datetime();

// Link phases in sequence
MATCH (a:EvolutionPhase {ordinal: 0}), (b:EvolutionPhase {ordinal: 1}) MERGE (a)-[:NEXT_PHASE]->(b);
MATCH (a:EvolutionPhase {ordinal: 1}), (b:EvolutionPhase {ordinal: 2}) MERGE (a)-[:NEXT_PHASE]->(b);
MATCH (a:EvolutionPhase {ordinal: 2}), (b:EvolutionPhase {ordinal: 3}) MERGE (a)-[:NEXT_PHASE]->(b);
MATCH (a:EvolutionPhase {ordinal: 3}), (b:EvolutionPhase {ordinal: 4}) MERGE (a)-[:NEXT_PHASE]->(b);
MATCH (a:EvolutionPhase {ordinal: 4}), (b:EvolutionPhase {ordinal: 5}) MERGE (a)-[:NEXT_PHASE]->(b);
MATCH (a:EvolutionPhase {ordinal: 5}), (b:EvolutionPhase {ordinal: 6}) MERGE (a)-[:NEXT_PHASE]->(b);

// Link all phases to the vision
MATCH (v:Vision {node_id: 'vision-fractal-forest'}), (p:EvolutionPhase)
MERGE (v)-[:HAS_PHASE]->(p);

// 5. Candidate first subgraphs (things ready to become :Projects)
MERGE (c1:CandidateProject {node_id: 'candidate-tetrahedron'})
SET c1.name = 'tetrahedron',
    c1.description = 'Personal OS + Discord orchestrator. Memory in YAML; project channels with briefs. Ready to become :Project {name: tetrahedron}.',
    c1.readiness = 'high — flat files ready to ingest as :Knowledge under scope.',
    c1.repo = 'kagrawal29/tetrahedron';

MERGE (c2:CandidateProject {node_id: 'candidate-delta'})
SET c2.name = 'delta',
    c2.description = 'Discord agent platform. Per-project channels with isolated agents. Registry in JSON. Conversations as JSONL. Ready to ingest as :DeltaProject + :ConversationTurn.',
    c2.readiness = 'high — needs delta-server up first.',
    c2.repo = 'kagrawal29/delta';

MERGE (c3:CandidateProject {node_id: 'candidate-ember'})
SET c3.name = 'ember',
    c3.description = 'Multi-tenant LinkedIn management. Scaled from arie prototype.',
    c3.readiness = 'medium — active development; defer until maverick pattern is proven.',
    c3.repo = 'kagrawal29/ember';

MERGE (c4:CandidateProject {node_id: 'candidate-arie'})
SET c4.name = 'arie',
    c4.description = 'Single-user LinkedIn intelligence agent prototype. Precedes ember.',
    c4.readiness = 'medium — useful as simpler first ingestion pilot.',
    c4.repo = 'kagrawal29/arie';

MATCH (v:Vision {node_id: 'vision-fractal-forest'}), (c:CandidateProject)
MERGE (v)-[:WILL_ADOPT]->(c);

// 6. Sovereignty rules (invariants the forest respects)
MERGE (r1:ForestRule {node_id: 'rule-no-cross-writes'})
SET r1.label = 'No project-to-project writes',
    r1.rule = 'A subgraph can READ mycelium core + other subgraphs but cannot MUTATE them. Writes go through source-of-truth repo PRs. Cross-reading is free; cross-mutation is never direct.';

MERGE (r2:ForestRule {node_id: 'rule-own-heartbeat'})
SET r2.label = 'Every :Being has its own heartbeat',
    r2.rule = 'Tetrahedron heartbeat is not mycelium core heartbeat. They tick independently. Each subgraph runs its own scheduled protocols on its own :Being.';

MERGE (r3:ForestRule {node_id: 'rule-couplings-are-edges'})
SET r3.label = 'Couplings are edges, not merges',
    r3.rule = 'When concepts across subgraphs match (via embedding similarity), a [:CROSS_COUPLING] edge forms with a :CrossProjectCoupling metadata node. Both endpoints remain distinct. No silent consolidation.';

MERGE (r4:ForestRule {node_id: 'rule-namespace-via-property'})
SET r4.label = 'Namespace via {project} property, not separate DBs',
    r4.rule = 'Neo4j Community supports one database. Subgraphs are scoped via {project: X} property on every node. Query discipline: always include {project: X} in MATCH when operating on a subgraph.';

MATCH (v:Vision {node_id: 'vision-fractal-forest'}), (r:ForestRule)
MERGE (v)-[:RESPECTS]->(r);

// 7. Trigger condition
MERGE (trigger:TriggerCondition {node_id: 'trigger-slice-h-start'})
SET trigger.label = 'When to begin Slice H',
    trigger.condition = 'Slice G (branch-aware graph pipeline) ships AND first Qubit Capital teammate has onboarded and committed a PR to maverick. Real team signal validates the maverick pattern before replicating it.',
    trigger.rationale = 'Starting Slice H before real signal means authoring :FailureMode + :OnboardingStep nodes speculatively. Starting after means we ingest lived experience.';

MERGE (v:Vision {node_id: 'vision-fractal-forest'})-[:TRIGGERED_BY]->(trigger);

RETURN 'Fractal forest vision crystallized: 1 Vision + 1 FractalInvariant + 1 TopologyMap + 7 EvolutionPhases + 4 CandidateProjects + 4 ForestRules + 1 TriggerCondition = 18 new graph nodes' AS result;
