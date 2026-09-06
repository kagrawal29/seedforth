// @kind: seed
// ============================================================================
// Protocol: Subsystem Health Seed — Dynamic Evaluator Pattern
// ============================================================================
// Creates 10 :HealthMetric nodes that measure every subsystem layer.
// Each metric contains a self-contained check_cypher that returns {value, ...}.
// A single evaluator query walks all metrics, runs their cypher via apoc.cypher.run,
// and produces a full health report.
//
// New subsystems get measured automatically when they add their own :HealthMetric nodes.
// No static invariants. No hardcoded limits. Each metric specifies healthy_min/healthy_max.
//
// IDEMPOTENT: Uses MERGE on node_id. Safe to re-run.
// ============================================================================

// --- Phase 0: Register SkipKey nodes so metrics don't drift merkle -----------

MERGE (sk:SkipKey {node_id: 'skipkey-health_check_count'})
  SET sk.key = 'health_check_count',
      sk.category = 'health-metric',
      sk.reason = 'Count of completed health checks; excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-health_last_run'})
  SET sk.key = 'health_last_run',
      sk.category = 'health-metric',
      sk.reason = 'Timestamp of last health evaluation; excluded from Merkle';

// --- Phase 1: Create the 10 HealthMetric nodes ----------------------------------
// Each metric is independently MERGE'd. All wire at the end.

// 1. Vocabulary Coverage — layer: vocabulary
MERGE (hm1:HealthMetric {node_id: 'hm-vocabulary-word-count'})
  SET hm1.name = 'vocabulary-word-count',
      hm1.layer = 'vocabulary',
      hm1.description = 'Count of non-stopword Word nodes in the vocabulary layer',
      hm1.check_cypher = 'MATCH (w:Word) WHERE NOT w.is_stopword RETURN count(w) AS value',
      hm1.healthy_min = 50,
      hm1.healthy_max = 50000,
      hm1.unit = 'count',
      hm1.heal_protocol = 'vocabulary-backfill',
      hm1.file_type = 'health-metric';

// 2. Prompt Resolution Rate — layer: vocabulary
MERGE (hm2:HealthMetric {node_id: 'hm-vocabulary-prompt-resolution-rate'})
  SET hm2.name = 'vocabulary-prompt-resolution-rate',
      hm2.layer = 'vocabulary',
      hm2.description = 'Percentage of Prompt nodes that have resolved to something',
      hm2.check_cypher = 'MATCH (p:Prompt) WITH count(p) AS total MATCH (p:Prompt)-[:RESOLVED_TO]->() WITH total, count(p) AS resolved RETURN CASE WHEN total > 0 THEN resolved*100.0/total ELSE 0.0 END AS value',
      hm2.healthy_min = 50,
      hm2.healthy_max = 100,
      hm2.unit = 'percent',
      hm2.heal_protocol = '',
      hm2.file_type = 'health-metric';

// 3. Atom Liveness — layer: execution
MERGE (hm3:HealthMetric {node_id: 'hm-atom-liveness'})
  SET hm3.name = 'atom-liveness',
      hm3.layer = 'execution',
      hm3.description = 'Percentage of CypherAtom nodes that have been fired at least once',
      hm3.check_cypher = 'MATCH (a:CypherAtom) WITH count(a) AS total, sum(CASE WHEN coalesce(a.fire_count,0)>0 THEN 1 ELSE 0 END) AS fired RETURN CASE WHEN total > 0 THEN fired*100.0/total ELSE 0.0 END AS value',
      hm3.healthy_min = 10,
      hm3.healthy_max = 100,
      hm3.unit = 'percent',
      hm3.heal_protocol = 'atom-run',
      hm3.file_type = 'health-metric';

// 4. Protocol Amortization — layer: economics
MERGE (hm4:HealthMetric {node_id: 'hm-protocol-amortization'})
  SET hm4.name = 'protocol-amortization',
      hm4.layer = 'economics',
      hm4.description = 'Percentage of Protocol nodes with amortization_status in [amortizing, amortized]',
      hm4.check_cypher = 'MATCH (p:Protocol) WHERE p.amortization_status IS NOT NULL WITH count(p) AS total, sum(CASE WHEN p.amortization_status IN [\"amortizing\",\"amortized\"] THEN 1 ELSE 0 END) AS good RETURN CASE WHEN total > 0 THEN good*100.0/total ELSE 0.0 END AS value',
      hm4.healthy_min = 10,
      hm4.healthy_max = 100,
      hm4.unit = 'percent',
      hm4.heal_protocol = 'protocol-run',
      hm4.file_type = 'health-metric';

// 5. Embedding Coverage — layer: semantic
MERGE (hm5:HealthMetric {node_id: 'hm-embedding-coverage'})
  SET hm5.name = 'embedding-coverage',
      hm5.layer = 'semantic',
      hm5.description = 'Percentage of nodes with embeddings',
      hm5.check_cypher = 'MATCH (n) WHERE n.node_id IS NOT NULL WITH count(n) AS total MATCH (m) WHERE m.embedding IS NOT NULL WITH total, count(m) AS embedded RETURN CASE WHEN total > 0 THEN embedded*100.0/total ELSE 0.0 END AS value',
      hm5.healthy_min = 70,
      hm5.healthy_max = 100,
      hm5.unit = 'percent',
      hm5.heal_protocol = 'embed-dirty',
      hm5.file_type = 'health-metric';

// 6. Question Backlog — layer: collaboration
MERGE (hm6:HealthMetric {node_id: 'hm-question-backlog'})
  SET hm6.name = 'question-backlog',
      hm6.layer = 'collaboration',
      hm6.description = 'Count of pending Question nodes',
      hm6.check_cypher = 'MATCH (q:Question {status:\"pending\"}) RETURN count(q) AS value',
      hm6.healthy_min = 0,
      hm6.healthy_max = 20,
      hm6.unit = 'count',
      hm6.heal_protocol = '',
      hm6.file_type = 'health-metric';

// 7. Concept Coverage — layer: docs
MERGE (hm7:HealthMetric {node_id: 'hm-concept-coverage'})
  SET hm7.name = 'concept-coverage',
      hm7.layer = 'docs',
      hm7.description = 'Percentage of labels that have a matching Concept node',
      hm7.check_cypher = 'CALL db.labels() YIELD label WITH collect(label) AS all_labels MATCH (c:Concept) WHERE c.name IS NOT NULL WITH all_labels, collect(DISTINCT c.name) AS concept_names WITH all_labels, concept_names, [l IN all_labels WHERE l IN concept_names] AS matching WITH matching, all_labels RETURN CASE WHEN size(all_labels) > 0 THEN size(matching)*100.0/size(all_labels) ELSE 0.0 END AS value',
      hm7.healthy_min = 30,
      hm7.healthy_max = 100,
      hm7.unit = 'percent',
      hm7.heal_protocol = 'concept-backfill',
      hm7.file_type = 'health-metric';

// 8. APOC Usage Rate — layer: capabilities
MERGE (hm8:HealthMetric {node_id: 'hm-apoc-usage-rate'})
  SET hm8.name = 'apoc-usage-rate',
      hm8.layer = 'capabilities',
      hm8.description = 'Percentage of APOC procedures/functions with at least one usage',
      hm8.check_cypher = 'MATCH (f) WHERE f:APOCProcedure OR f:APOCFunction WITH count(f) AS total OPTIONAL MATCH (f2) WHERE (f2:APOCProcedure OR f2:APOCFunction) AND (f2)-[:USED_BY]->() WITH total, count(DISTINCT f2) AS used RETURN CASE WHEN total > 0 THEN used*100.0/total ELSE 0.0 END AS value',
      hm8.healthy_min = 5,
      hm8.healthy_max = 100,
      hm8.unit = 'percent',
      hm8.heal_protocol = '',
      hm8.file_type = 'health-metric';

// 9. Rhythm Tick Rate — layer: rhythm
MERGE (hm9:HealthMetric {node_id: 'hm-rhythm-tick-rate'})
  SET hm9.name = 'rhythm-tick-rate',
      hm9.layer = 'rhythm',
      hm9.description = 'Heartbeat active in last 5 minutes (1=yes, 0=no)',
      hm9.check_cypher = 'MATCH (b:Being) RETURN CASE WHEN b.vital_measured_ms IS NOT NULL AND timestamp() - b.vital_measured_ms < 300000 THEN 1 ELSE 0 END AS value',
      hm9.healthy_min = 1,
      hm9.healthy_max = 1,
      hm9.unit = 'boolean',
      hm9.heal_protocol = 'heartbeat-restart',
      hm9.file_type = 'health-metric';

// 10. Trace Accumulation — layer: observability
MERGE (hm10:HealthMetric {node_id: 'hm-trace-accumulation'})
  SET hm10.name = 'trace-accumulation',
      hm10.layer = 'observability',
      hm10.description = 'Count of QueryTrace nodes accumulated in the system',
      hm10.check_cypher = 'MATCH (qt:QueryTrace) RETURN count(qt) AS value',
      hm10.healthy_min = 0,
      hm10.healthy_max = 10000,
      hm10.unit = 'count',
      hm10.heal_protocol = 'trace-summarize',
      hm10.file_type = 'health-metric';

// --- Phase 2: Wire all metrics to infrastructure --------------------------------

MATCH (ont:Ontology)
MATCH (being:Being {node_id: 'being-mycelium'})
MATCH (rhythm:Rhythm {node_id: 'rhythm-heartbeat'})
WITH ont, being, rhythm
MATCH (hm:HealthMetric) WHERE hm.file_type = 'health-metric'
MERGE (hm)-[:METRIC_OF]->(ont)
MERGE (hm)-[:MONITORED_BY]->(rhythm)
MERGE (hm)-[:MONITORS]->(being);

// Wire each metric to its layer concept (if it exists)
MATCH (hm:HealthMetric {layer: 'vocabulary'})
OPTIONAL MATCH (concept:Concept {name: 'vocabulary'})
WITH hm, concept WHERE concept IS NOT NULL
MERGE (hm)-[:MEASURES]->(concept);

MATCH (hm:HealthMetric {layer: 'execution'})
OPTIONAL MATCH (concept:Concept {name: 'execution'})
WITH hm, concept WHERE concept IS NOT NULL
MERGE (hm)-[:MEASURES]->(concept);

MATCH (hm:HealthMetric {layer: 'economics'})
OPTIONAL MATCH (concept:Concept {name: 'economics'})
WITH hm, concept WHERE concept IS NOT NULL
MERGE (hm)-[:MEASURES]->(concept);

MATCH (hm:HealthMetric {layer: 'semantic'})
OPTIONAL MATCH (concept:Concept {name: 'semantic'})
WITH hm, concept WHERE concept IS NOT NULL
MERGE (hm)-[:MEASURES]->(concept);

MATCH (hm:HealthMetric {layer: 'collaboration'})
OPTIONAL MATCH (concept:Concept {name: 'collaboration'})
WITH hm, concept WHERE concept IS NOT NULL
MERGE (hm)-[:MEASURES]->(concept);

MATCH (hm:HealthMetric {layer: 'docs'})
OPTIONAL MATCH (concept:Concept {name: 'docs'})
WITH hm, concept WHERE concept IS NOT NULL
MERGE (hm)-[:MEASURES]->(concept);

MATCH (hm:HealthMetric {layer: 'capabilities'})
OPTIONAL MATCH (concept:Concept {name: 'capabilities'})
WITH hm, concept WHERE concept IS NOT NULL
MERGE (hm)-[:MEASURES]->(concept);

MATCH (hm:HealthMetric {layer: 'rhythm'})
OPTIONAL MATCH (concept:Concept {name: 'rhythm'})
WITH hm, concept WHERE concept IS NOT NULL
MERGE (hm)-[:MEASURES]->(concept);

MATCH (hm:HealthMetric {layer: 'observability'})
OPTIONAL MATCH (concept:Concept {name: 'observability'})
WITH hm, concept WHERE concept IS NOT NULL
MERGE (hm)-[:MEASURES]->(concept);

// Wire metrics to their heal protocols (if specified and protocol exists)
MATCH (hm:HealthMetric) WHERE hm.heal_protocol <> ''
WITH hm, hm.heal_protocol AS heal_id
OPTIONAL MATCH (proto:Protocol {node_id: heal_id})
WITH hm, proto WHERE proto IS NOT NULL
MERGE (hm)-[:HEALED_BY]->(proto);

// --- Phase 3: The Dynamic Evaluator Query ----------------------------------------
// This query executes every metric's check_cypher and produces a health report.
// It uses apoc.cypher.run to invoke each metric's check dynamically.

MATCH (hm:HealthMetric) WHERE hm.file_type = 'health-metric'
CALL apoc.cypher.run(hm.check_cypher, {}) YIELD value AS result
WITH hm, result.value AS metric_value
RETURN
  hm.node_id AS metric_id,
  hm.name AS metric_name,
  hm.layer AS layer,
  metric_value AS current_value,
  hm.unit AS unit,
  hm.healthy_min AS healthy_min,
  hm.healthy_max AS healthy_max,
  CASE
    WHEN metric_value >= hm.healthy_min AND metric_value <= hm.healthy_max THEN 'healthy'
    WHEN metric_value < hm.healthy_min THEN 'low'
    ELSE 'high'
  END AS status,
  hm.heal_protocol AS heal_protocol,
  hm.description AS description
ORDER BY status DESC, layer, metric_name;
