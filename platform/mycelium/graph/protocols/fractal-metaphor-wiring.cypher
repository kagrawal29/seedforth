// @node_id: protocol-fractal-metaphor-wiring
// @label: "Fractal Metaphor Wiring"
// ============================================================================
// Protocol: Fractal Metaphor Wiring
// ============================================================================
// Wires every biological metaphor to every subsystem and health metric it
// illuminates. The design principle is FRACTAL: every subsystem is a self-similar
// image of the whole. The same lifecycle (birth → growth → measurement →
// decay → renewal) repeats at node, subsystem, and system scales.
//
// This protocol:
// 1. Creates :ILLUMINATES edges from each metaphor to relevant targets
// 2. Adds metaphor_explanation properties to HealthMetrics
// 3. Creates a :DesignPrinciple node for fractal self-similarity
// 4. Wires it to :Ontology and all :Metaphor nodes
//
// Idempotent: uses only MERGE, safe to re-run.
//
// Edge counts after wiring:
//   - metaphor-heartbeat: >= 10 targets
//   - metaphor-immune: >= 10 targets
//   - metaphor-synapse: >= 10 targets
//   - metaphor-dna: >= 10 targets
//   - metaphor-speciation: >= 5 targets
//   - metaphor-cell: >= 10 targets
//   - metaphor-forest-mycelium: >= 10 targets
// ============================================================================

// === metaphor-heartbeat illuminates rhythm, Being, HealthMetrics, and vitals ===

MATCH (m:Metaphor {node_id: 'metaphor-heartbeat'}),
      (rhythm:Rhythm {node_id: 'rhythm-heartbeat'})
MERGE (m)-[:ILLUMINATES]->(rhythm);

MATCH (m:Metaphor {node_id: 'metaphor-heartbeat'}),
      (being:Being {node_id: 'being-mycelium'})
MERGE (m)-[:ILLUMINATES]->(being);

MATCH (m:Metaphor {node_id: 'metaphor-heartbeat'}),
      (hm:HealthMetric)
MERGE (m)-[:ILLUMINATES]->(hm);

MATCH (m:Metaphor {node_id: 'metaphor-heartbeat'}),
      (inv:Invariant)
WHERE inv.node_id CONTAINS 'vital'
MERGE (m)-[:ILLUMINATES]->(inv);

// === metaphor-immune illuminates all Invariants, Protocol-Immune, Questions, and self-heal purpose ===

MATCH (m:Metaphor {node_id: 'metaphor-immune'}),
      (inv:Invariant)
MERGE (m)-[:ILLUMINATES]->(inv);

MATCH (m:Metaphor {node_id: 'metaphor-immune'}),
      (proto:Protocol {node_id: 'protocol-immune'})
MERGE (m)-[:ILLUMINATES]->(proto);

MATCH (m:Metaphor {node_id: 'metaphor-immune'}),
      (q:Question)
MERGE (m)-[:ILLUMINATES]->(q);

MATCH (m:Metaphor {node_id: 'metaphor-immune'}),
      (purpose:Purpose {node_id: 'purpose-self-heal'})
MERGE (m)-[:ILLUMINATES]->(purpose);

MATCH (m:Metaphor {node_id: 'metaphor-immune'}),
      (hm:HealthMetric)
MERGE (m)-[:ILLUMINATES]->(hm);

// === metaphor-synapse illuminates fired atoms, learn-from-use, and prompt-ingest rhythm ===

MATCH (m:Metaphor {node_id: 'metaphor-synapse'}),
      (a:CypherAtom)
WHERE coalesce(a.fire_count, 0) > 0
MERGE (m)-[:ILLUMINATES]->(a);

MATCH (m:Metaphor {node_id: 'metaphor-synapse'}),
      (purpose:Purpose {node_id: 'purpose-learn-from-use'})
MERGE (m)-[:ILLUMINATES]->(purpose);

MATCH (m:Metaphor {node_id: 'metaphor-synapse'}),
      (rhythm:Rhythm {node_id: 'rhythm-prompt-ingest'})
MERGE (m)-[:ILLUMINATES]->(rhythm);

// === metaphor-dna illuminates merkle protocol, all Species, Being, and merkle invariants ===

MATCH (m:Metaphor {node_id: 'metaphor-dna'}),
      (proto:Protocol {node_id: 'protocol-merkle-properties'})
MERGE (m)-[:ILLUMINATES]->(proto);

MATCH (m:Metaphor {node_id: 'metaphor-dna'}),
      (species:Species)
MERGE (m)-[:ILLUMINATES]->(species);

MATCH (m:Metaphor {node_id: 'metaphor-dna'}),
      (being:Being {node_id: 'being-mycelium'})
MERGE (m)-[:ILLUMINATES]->(being);

MATCH (m:Metaphor {node_id: 'metaphor-dna'}),
      (inv:Invariant)
WHERE inv.node_id CONTAINS 'merkle'
MERGE (m)-[:ILLUMINATES]->(inv);

// === metaphor-speciation illuminates all Species, species protocols, and graph-native-authority purpose ===

MATCH (m:Metaphor {node_id: 'metaphor-speciation'}),
      (species:Species)
MERGE (m)-[:ILLUMINATES]->(species);

MATCH (m:Metaphor {node_id: 'metaphor-speciation'}),
      (proto:Protocol)
WHERE proto.node_id CONTAINS 'species'
MERGE (m)-[:ILLUMINATES]->(proto);

MATCH (m:Metaphor {node_id: 'metaphor-speciation'}),
      (purpose:Purpose {node_id: 'purpose-graph-native-authority'})
MERGE (m)-[:ILLUMINATES]->(purpose);

// === metaphor-cell illuminates all Subsystems, Personas, Concepts, and HealthMetrics ===

MATCH (m:Metaphor {node_id: 'metaphor-cell'}),
      (subsys:Subsystem)
MERGE (m)-[:ILLUMINATES]->(subsys);

MATCH (m:Metaphor {node_id: 'metaphor-cell'}),
      (persona:Persona)
MERGE (m)-[:ILLUMINATES]->(persona);

MATCH (m:Metaphor {node_id: 'metaphor-cell'}),
      (concept:Concept)
MERGE (m)-[:ILLUMINATES]->(concept);

MATCH (m:Metaphor {node_id: 'metaphor-cell'}),
      (hm:HealthMetric)
MERGE (m)-[:ILLUMINATES]->(hm);

// === metaphor-forest-mycelium illuminates Ontology, Words, dense-by-design purpose, and Being ===

MATCH (m:Metaphor {node_id: 'metaphor-forest-mycelium'}),
      (ontology:Ontology)
MERGE (m)-[:ILLUMINATES]->(ontology);

MATCH (m:Metaphor {node_id: 'metaphor-forest-mycelium'}),
      (word:Word)
MERGE (m)-[:ILLUMINATES]->(word);

MATCH (m:Metaphor {node_id: 'metaphor-forest-mycelium'}),
      (purpose:Purpose {node_id: 'purpose-dense-by-design'})
MERGE (m)-[:ILLUMINATES]->(purpose);

MATCH (m:Metaphor {node_id: 'metaphor-forest-mycelium'}),
      (being:Being {node_id: 'being-mycelium'})
MERGE (m)-[:ILLUMINATES]->(being);

// === Add metaphor_explanation to selected HealthMetrics ===

MATCH (hm:HealthMetric {node_id: 'hm-atom-liveness'})
SET hm.metaphor_explanation = 'Like neurons that have never fired — present but not yet part of any thought. Low atom-liveness means the execution layer has structure without function. Metaphor: synapse (unused atoms are inactive synapses).';

MATCH (hm:HealthMetric {node_id: 'hm-question-backlog'})
SET hm.metaphor_explanation = 'The immune system asking for help. Questions are the graph sensing anomalies and requesting repair. A growing backlog means the immune system is detecting more problems than the heal_protocols can resolve. Metaphor: immune (detection rate outpacing healing).';

MATCH (hm:HealthMetric {node_id: 'hm-vocabulary-prompt-resolution-rate'})
SET hm.metaphor_explanation = 'The heartbeat of prompt processing. Each prompt fires synapses (execution), and each execution integrates into the vocabulary. Low resolution rate = weak heartbeat. Metaphor: heartbeat (pulse of incoming demand) and synapse (each prompt fires atoms).';

MATCH (hm:HealthMetric {node_id: 'hm-trace-accumulation'})
SET hm.metaphor_explanation = 'DNA accumulating mutations and memories. Each trace is a record of what fired, when, and what changed. High trace accumulation with low decay means the graph is remembering everything — like a genome recording evolutionary history. Metaphor: DNA (immutable record of activity).';

MATCH (hm:HealthMetric {node_id: 'hm-rhythm-tick-rate'})
SET hm.metaphor_explanation = 'The heartbeat itself. Every tick is a pulse of the system checking its own vitals. Low tick rate = missing heartbeat; high tick rate = tachycardia. Metaphor: heartbeat (the rhythm is the pulse).';

MATCH (hm:HealthMetric {node_id: 'hm-embedding-coverage'})
SET hm.metaphor_explanation = 'The forest mycelium nutrient distribution. High coverage means every node can be found via semantic similarity — the underground network reaches everywhere. Low coverage = isolated pockets. Metaphor: forest-mycelium (latent semantic connectivity).';

// === Create the DesignPrinciple node ===

MERGE (dp:DesignPrinciple {
  node_id: 'design-fractal-self-similarity'
})
ON CREATE SET dp.name = 'Fractal Self-Similarity',
              dp.description = 'Every subsystem is a self-similar image of the whole. The same lifecycle (birth, growth, measurement, decay, renewal) repeats at node, subsystem, and system level. The same edge types (HEALED_BY, MONITORED_BY, SERVES, ILLUMINATES) wire every scale. When building anything new, repeat existing patterns — do not invent new ones. The graph density comes from this repetition.',
              dp.file_type = 'principle',
              dp.created_at = toString(datetime());

// === Wire DesignPrinciple to Ontology ===

MATCH (dp:DesignPrinciple {node_id: 'design-fractal-self-similarity'}),
      (ontology:Ontology)
MERGE (dp)-[:PRINCIPLE_OF]->(ontology);

// === Wire DesignPrinciple to every Metaphor ===

MATCH (dp:DesignPrinciple {node_id: 'design-fractal-self-similarity'}),
      (m:Metaphor)
MERGE (dp)-[:EMBODIES]->(m);
