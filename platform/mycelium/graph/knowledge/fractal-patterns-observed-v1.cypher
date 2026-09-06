// @node_id: fractal-patterns-observed-v1
// @label: "Fractal patterns observed across 15 forest-panel sessions (2026-04-19)"
// @kind: knowledge
//
// Empirical patterns that recurred across 15 forest-panel sessions, derived
// from the HEARD_FROM + FIRED_WITH signal corpus. Each is a crystal candidate:
// the weaver should materialize :FractalEcho nodes from these after ingest +
// fire_count promotion.
// ============================================================================

MERGE (set:FractalPatternSet {node_id: 'fractal-patterns-observed-v1'})
SET set.project = 'mycelium',
    set.session = 'session-2026-04-19-forest-panel',
    set.declared_at = datetime();

UNWIND [
  {n: 1, id: 'voice-is-the-fractal-floor',
   title: 'Voice is the fractal floor',
   evidence: 'A7_voice/AI_Agents.md surfaced in 7 of 15 panels regardless of topic',
   meaning: 'How the product SOUNDS is invariant under what the product DOES. Voice is the universal substrate — every question about the product eventually reaches for it.',
   scales: ['marketing','friend','vc-ai-associate'],
   echo_seed: 'product-voice-invariance'},
  {n: 2, id: 'classifiers-are-immune-cycles',
   title: 'Classifiers ARE immune cycles, translated',
   evidence: 'maverick-marketing _a4_classify_heuristic.py + _a6_competitor_audit + _a2_analyze.py recurred 4-6 times each, always co-firing with mycelium invariant/gap nodes',
   meaning: 'Marketing\'s classifier scripts play the exact structural role that mycelium\'s :Invariant + :Gap + immune-cycle plays in the substrate: decide what this thing is and where it goes. Same function, different expression across scopes. Live :FractalEcho candidate.',
   scales: ['marketing','mycelium'],
   echo_seed: 'classifier-as-immune-cycle'},
  {n: 3, id: 'migrations-are-the-spine',
   title: 'Migrations are the schema spine',
   evidence: 'V0008 ingestion_rules, V0019 orphan_test, V0020 process_invariants_check_hooks, V0022 task_types, V0028 git_provenance, V0032 decision_far — each recurred 3-4 panels',
   meaning: 'Every serious question eventually asks "what\'s the schema?" and the migrations answer. maverick-dev as platform spine IS the persistent promise of shape across the forest.',
   scales: ['maverick-dev','mycelium'],
   echo_seed: 'schema-as-promise'},
  {n: 4, id: 'graph-queries-itself-recursively',
   title: 'The graph keeps returning its own introspection tools',
   evidence: 'graph-query/SKILL.md (5 panels), parse_skill_anti_patterns.py (4), dogfood_graph.py (3), graph-context.sh',
   meaning: 'Ask anything, the forest answers by offering ways to ask it. Self-referential by construction.',
   scales: ['maverick-dev','vc-ai-associate','mycelium'],
   echo_seed: 'recursive-introspection'},
  {n: 5, id: 'void-has-a-shape',
   title: 'The void has a shape — silence maps sovereignty',
   evidence: 'mycelium silent on product-deal questions. vc-ai-associate silent on fund operations. maverick-marketing silent on fractal zoom. The silences are consistent and domain-coherent.',
   meaning: 'Each scope has a shape of what it CANNOT answer. That silhouette IS the Being\'s sovereignty made visible. Silence is signal.',
   scales: ['all-6-scopes'],
   echo_seed: 'sovereignty-by-silence'},
  {n: 6, id: 'round2-only-strengthens-where-real',
   title: 'Hebbian round-2 only fires where real signal exists',
   evidence: 'Round 2 resonance jumped 0.05-0.10 for Beings whose subgraph carried the topic, stayed flat or silent for those that didn\'t, in every single panel',
   meaning: 'The mechanism doesn\'t generate false positives. Cross-subgraph echo only amplifies where genuine semantic resonance already exists. Makes Hebbian promotion a trustworthy gate.',
   scales: ['meta-mechanism'],
   echo_seed: 'hebbian-zero-false-positive'}
] AS p
MERGE (pat:FractalPattern {node_id: 'pattern-' + p.id})
SET pat.project = 'mycelium',
    pat.order = p.n,
    pat.title = p.title,
    pat.evidence = p.evidence,
    pat.meaning = p.meaning,
    pat.scales = p.scales,
    pat.echo_seed = p.echo_seed,
    pat.status = 'observed',
    pat.observed_at = datetime();

// Wire patterns to the set (self-contained MATCH)
MATCH (set:FractalPatternSet {node_id: 'fractal-patterns-observed-v1'}),
      (pat:FractalPattern)
WHERE pat.node_id STARTS WITH 'pattern-'
MERGE (set)-[:CONTAINS]->(pat);

// Link the pattern set to the session that produced it
MATCH (set:FractalPatternSet {node_id: 'fractal-patterns-observed-v1'}),
      (s:SessionReflection {node_id: 'session-2026-04-19-forest-panel'})
MERGE (s)-[:SURFACED]->(set);

// Link to the plan so Phase 4 (weave-echoes) can pick these up as seeds
MATCH (set:FractalPatternSet {node_id: 'fractal-patterns-observed-v1'}),
      (plan:FractalManifestationPlan {node_id: 'fractal-manifestation-plan-v1'})
MERGE (plan)-[:SEEDED_BY]->(set);

RETURN 'Six :FractalPattern nodes crystallized — ready for the weaver to materialize as :FractalEcho on Phase 4 fire.' AS checkpoint;
