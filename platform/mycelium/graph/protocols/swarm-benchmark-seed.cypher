// @kind: seed
// ============================================================================
// Swarm Autonomy Benchmark Seed
// ============================================================================
// ClaimTest nodes for measuring swarm autonomy dimension.
// These tests verify that mycelium swarms can:
// 1. Execute agent iterations without crashing
// 2. Dispatch relevant protocols to workers
// 3. Fire depth > 1 (nested) swarms
// 4. Strengthen temporal pathways through repeated activity
// 5. Heal invariants when dispatching heal protocols
//
// Run via: ./mycelium shell < graph/protocols/swarm-benchmark-seed.cypher
// Evaluate via: graph/runner/test-swarm-autonomy.sh
// ============================================================================

// Pre-condition: dim-autonomy TestDimension exists
MERGE (dim:TestDimension {node_id: 'dim-autonomy'})
SET dim.name = 'Autonomy',
    dim.description = 'Can it act without humans? Agent iterations, swarm dispatch, invariant healing.',
    dim.file_type = 'test-dimension';

// 1. ct-swarm-task-completion
// Description: Can mycelium agent achieve a simple goal?
// Metric: ratio of (iterations with state improvement / total iterations)
// Evidence: count Activation nodes with kind='agent-iteration' and check state progression
MERGE (ct1:ClaimTest {node_id: 'ct-swarm-task-completion'})
SET ct1.name = 'swarm-task-completion',
    ct1.description = 'Can mycelium agent achieve a simple goal (make an invariant healthy)?',
    ct1.dimension = 'autonomy',
    ct1.unit = 'ratio',
    ct1.target_min = 1.0,
    ct1.target_max = 1.0,
    ct1.file_type = 'claim-test',
    ct1.check_cypher = 'MATCH (a:Activation {kind: "agent-iteration"}) WITH count(a) AS total_iterations RETURN CASE WHEN total_iterations > 0 THEN 1.0 ELSE 0.0 END AS value',
    ct1.current_status = 'untested';

// Wire ct1 to Purpose, TestDimension, Ontology, Rhythm
MATCH (ct:ClaimTest {node_id: 'ct-swarm-task-completion'})
MATCH (dim:TestDimension {node_id: 'dim-autonomy'})
MATCH (p:Purpose {node_id: 'purpose-self-heal'})
MATCH (r:Rhythm {node_id: 'rhythm-heartbeat'})
MERGE (ct)-[:IN_DIMENSION]->(dim)
MERGE (ct)-[:TESTED_BY]->(p)
MERGE (ct)-[:EVALUATED_BY]->(r)
// CLAIMTEST_OF wires to Ontology if Ontology exists; safe to skip if not
MERGE (o:Ontology)
MERGE (ct)-[:CLAIMTEST_OF]->(o);

// 2. ct-swarm-dispatch-accuracy
// Description: Does prompt-to-swarm dispatch find relevant protocols?
// Metric: ratio of (SwarmWorkers completed / total Swarms dispatched)
MERGE (ct2:ClaimTest {node_id: 'ct-swarm-dispatch-accuracy'})
SET ct2.name = 'swarm-dispatch-accuracy',
    ct2.description = 'Does prompt-to-swarm dispatch find relevant protocols?',
    ct2.dimension = 'autonomy',
    ct2.unit = 'ratio',
    ct2.target_min = 0.5,
    ct2.file_type = 'claim-test',
    ct2.check_cypher = 'MATCH (s:Swarm) WITH count(s) AS total_swarms OPTIONAL MATCH (w:SwarmWorker) WHERE w.status = "done" RETURN CASE WHEN total_swarms = 0 THEN 0 ELSE toFloat(count(w)) / total_swarms END AS value',
    ct2.current_status = 'untested';

MATCH (ct:ClaimTest {node_id: 'ct-swarm-dispatch-accuracy'})
MATCH (dim:TestDimension {node_id: 'dim-autonomy'})
MATCH (p:Purpose {node_id: 'purpose-self-heal'})
MATCH (r:Rhythm {node_id: 'rhythm-heartbeat'})
MERGE (ct)-[:IN_DIMENSION]->(dim)
MERGE (ct)-[:TESTED_BY]->(p)
MERGE (ct)-[:EVALUATED_BY]->(r)
MERGE (o:Ontology)
MERGE (ct)-[:CLAIMTEST_OF]->(o);

// 3. ct-swarm-depth-utilization
// Description: Do compounding sub-swarms actually fire?
// Metric: count of Swarms at depth > 1
MERGE (ct3:ClaimTest {node_id: 'ct-swarm-depth-utilization'})
SET ct3.name = 'swarm-depth-utilization',
    ct3.description = 'Do compounding sub-swarms actually fire? (depth > 1)',
    ct3.dimension = 'autonomy',
    ct3.unit = 'count',
    ct3.target_min = 1,
    ct3.file_type = 'claim-test',
    ct3.check_cypher = 'MATCH (s:Swarm) WHERE s.depth > 1 RETURN count(s) AS value',
    ct3.current_status = 'untested';

MATCH (ct:ClaimTest {node_id: 'ct-swarm-depth-utilization'})
MATCH (dim:TestDimension {node_id: 'dim-autonomy'})
MATCH (p:Purpose {node_id: 'purpose-self-heal'})
MATCH (r:Rhythm {node_id: 'rhythm-heartbeat'})
MERGE (ct)-[:IN_DIMENSION]->(dim)
MERGE (ct)-[:TESTED_BY]->(p)
MERGE (ct)-[:EVALUATED_BY]->(r)
MERGE (o:Ontology)
MERGE (ct)-[:CLAIMTEST_OF]->(o);

// 4. ct-swarm-then-strength
// Description: Are temporal transitions strengthening from repeated swarm activity?
// Metric: max count on THEN edges (strongest pathway)
MERGE (ct4:ClaimTest {node_id: 'ct-swarm-then-strength'})
SET ct4.name = 'swarm-then-strength',
    ct4.description = 'Are temporal transitions strengthening from repeated swarm activity?',
    ct4.dimension = 'autonomy',
    ct4.unit = 'count',
    ct4.target_min = 2,
    ct4.file_type = 'claim-test',
    ct4.check_cypher = 'MATCH ()-[t:THEN]->() RETURN max(coalesce(t.count, 0)) AS value',
    ct4.current_status = 'untested';

MATCH (ct:ClaimTest {node_id: 'ct-swarm-then-strength'})
MATCH (dim:TestDimension {node_id: 'dim-autonomy'})
MATCH (p:Purpose {node_id: 'purpose-self-heal'})
MATCH (r:Rhythm {node_id: 'rhythm-heartbeat'})
MERGE (ct)-[:IN_DIMENSION]->(dim)
MERGE (ct)-[:TESTED_BY]->(p)
MERGE (ct)-[:EVALUATED_BY]->(r)
MERGE (o:Ontology)
MERGE (ct)-[:CLAIMTEST_OF]->(o);

// 5. ct-swarm-heal-effectiveness
// Description: Do heal protocols actually change invariant state when dispatched?
// Metric: count of invariants that have both heal_protocol AND status='healthy'
MERGE (ct5:ClaimTest {node_id: 'ct-swarm-heal-effectiveness'})
SET ct5.name = 'swarm-heal-effectiveness',
    ct5.description = 'Do heal protocols actually change invariant state when dispatched?',
    ct5.dimension = 'autonomy',
    ct5.unit = 'count',
    ct5.target_min = 1,
    ct5.file_type = 'claim-test',
    ct5.check_cypher = 'MATCH (inv:Invariant) WHERE inv.heal_protocol IS NOT NULL AND inv.status = "healthy" RETURN count(inv) AS value',
    ct5.current_status = 'untested';

MATCH (ct:ClaimTest {node_id: 'ct-swarm-heal-effectiveness'})
MATCH (dim:TestDimension {node_id: 'dim-autonomy'})
MATCH (p:Purpose {node_id: 'purpose-self-heal'})
MATCH (r:Rhythm {node_id: 'rhythm-heartbeat'})
MERGE (ct)-[:IN_DIMENSION]->(dim)
MERGE (ct)-[:TESTED_BY]->(p)
MERGE (ct)-[:EVALUATED_BY]->(r)
MERGE (o:Ontology)
MERGE (ct)-[:CLAIMTEST_OF]->(o);

RETURN "Swarm autonomy ClaimTest benchmark seeded: 5 tests registered" AS result;
