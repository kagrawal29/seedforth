// @kind: seed
// ============================================================================
// Protocol: Claim Test Rubric Seed
// ============================================================================
// Every Purpose, Subsystem, DesignPrinciple, and Rhythm makes CLAIMS about
// what the system does. Those claims must be TESTABLE, MEASURABLE, and SCORED
// — not assumed.
//
// This protocol creates a first-class graph layer for claim testing:
// - 6 TestDimension nodes for multidimensional measurement
// - 25+ ClaimTest nodes covering all 6 Purposes and key subsystems
// - Bidirectional edges (TESTED_BY, IN_DIMENSION, PART_OF, EVALUATED_BY)
// - Integration with existing UXRubric nodes (bridge old + new measurement layers)
//
// ============================================================================

// === GET REFERENCE NODES ===
MATCH (ontology:Ontology {node_id: 'ontology-mycelium'})
MATCH (hb:Rhythm {node_id: 'rhythm-heartbeat'})
WITH ontology, hb

// === CREATE TEST DIMENSIONS ===
MERGE (dim_reliability:TestDimension {node_id: 'dim-reliability'})
SET dim_reliability.name = 'Reliability',
    dim_reliability.description = 'Does it work every time? Error rates, success rates, stability under load.',
    dim_reliability.file_type = 'test-dimension'

MERGE (dim_coverage:TestDimension {node_id: 'dim-coverage'})
SET dim_coverage.name = 'Coverage',
    dim_coverage.description = 'Does it reach everything? Embedding %, concept %, atom %, fractal completeness.',
    dim_coverage.file_type = 'test-dimension'

MERGE (dim_performance:TestDimension {node_id: 'dim-performance'})
SET dim_performance.name = 'Performance',
    dim_performance.description = 'Is it fast enough? Query latency, heartbeat duration, embed throughput.',
    dim_performance.file_type = 'test-dimension'

MERGE (dim_density:TestDimension {node_id: 'dim-density'})
SET dim_density.name = 'Density',
    dim_density.description = 'Is it connected enough? Typed density, island count, lifecycle edge completeness.',
    dim_density.file_type = 'test-dimension'

MERGE (dim_economics:TestDimension {node_id: 'dim-economics'})
SET dim_economics.name = 'Economics',
    dim_economics.description = 'Is it worth the cost? Amortization rate, cost per use, dead protocol %.',
    dim_economics.file_type = 'test-dimension'

MERGE (dim_autonomy:TestDimension {node_id: 'dim-autonomy'})
SET dim_autonomy.name = 'Autonomy',
    dim_autonomy.description = 'Can it act without humans? Heal coverage, auto-resolution rate, question backlog.',
    dim_autonomy.file_type = 'test-dimension'

WITH ontology, hb, dim_reliability, dim_coverage, dim_performance, dim_density, dim_economics, dim_autonomy

// === CREATE CLAIM TESTS ===

// purpose-learn-from-use (5 tests)
MATCH (p_learn:Purpose {node_id: 'purpose-learn-from-use'})

MERGE (ct1:ClaimTest {node_id: 'ct-ingestion-rate'})
SET ct1.name = 'ingestion-rate',
    ct1.dimension = 'reliability',
    ct1.file_type = 'claim-test',
    ct1.unit = 'ratio',
    ct1.target_min = 0.90,
    ct1.target_max = NULL,
    ct1.description = 'Prompts successfully ingested / ask-traces. Measures intake health.',
    ct1.check_cypher = 'MATCH (p:Prompt) WITH COUNT(p) AS prompt_count MATCH (qt:QueryTrace {command: "ask"}) WITH prompt_count, COUNT(qt) AS ask_count RETURN CASE WHEN ask_count = 0 THEN 0 ELSE toFloat(prompt_count) / toFloat(ask_count) END AS value',
    ct1.current_value = NULL,
    ct1.current_status = 'untested'

MERGE (ct1)-[:IN_DIMENSION]->(dim_reliability)
MERGE (ct1)-[:PART_OF]->(ontology)
MERGE (p_learn)-[:TESTED_BY]->(ct1)
MERGE (hb)-[:EVALUATED_BY]->(ct1)

MERGE (ct2:ClaimTest {node_id: 'ct-hebbian-reuse'})
SET ct2.name = 'hebbian-reuse',
    ct2.dimension = 'reliability',
    ct2.file_type = 'claim-test',
    ct2.unit = 'ratio',
    ct2.target_min = 0.15,
    ct2.target_max = NULL,
    ct2.description = 'Queries with fire_count > 1 / total queries. Measures learning through reuse.',
    ct2.check_cypher = 'MATCH (q:Query) WITH COUNT(q) AS total_queries MATCH (q:Query) WHERE q.fire_count > 1 WITH total_queries, COUNT(q) AS reused_queries RETURN CASE WHEN total_queries = 0 THEN 0 ELSE toFloat(reused_queries) / toFloat(total_queries) END AS value',
    ct2.current_value = NULL,
    ct2.current_status = 'untested'

MERGE (ct2)-[:IN_DIMENSION]->(dim_reliability)
MERGE (ct2)-[:PART_OF]->(ontology)
MERGE (p_learn)-[:TESTED_BY]->(ct2)
MERGE (hb)-[:EVALUATED_BY]->(ct2)

MERGE (ct3:ClaimTest {node_id: 'ct-vocabulary-growth'})
SET ct3.name = 'vocabulary-growth',
    ct3.dimension = 'coverage',
    ct3.file_type = 'claim-test',
    ct3.unit = 'count',
    ct3.target_min = 500,
    ct3.target_max = NULL,
    ct3.description = 'Count of non-stopword Words in graph. Measures vocabulary density.',
    ct3.check_cypher = 'MATCH (w:Word) WHERE NOT (w)-[:IS_STOPWORD]->() RETURN COUNT(w) AS value',
    ct3.current_value = NULL,
    ct3.current_status = 'untested'

MERGE (ct3)-[:IN_DIMENSION]->(dim_coverage)
MERGE (ct3)-[:PART_OF]->(ontology)
MERGE (p_learn)-[:TESTED_BY]->(ct3)
MERGE (hb)-[:EVALUATED_BY]->(ct3)

MERGE (ct4:ClaimTest {node_id: 'ct-bigram-density'})
SET ct4.name = 'bigram-density',
    ct4.dimension = 'density',
    ct4.file_type = 'claim-test',
    ct4.unit = 'ratio',
    ct4.target_min = 0.5,
    ct4.target_max = NULL,
    ct4.description = 'Bigram edges / content words. Measures sequential linguistic connectivity.',
    ct4.check_cypher = 'MATCH (w:Word) WHERE NOT (w)-[:IS_STOPWORD]->() WITH COUNT(w) AS word_count MATCH (b:Bigram) WHERE (b)-[:MADE_OF]->(:Word) WITH word_count, COUNT(b) AS bigram_count RETURN CASE WHEN word_count = 0 THEN 0 ELSE toFloat(bigram_count) / toFloat(word_count) END AS value',
    ct4.current_value = NULL,
    ct4.current_status = 'untested'

MERGE (ct4)-[:IN_DIMENSION]->(dim_density)
MERGE (ct4)-[:PART_OF]->(ontology)
MERGE (p_learn)-[:TESTED_BY]->(ct4)
MERGE (hb)-[:EVALUATED_BY]->(ct4)

MERGE (ct5:ClaimTest {node_id: 'ct-resolution-rate'})
SET ct5.name = 'resolution-rate',
    ct5.dimension = 'autonomy',
    ct5.file_type = 'claim-test',
    ct5.unit = 'ratio',
    ct5.target_min = 0.70,
    ct5.target_max = NULL,
    ct5.description = 'Prompts with RESOLVED_TO edge / total prompts. Measures self-directed problem closure.',
    ct5.check_cypher = 'MATCH (p:Prompt) WITH COUNT(p) AS total_prompts MATCH (p:Prompt)-[:RESOLVED_TO]->() WITH total_prompts, COUNT(DISTINCT p) AS resolved_prompts RETURN CASE WHEN total_prompts = 0 THEN 0 ELSE toFloat(resolved_prompts) / toFloat(total_prompts) END AS value',
    ct5.current_value = NULL,
    ct5.current_status = 'untested'

MERGE (ct5)-[:IN_DIMENSION]->(dim_autonomy)
MERGE (ct5)-[:PART_OF]->(ontology)
MERGE (p_learn)-[:TESTED_BY]->(ct5)
MERGE (hb)-[:EVALUATED_BY]->(ct5)

WITH ontology, hb, dim_reliability, dim_coverage, dim_performance, dim_density, dim_economics, dim_autonomy

// purpose-speak-about-itself (4 tests)
MATCH (p_speak:Purpose {node_id: 'purpose-speak-about-itself'})

MERGE (ct6:ClaimTest {node_id: 'ct-concept-coverage'})
SET ct6.name = 'concept-coverage',
    ct6.dimension = 'coverage',
    ct6.file_type = 'claim-test',
    ct6.unit = 'ratio',
    ct6.target_min = 0.30,
    ct6.target_max = NULL,
    ct6.description = 'Labels with SEEMS_LIKE->Concept / total labels. Self-awareness via semantic classification.',
    ct6.check_cypher = 'MATCH (n) WHERE n.label IS NOT NULL WITH COUNT(n) AS total_labels MATCH (n) WHERE n.label IS NOT NULL AND (n)-[:SEEMS_LIKE]->(:Concept) WITH total_labels, COUNT(n) AS classified RETURN CASE WHEN total_labels = 0 THEN 0 ELSE toFloat(classified) / toFloat(total_labels) END AS value',
    ct6.current_value = NULL,
    ct6.current_status = 'untested'

MERGE (ct6)-[:IN_DIMENSION]->(dim_coverage)
MERGE (ct6)-[:PART_OF]->(ontology)
MERGE (p_speak)-[:TESTED_BY]->(ct6)
MERGE (hb)-[:EVALUATED_BY]->(ct6)

MERGE (ct7:ClaimTest {node_id: 'ct-guide-coverage'})
SET ct7.name = 'guide-coverage',
    ct7.dimension = 'coverage',
    ct7.file_type = 'claim-test',
    ct7.unit = 'ratio',
    ct7.target_min = 0.50,
    ct7.target_max = NULL,
    ct7.description = 'Key operations with attached Guide / total operations. Self-instruction completeness.',
    ct7.check_cypher = 'MATCH (op:Operation) WITH COUNT(op) AS total_ops MATCH (op:Operation)-[:HAS_GUIDE]->(:Guide) WITH total_ops, COUNT(op) AS guided_ops RETURN CASE WHEN total_ops = 0 THEN 0 ELSE toFloat(guided_ops) / toFloat(total_ops) END AS value',
    ct7.current_value = NULL,
    ct7.current_status = 'untested'

MERGE (ct7)-[:IN_DIMENSION]->(dim_coverage)
MERGE (ct7)-[:PART_OF]->(ontology)
MERGE (p_speak)-[:TESTED_BY]->(ct7)
MERGE (hb)-[:EVALUATED_BY]->(ct7)

MERGE (ct8:ClaimTest {node_id: 'ct-metaphor-illumination'})
SET ct8.name = 'metaphor-illumination',
    ct8.dimension = 'density',
    ct8.file_type = 'claim-test',
    ct8.unit = 'ratio',
    ct8.target_min = 10,
    ct8.target_max = NULL,
    ct8.description = 'Avg ILLUMINATES edges per Metaphor. Richness of explanatory power.',
    ct8.check_cypher = 'MATCH (m:Metaphor) WITH m, COUNT((m)-[:ILLUMINATES]->()) AS illum_count WITH AVG(illum_count) AS avg_illum RETURN COALESCE(avg_illum, 0) AS value',
    ct8.current_value = NULL,
    ct8.current_status = 'untested'

MERGE (ct8)-[:IN_DIMENSION]->(dim_density)
MERGE (ct8)-[:PART_OF]->(ontology)
MERGE (p_speak)-[:TESTED_BY]->(ct8)
MERGE (hb)-[:EVALUATED_BY]->(ct8)

MERGE (ct9:ClaimTest {node_id: 'ct-compose-reply-success'})
SET ct9.name = 'compose-reply-success',
    ct9.dimension = 'reliability',
    ct9.file_type = 'claim-test',
    ct9.unit = 'ratio',
    ct9.target_min = 0.80,
    ct9.target_max = NULL,
    ct9.description = 'Compose-reply protocol success rate (set to 0 until tested in production).',
    ct9.check_cypher = 'MATCH (p:Protocol {node_id: "protocol-compose-reply"}) OPTIONAL MATCH (p)-[:FIRED_BY]->(t:Trace) WHERE t.success = true WITH COUNT(t) AS success_count MATCH (p)-[:FIRED_BY]->(t:Trace) WITH success_count, COUNT(t) AS total_count RETURN CASE WHEN total_count = 0 THEN 0 ELSE toFloat(success_count) / toFloat(total_count) END AS value',
    ct9.current_value = 0,
    ct9.current_status = 'untested'

MERGE (ct9)-[:IN_DIMENSION]->(dim_reliability)
MERGE (ct9)-[:PART_OF]->(ontology)
MERGE (p_speak)-[:TESTED_BY]->(ct9)
MERGE (hb)-[:EVALUATED_BY]->(ct9)

WITH ontology, hb, dim_reliability, dim_coverage, dim_performance, dim_density, dim_economics, dim_autonomy

// purpose-amortize-llm-cost (4 tests)
MATCH (p_amortize:Purpose {node_id: 'purpose-amortize-llm-cost'})

MERGE (ct10:ClaimTest {node_id: 'ct-protocol-amortization'})
SET ct10.name = 'protocol-amortization',
    ct10.dimension = 'economics',
    ct10.file_type = 'claim-test',
    ct10.unit = 'ratio',
    ct10.target_min = 0.10,
    ct10.target_max = NULL,
    ct10.description = '(amortizing+amortized) protocols / total protocols. Measures cost distribution.',
    ct10.check_cypher = 'MATCH (pr:Protocol) WITH COUNT(pr) AS total_protocols MATCH (pr:Protocol) WHERE pr.status IN ["amortizing", "amortized"] WITH total_protocols, COUNT(pr) AS amortized_count RETURN CASE WHEN total_protocols = 0 THEN 0 ELSE toFloat(amortized_count) / toFloat(total_protocols) END AS value',
    ct10.current_value = NULL,
    ct10.current_status = 'untested'

MERGE (ct10)-[:IN_DIMENSION]->(dim_economics)
MERGE (ct10)-[:PART_OF]->(ontology)
MERGE (p_amortize)-[:TESTED_BY]->(ct10)
MERGE (hb)-[:EVALUATED_BY]->(ct10)

MERGE (ct11:ClaimTest {node_id: 'ct-dead-protocol-ratio'})
SET ct11.name = 'dead-protocol-ratio',
    ct11.dimension = 'economics',
    ct11.file_type = 'claim-test',
    ct11.unit = 'ratio',
    ct11.target_min = NULL,
    ct11.target_max = 0.70,
    ct11.description = 'Dead protocols / total protocols. Measures code cleanup and refactoring debt.',
    ct11.check_cypher = 'MATCH (pr:Protocol) WITH COUNT(pr) AS total_protocols MATCH (pr:Protocol) WHERE pr.status = "dead" WITH total_protocols, COUNT(pr) AS dead_count RETURN CASE WHEN total_protocols = 0 THEN 0 ELSE toFloat(dead_count) / toFloat(total_protocols) END AS value',
    ct11.current_value = NULL,
    ct11.current_status = 'untested'

MERGE (ct11)-[:IN_DIMENSION]->(dim_economics)
MERGE (ct11)-[:PART_OF]->(ontology)
MERGE (p_amortize)-[:TESTED_BY]->(ct11)
MERGE (hb)-[:EVALUATED_BY]->(ct11)

MERGE (ct12:ClaimTest {node_id: 'ct-avg-cost-per-use'})
SET ct12.name = 'avg-cost-per-use',
    ct12.dimension = 'economics',
    ct12.file_type = 'claim-test',
    ct12.unit = 'ratio',
    ct12.target_min = NULL,
    ct12.target_max = 0.05,
    ct12.description = 'Average cost_per_use across fired protocols. Measures LLM amortization success.',
    ct12.check_cypher = 'MATCH (pr:Protocol) WHERE pr.fire_count > 0 AND pr.cost_per_use IS NOT NULL WITH AVG(pr.cost_per_use) AS avg_cost RETURN COALESCE(avg_cost, 0) AS value',
    ct12.current_value = NULL,
    ct12.current_status = 'untested'

MERGE (ct12)-[:IN_DIMENSION]->(dim_economics)
MERGE (ct12)-[:PART_OF]->(ontology)
MERGE (p_amortize)-[:TESTED_BY]->(ct12)
MERGE (hb)-[:EVALUATED_BY]->(ct12)

MERGE (ct13:ClaimTest {node_id: 'ct-atom-fire-coverage'})
SET ct13.name = 'atom-fire-coverage',
    ct13.dimension = 'coverage',
    ct13.file_type = 'claim-test',
    ct13.unit = 'ratio',
    ct13.target_min = 0.10,
    ct13.target_max = NULL,
    ct13.description = 'Atoms with fire_count > 0 / total atoms. Measures atomic-level reuse.',
    ct13.check_cypher = 'MATCH (a:CypherAtom) WITH COUNT(a) AS total_atoms MATCH (a:CypherAtom) WHERE a.fire_count > 0 WITH total_atoms, COUNT(a) AS fired_atoms RETURN CASE WHEN total_atoms = 0 THEN 0 ELSE toFloat(fired_atoms) / toFloat(total_atoms) END AS value',
    ct13.current_value = NULL,
    ct13.current_status = 'untested'

MERGE (ct13)-[:IN_DIMENSION]->(dim_coverage)
MERGE (ct13)-[:PART_OF]->(ontology)
MERGE (p_amortize)-[:TESTED_BY]->(ct13)
MERGE (hb)-[:EVALUATED_BY]->(ct13)

WITH ontology, hb, dim_reliability, dim_coverage, dim_performance, dim_density, dim_economics, dim_autonomy

// purpose-self-heal (4 tests)
MATCH (p_heal:Purpose {node_id: 'purpose-self-heal'})

MERGE (ct14:ClaimTest {node_id: 'ct-heal-coverage'})
SET ct14.name = 'heal-coverage',
    ct14.dimension = 'autonomy',
    ct14.file_type = 'claim-test',
    ct14.unit = 'ratio',
    ct14.target_min = 0.50,
    ct14.target_max = NULL,
    ct14.description = 'Questions with heal_protocol / total questions. Measures auto-remediation capability.',
    ct14.check_cypher = 'MATCH (q:Question) WITH COUNT(q) AS total_questions MATCH (q:Question) WHERE (q)-[:HEALED_BY]->(:Protocol) WITH total_questions, COUNT(q) AS healed_questions RETURN CASE WHEN total_questions = 0 THEN 0 ELSE toFloat(healed_questions) / toFloat(total_questions) END AS value',
    ct14.current_value = NULL,
    ct14.current_status = 'untested'

MERGE (ct14)-[:IN_DIMENSION]->(dim_autonomy)
MERGE (ct14)-[:PART_OF]->(ontology)
MERGE (p_heal)-[:TESTED_BY]->(ct14)
MERGE (hb)-[:EVALUATED_BY]->(ct14)

MERGE (ct15:ClaimTest {node_id: 'ct-auto-resolution'})
SET ct15.name = 'auto-resolution',
    ct15.dimension = 'autonomy',
    ct15.file_type = 'claim-test',
    ct15.unit = 'ratio',
    ct15.target_min = 0.10,
    ct15.target_max = NULL,
    ct15.description = 'Questions auto-healed / total questions. Measures autonomous healing success.',
    ct15.check_cypher = 'MATCH (q:Question) WITH COUNT(q) AS total_questions MATCH (q:Question) WHERE q.auto_resolved = true WITH total_questions, COUNT(q) AS auto_resolved RETURN CASE WHEN total_questions = 0 THEN 0 ELSE toFloat(auto_resolved) / toFloat(total_questions) END AS value',
    ct15.current_value = NULL,
    ct15.current_status = 'untested'

MERGE (ct15)-[:IN_DIMENSION]->(dim_autonomy)
MERGE (ct15)-[:PART_OF]->(ontology)
MERGE (p_heal)-[:TESTED_BY]->(ct15)
MERGE (hb)-[:EVALUATED_BY]->(ct15)

MERGE (ct16:ClaimTest {node_id: 'ct-invariant-health'})
SET ct16.name = 'invariant-health',
    ct16.dimension = 'reliability',
    ct16.file_type = 'claim-test',
    ct16.unit = 'ratio',
    ct16.target_min = 0.80,
    ct16.target_max = NULL,
    ct16.description = 'Healthy invariants / total invariants. Measures system stability baseline.',
    ct16.check_cypher = 'MATCH (i:Invariant) WITH COUNT(i) AS total_invariants MATCH (i:Invariant) WHERE i.is_healthy = true WITH total_invariants, COUNT(i) AS healthy_count RETURN CASE WHEN total_invariants = 0 THEN 0 ELSE toFloat(healthy_count) / toFloat(total_invariants) END AS value',
    ct16.current_value = NULL,
    ct16.current_status = 'untested'

MERGE (ct16)-[:IN_DIMENSION]->(dim_reliability)
MERGE (ct16)-[:PART_OF]->(ontology)
MERGE (p_heal)-[:TESTED_BY]->(ct16)
MERGE (hb)-[:EVALUATED_BY]->(ct16)

MERGE (ct17:ClaimTest {node_id: 'ct-vital-coverage'})
SET ct17.name = 'vital-coverage',
    ct17.dimension = 'reliability',
    ct17.file_type = 'claim-test',
    ct17.unit = 'ratio',
    ct17.target_min = 1.0,
    ct17.target_max = NULL,
    ct17.description = 'Vital-sign invariants with status != NULL / total vital invariants. Liveness requirement.',
    ct17.check_cypher = 'MATCH (i:Invariant {is_vital: true}) WITH COUNT(i) AS total_vitals MATCH (i:Invariant {is_vital: true}) WHERE i.last_status IS NOT NULL WITH total_vitals, COUNT(i) AS reported RETURN CASE WHEN total_vitals = 0 THEN 1 ELSE toFloat(reported) / toFloat(total_vitals) END AS value',
    ct17.current_value = NULL,
    ct17.current_status = 'untested'

MERGE (ct17)-[:IN_DIMENSION]->(dim_reliability)
MERGE (ct17)-[:PART_OF]->(ontology)
MERGE (p_heal)-[:TESTED_BY]->(ct17)
MERGE (hb)-[:EVALUATED_BY]->(ct17)

WITH ontology, hb, dim_reliability, dim_coverage, dim_performance, dim_density, dim_economics, dim_autonomy

// purpose-graph-native-authority (3 tests)
MATCH (p_authority:Purpose {node_id: 'purpose-graph-native-authority'})

MERGE (ct18:ClaimTest {node_id: 'ct-merkle-stability'})
SET ct18.name = 'merkle-stability',
    ct18.dimension = 'reliability',
    ct18.file_type = 'claim-test',
    ct18.unit = 'boolean',
    ct18.target_min = 1,
    ct18.target_max = NULL,
    ct18.description = 'Root hash drift at idle: vital_root_hash = root_hash. Immutability guarantee.',
    ct18.check_cypher = 'MATCH (b:Being) RETURN CASE WHEN b.vital_root_hash = b.root_hash THEN 1 ELSE 0 END AS value LIMIT 1',
    ct18.current_value = NULL,
    ct18.current_status = 'untested'

MERGE (ct18)-[:IN_DIMENSION]->(dim_reliability)
MERGE (ct18)-[:PART_OF]->(ontology)
MERGE (p_authority)-[:TESTED_BY]->(ct18)
MERGE (hb)-[:EVALUATED_BY]->(ct18)

MERGE (ct19:ClaimTest {node_id: 'ct-atom-coverage'})
SET ct19.name = 'atom-coverage',
    ct19.dimension = 'coverage',
    ct19.file_type = 'claim-test',
    ct19.unit = 'ratio',
    ct19.target_min = 0.60,
    ct19.target_max = NULL,
    ct19.description = 'Protocols with atoms / total protocols. Decomposition into atomic cyphers.',
    ct19.check_cypher = 'MATCH (pr:Protocol) WITH COUNT(pr) AS total_protocols MATCH (pr:Protocol)-[:COMPOSED_OF]->(:CypherAtom) WITH total_protocols, COUNT(DISTINCT pr) AS atomized RETURN CASE WHEN total_protocols = 0 THEN 0 ELSE toFloat(atomized) / toFloat(total_protocols) END AS value',
    ct19.current_value = NULL,
    ct19.current_status = 'untested'

MERGE (ct19)-[:IN_DIMENSION]->(dim_coverage)
MERGE (ct19)-[:PART_OF]->(ontology)
MERGE (p_authority)-[:TESTED_BY]->(ct19)
MERGE (hb)-[:EVALUATED_BY]->(ct19)

MERGE (ct20:ClaimTest {node_id: 'ct-cli-trace-ratio'})
SET ct20.name = 'cli-trace-ratio',
    ct20.dimension = 'performance',
    ct20.file_type = 'claim-test',
    ct20.unit = 'ratio',
    ct20.target_min = 0.50,
    ct20.target_max = NULL,
    ct20.description = 'Shell/CLI traces / total cypher operations. All-cypher verification.',
    ct20.check_cypher = 'MATCH (qt:QueryTrace {source: "shell"}) WITH COUNT(qt) AS shell_count MATCH (qt:QueryTrace) WITH shell_count, COUNT(qt) AS total_count RETURN CASE WHEN total_count = 0 THEN 0 ELSE toFloat(shell_count) / toFloat(total_count) END AS value',
    ct20.current_value = NULL,
    ct20.current_status = 'untested'

MERGE (ct20)-[:IN_DIMENSION]->(dim_performance)
MERGE (ct20)-[:PART_OF]->(ontology)
MERGE (p_authority)-[:TESTED_BY]->(ct20)
MERGE (hb)-[:EVALUATED_BY]->(ct20)

WITH ontology, hb, dim_reliability, dim_coverage, dim_performance, dim_density, dim_economics, dim_autonomy

// purpose-dense-by-design (5 tests)
MATCH (p_dense:Purpose {node_id: 'purpose-dense-by-design'})

MERGE (ct21:ClaimTest {node_id: 'ct-typed-density'})
SET ct21.name = 'typed-density',
    ct21.dimension = 'density',
    ct21.file_type = 'claim-test',
    ct21.unit = 'ratio',
    ct21.target_min = 3.0,
    ct21.target_max = NULL,
    ct21.description = 'Typed edges / nodes. Connectivity breadth at every node.',
    ct21.check_cypher = 'MATCH (n) WHERE NOT (n:TestDimension) WITH COUNT(n) AS node_count MATCH (n)-[e]->() WHERE e.type IS NOT NULL RETURN CASE WHEN node_count = 0 THEN 0 ELSE toFloat(COUNT(e)) / toFloat(node_count) END AS value',
    ct21.current_value = NULL,
    ct21.current_status = 'untested'

MERGE (ct21)-[:IN_DIMENSION]->(dim_density)
MERGE (ct21)-[:PART_OF]->(ontology)
MERGE (p_dense)-[:TESTED_BY]->(ct21)
MERGE (hb)-[:EVALUATED_BY]->(ct21)

MERGE (ct22:ClaimTest {node_id: 'ct-island-count'})
SET ct22.name = 'island-count',
    ct22.dimension = 'density',
    ct22.file_type = 'claim-test',
    ct22.unit = 'count',
    ct22.target_min = NULL,
    ct22.target_max = 5,
    ct22.description = 'Labels with 0 typed outgoing edges. Isolated nodes indicate schema gaps.',
    ct22.check_cypher = 'MATCH (n) WHERE n.label IS NOT NULL AND NOT (n)-[e]->() WHERE e.type IS NOT NULL RETURN COUNT(n) AS value',
    ct22.current_value = NULL,
    ct22.current_status = 'untested'

MERGE (ct22)-[:IN_DIMENSION]->(dim_density)
MERGE (ct22)-[:PART_OF]->(ontology)
MERGE (p_dense)-[:TESTED_BY]->(ct22)
MERGE (hb)-[:EVALUATED_BY]->(ct22)

MERGE (ct23:ClaimTest {node_id: 'ct-fractal-completeness'})
SET ct23.name = 'fractal-completeness',
    ct23.dimension = 'density',
    ct23.file_type = 'claim-test',
    ct23.unit = 'ratio',
    ct23.target_min = 0.67,
    ct23.target_max = NULL,
    ct23.description = 'Key labels with 3+ lifecycle edges / 9 possible. Fractal self-similarity.',
    ct23.check_cypher = 'MATCH (n:Label) WITH COUNT(n) AS total_labels, COLLECT(n) AS all_labels UNWIND all_labels AS n WITH n, [(n)-[e]->() WHERE e.type IN ["CREATED_BY", "MODIFIED_BY", "DEPRECATED_BY", "REPLACED_BY", "SPAWNED_FROM", "TESTED_BY", "DEPENDS_ON", "COMPLETES", "CONFLICTS_WITH"] | e] AS lifecycle_edges WITH COUNT(CASE WHEN SIZE(lifecycle_edges) >= 3 THEN 1 END) AS complete RETURN CASE WHEN total_labels = 0 THEN 0 ELSE toFloat(complete) / toFloat(total_labels) END AS value',
    ct23.current_value = NULL,
    ct23.current_status = 'untested'

MERGE (ct23)-[:IN_DIMENSION]->(dim_density)
MERGE (ct23)-[:PART_OF]->(ontology)
MERGE (p_dense)-[:TESTED_BY]->(ct23)
MERGE (hb)-[:EVALUATED_BY]->(ct23)

MERGE (ct24:ClaimTest {node_id: 'ct-orphan-rate'})
SET ct24.name = 'orphan-rate',
    ct24.dimension = 'density',
    ct24.file_type = 'claim-test',
    ct24.unit = 'ratio',
    ct24.target_min = NULL,
    ct24.target_max = 0.02,
    ct24.description = 'Orphan nodes (no incoming/outgoing edges) / total. Measures wiring completeness.',
    ct24.check_cypher = 'MATCH (n) WHERE NOT (n:TestDimension) WITH COUNT(n) AS total_nodes MATCH (n) WHERE NOT (n:TestDimension) AND NOT (n)-[]-() RETURN CASE WHEN total_nodes = 0 THEN 0 ELSE toFloat(COUNT(n)) / toFloat(total_nodes) END AS value',
    ct24.current_value = NULL,
    ct24.current_status = 'untested'

MERGE (ct24)-[:IN_DIMENSION]->(dim_density)
MERGE (ct24)-[:PART_OF]->(ontology)
MERGE (p_dense)-[:TESTED_BY]->(ct24)
MERGE (hb)-[:EVALUATED_BY]->(ct24)

MERGE (ct25:ClaimTest {node_id: 'ct-community-coverage'})
SET ct25.name = 'community-coverage',
    ct25.dimension = 'coverage',
    ct25.file_type = 'claim-test',
    ct25.unit = 'ratio',
    ct25.target_min = 0.50,
    ct25.target_max = NULL,
    ct25.description = 'Nodes in multi-node communities / total. Measures semantic clustering.',
    ct25.check_cypher = 'MATCH (n) WHERE NOT (n:TestDimension) WITH COUNT(n) AS total_nodes MATCH (n) WHERE NOT (n:TestDimension) AND ((n)-[:SIMILAR]->(:Label) OR (n)<-[:SIMILAR]-(:Label)) RETURN CASE WHEN total_nodes = 0 THEN 0 ELSE toFloat(COUNT(DISTINCT n)) / toFloat(total_nodes) END AS value',
    ct25.current_value = NULL,
    ct25.current_status = 'untested'

MERGE (ct25)-[:IN_DIMENSION]->(dim_coverage)
MERGE (ct25)-[:PART_OF]->(ontology)
MERGE (p_dense)-[:TESTED_BY]->(ct25)
MERGE (hb)-[:EVALUATED_BY]->(ct25)

WITH ontology, hb, dim_reliability, dim_coverage, dim_performance, dim_density, dim_economics, dim_autonomy

// === BRIDGE UX RUBRIC TO TEST DIMENSIONS ===
OPTIONAL MATCH (safety:UXDimension {node_id: 'uxdim-safety'})
OPTIONAL MATCH (observability:UXDimension {node_id: 'uxdim-observability'})
OPTIONAL MATCH (speed:UXDimension {node_id: 'uxdim-speed'})
OPTIONAL MATCH (discoverability:UXDimension {node_id: 'uxdim-discoverability'})
OPTIONAL MATCH (selfhealing:UXDimension {node_id: 'uxdim-self-healing'})
OPTIONAL MATCH (explainability:UXDimension {node_id: 'uxdim-explainability'})
OPTIONAL MATCH (predictability:UXDimension {node_id: 'uxdim-predictability'})

FOREACH (x IN CASE WHEN safety IS NOT NULL THEN [1] ELSE [] END | MERGE (safety)-[:ALIGNS_WITH]->(dim_reliability))
FOREACH (x IN CASE WHEN observability IS NOT NULL THEN [1] ELSE [] END | MERGE (observability)-[:ALIGNS_WITH]->(dim_coverage))
FOREACH (x IN CASE WHEN speed IS NOT NULL THEN [1] ELSE [] END | MERGE (speed)-[:ALIGNS_WITH]->(dim_performance))
FOREACH (x IN CASE WHEN discoverability IS NOT NULL THEN [1] ELSE [] END | MERGE (discoverability)-[:ALIGNS_WITH]->(dim_density))
FOREACH (x IN CASE WHEN selfhealing IS NOT NULL THEN [1] ELSE [] END | MERGE (selfhealing)-[:ALIGNS_WITH]->(dim_autonomy))
FOREACH (x IN CASE WHEN explainability IS NOT NULL THEN [1] ELSE [] END | MERGE (explainability)-[:ALIGNS_WITH]->(dim_coverage))
FOREACH (x IN CASE WHEN predictability IS NOT NULL THEN [1] ELSE [] END | MERGE (predictability)-[:ALIGNS_WITH]->(dim_reliability))

RETURN "ClaimTest rubric created" AS status
