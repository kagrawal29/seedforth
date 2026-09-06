// @kind: seed
// Seed Capability and Decision Rule nodes so the graph knows about its own infrastructure
// Phase 2 of self-knowledge seeding

// Capability: ask - semantic vector search over graph nodes
MERGE (c1:Capability:Guide {node_id: 'capability-ask'})
SET c1.name = 'ask',
    c1.command = './mycelium ask "question"',
    c1.what = 'Semantic vector search over all graph nodes. Deposits Prompt, Word, Bigram nodes. Creates RESOLVED_TO and TRAVERSED edges.',
    c1.when_to_use = 'When you need to find existing knowledge. When you want to teach the graph new vocabulary. When exploring what the graph knows about a topic.',
    c1.cost = 'One embedding call per novel question. Zero cost for cache hits (cosine > 0.95).',
    c1.learns = 'Deposits Words, Bigrams, Prompts. Strengthens INFERRED_SIMILAR edges. Creates INVOKES edges that increment fire_count.',
    c1.health_signal = 'cache_hit_rate, vocabulary_growth_rate, cosine_distribution';

// Capability: swarm - parallel Cypher workers dispatched by semantic match
MERGE (c2:Capability:Guide {node_id: 'capability-swarm'})
SET c2.name = 'swarm',
    c2.command = './mycelium swarm --from-prompt "task"',
    c2.what = 'Parallel Cypher workers dispatched by semantic match. Creates Swarm, SwarmWorker, SwarmState nodes. Can spawn sub-swarms at depth > 1.',
    c2.when_to_use = 'When you need graph-native computation at zero LLM cost. For bulk operations, health sweeps, gap detection, protocol execution. Preferred over ask for work the graph can do itself.',
    c2.cost = 'One embedding call to dispatch. Zero LLM tokens for worker execution.',
    c2.learns = 'Creates Swarm topology. Findings recorded in SwarmState. Sub-swarms compound into deeper investigation.',
    c2.health_signal = 'worker_completion_rate, dispatch_accuracy, depth_utilization';

// Capability: agent - autonomous sense-decide-act-observe loop
MERGE (c3:Capability:Guide {node_id: 'capability-agent'})
SET c3.name = 'agent',
    c3.command = './mycelium agent "goal"',
    c3.what = 'Autonomous sense-decide-act-observe loop. Iterates until goal is met or max iterations reached. Creates Activation nodes tracking each iteration.',
    c3.when_to_use = 'When you need autonomous goal-directed behavior. For complex tasks requiring multiple steps, observation, and adaptation. The highest autonomy mode.',
    c3.cost = 'Multiple embedding calls per iteration. Zero LLM tokens.',
    c3.learns = 'Creates Activation nodes. Tracks iteration count. Measures goal achievement.',
    c3.health_signal = 'iteration_count, goal_achievement_rate, action_diversity';

// Capability: heartbeat - automatic 30-minute maintenance cycle
MERGE (c4:Capability:Guide {node_id: 'capability-heartbeat'})
SET c4.name = 'heartbeat',
    c4.command = './mycelium heartbeat or scripts/heartbeat.py',
    c4.what = 'Scheduled 30-minute cycle executing 16 phases: liveness, decay, gap detection, healing, dream round, embedding refresh, amortization recount, test execution, reporting.',
    c4.when_to_use = 'Runs automatically on schedule. Should never be bypassed. Is the primary mechanism for graph self-maintenance.',
    c4.cost = 'Zero LLM tokens. Pure Cypher execution.',
    c4.learns = 'Updates health scores, fires protocols, detects gaps, heals auto-fixable issues, decays stale edges, recomputes amortization.',
    c4.health_signal = 'heartbeat_count, health_score, protocol_fire_distribution';

// Capability: healing - immune system for gap detection and repair
MERGE (c5:Capability:Guide {node_id: 'capability-healing'})
SET c5.name = 'healing',
    c5.command = 'Triggered by heartbeat via THEN chain: detect-gaps → healing → audit',
    c5.what = 'Immune system. Detects gaps, classifies auto-fixability, executes healing Cypher, audits results. Creates Gap nodes with CONCERNS edges.',
    c5.when_to_use = 'Activated automatically when invariants fail or gaps are detected. Manual trigger via swarm for urgent healing.',
    c5.cost = 'Zero LLM tokens. Graph topology drives all healing decisions.',
    c5.learns = 'Creates Gap nodes. Classifies auto_fixable. Tracks resolution. Strengthens THEN chain through repeated execution.',
    c5.health_signal = 'gaps_open, gaps_resolved, invariant_health_ratio, heal_protocol_fire_count';

// Decision rule: when to use swarm vs ask vs agent
MERGE (d1:DecisionRule:Guide {node_id: 'decision-swarm-vs-ask'})
SET d1.rule = 'Use swarm for work the graph can do natively (health sweeps, gap detection, protocol execution, bulk operations). Use ask for exploration, vocabulary teaching, discovering what the graph knows. Use agent for autonomous multi-step goals.',
    d1.priority_order = 'swarm (zero cost, graph-native) > ask (one embedding, teaches vocabulary) > agent (multiple embeddings, autonomous)',
    d1.anti_pattern = 'Never use shell for work that swarm or ask can do. Shell bypasses all learning mechanisms.';

// Decision rule: when to use heartbeat vs manual healing
MERGE (d2:DecisionRule:Guide {node_id: 'decision-heartbeat-vs-manual'})
SET d2.rule = 'Heartbeat is the default maintenance loop. Only trigger manual healing via swarm when there is an active blocking issue that cannot wait for the next heartbeat cycle (30 minutes).',
    d2.priority_order = 'heartbeat (scheduled, comprehensive) > manual swarm healing (emergency only)';

// Link capabilities to the Being (mycelium graph itself)
MERGE (b:Being {node_id: 'being-mycelium'})
MERGE (c1)-[:CAPABILITY_OF]->(b)
MERGE (c2)-[:CAPABILITY_OF]->(b)
MERGE (c3)-[:CAPABILITY_OF]->(b)
MERGE (c4)-[:CAPABILITY_OF]->(b)
MERGE (c5)-[:CAPABILITY_OF]->(b)
MERGE (d1)-[:GOVERNS]->(b)
MERGE (d2)-[:GOVERNS]->(b)

RETURN
  5 as capabilities_created,
  2 as decision_rules_created,
  'Infrastructure knowledge nodes seeded successfully' as status
