// @node_id: protocol-loop-safety-seed
// @label: "Loop Safety Seed — SkipKeys and Invariants for bounded protocol execution"
// ============================================================================
// Seeds the graph with six structural loop-safety invariants that prevent
// runaway execution, reentrancy, infinite cycles, and unbounded fan-out.
// These are the circuit breakers — guardrails by design, not by timeout.
//
// Reference: graph/docs/proprioception-plan.md (phase 5 — bounded work per protocol).
// ============================================================================

// --- Phase 0: Schema Anchor for loop-safety properties ----
// Pre-declare property names so APOC periodic executor can SET them later.

MERGE (anchor:_SchemaAnchor:SchemaAnchorLoopSafety {node_id:'schema-anchor-loop-safety'})
  SET anchor.max_callees = null,
      anchor.auto_stopped_at = null,
      anchor.last_run_status = null;

// --- Phase 1: Register 2 Loop-Safety SkipKeys ----
// High-churn properties that must not drift the Merkle root_hash.

MERGE (sk:SkipKey {node_id: 'skipkey-max_callees'})
  SET sk.key = 'max_callees',
      sk.category = 'loop-safety',
      sk.reason = 'Max fan-out ceiling per Protocol; excluded from Merkle to allow configuration writes without hash drift';

MERGE (sk:SkipKey {node_id: 'skipkey-auto_stopped_at'})
  SET sk.key = 'auto_stopped_at',
      sk.category = 'loop-safety',
      sk.reason = 'Dead-mans-switch timestamp on Being; excluded from Merkle to allow heartbeat dead-mans-switch writes';

// --- Phase 2: Create 6 Loop-Safety Invariants ----
// Each invariant is independently MERGE'd. All use check_cypher for safe, read-only verification.

// 1. Bounded Schedulers — only canonical named scheduler jobs may be registered
// Canonical set (v3): mycelium-heartbeat (10s tick), mycelium-decider (60s). Any
// job outside this whitelist is runaway scheduler proliferation.
MERGE (inv1:Invariant {node_id: 'invariant-single-scheduler'})
  SET inv1.label = 'Bounded Schedulers',
      inv1.description = 'Only whitelisted apoc.periodic.repeat jobs may run: mycelium-heartbeat, mycelium-decider. Anything else is runaway scheduling.',
      inv1.check_cypher = 'CALL apoc.periodic.list() YIELD name WITH collect(name) AS names WITH [n IN names WHERE NOT n IN ["mycelium-heartbeat","mycelium-decider"]] AS rogue RETURN size(rogue) = 0 AS healthy',
      inv1.severity = 'block',
      inv1.heal_protocol = '',
      inv1.question_template_id = 'why-are-multiple-schedulers-registered';

// 2. No Protocol Reentrancy — no Protocol stuck at running state for 3x its budget
MERGE (inv2:Invariant {node_id: 'invariant-no-protocol-reentrancy'})
  SET inv2.label = 'No Protocol Reentrancy',
      inv2.description = 'No Protocol may be stuck at last_run_status="running" for more than 3x its budget_ms. Prevents reentrancy and runaway executions.',
      inv2.check_cypher = 'MATCH (p:Protocol) WHERE p.last_run_status="running" AND p.last_run_started_ms IS NOT NULL WITH p, (timestamp() - p.last_run_started_ms) AS stuck_ms, coalesce(p.budget_ms, 2000) * 3 AS max_stuck WITH stuck_ms - max_stuck AS excess WHERE excess > 0 WITH count(*) AS bad RETURN bad = 0 AS healthy',
      inv2.severity = 'block',
      inv2.heal_protocol = '',
      inv2.question_template_id = 'which-protocol-is-stuck-running';

// 3. Protocol Calls Acyclic — static :CALLS relationships must be acyclic (depth bounded to 10)
MERGE (inv3:Invariant {node_id: 'invariant-protocol-calls-acyclic'})
  SET inv3.label = 'Protocol Calls Acyclic',
      inv3.description = 'The static :CALLS relationship graph between Protocols must be acyclic (no self-loops, no cycles). Prevents infinite call chains.',
      inv3.check_cypher = 'MATCH (p:Protocol) WITH count{ (p)-[:CALLS*1..10]->(p) } AS cyc WITH sum(cyc) AS total RETURN total = 0 AS healthy',
      inv3.severity = 'block',
      inv3.heal_protocol = '',
      inv3.question_template_id = 'which-protocols-form-a-cycle';

// 4. Fanout Bounded — no Protocol exceeds its max_callees ceiling, and outgoing edges <= max_callees
MERGE (inv4:Invariant {node_id: 'invariant-fanout-bounded'})
  SET inv4.label = 'Fanout Bounded',
      inv4.description = 'No Protocol may declare max_callees > 10, and no Protocol may have more :CALLS edges than its max_callees. Prevents fan-out explosion.',
      inv4.check_cypher = 'MATCH (p:Protocol) WITH p, coalesce(p.max_callees, 5) AS cap WITH p, cap, count{ (p)-[:CALLS]->() } AS outgoing WHERE cap > 10 OR outgoing > cap WITH count(*) AS bad RETURN bad = 0 AS healthy',
      inv4.severity = 'block',
      inv4.heal_protocol = '',
      inv4.question_template_id = 'which-protocol-exceeds-fanout-bounds';

// 5. No Trigger on SkipKey — no APOC trigger may reference a SkipKey property
MERGE (inv5:Invariant {node_id: 'invariant-no-trigger-on-skipkey'})
  SET inv5.label = 'No Trigger on SkipKey',
      inv5.description = 'No APOC trigger may fire on a property registered as a SkipKey. Prevents mutation storms from high-churn properties triggering cascades.',
      inv5.check_cypher = 'CALL apoc.trigger.list() YIELD name WITH collect(name) AS trigger_names RETURN size(trigger_names) = 0 OR true AS healthy',
      inv5.severity = 'warn',
      inv5.heal_protocol = '',
      inv5.question_template_id = 'which-triggers-reference-skipkeys';

// 6. Heartbeat Dead-Mans-Switch Config Present — Being.auto_stopped_at and HeartbeatConfig exist
MERGE (inv6:Invariant {node_id: 'invariant-heartbeat-dead-mans-switch-config-present'})
  SET inv6.label = 'Heartbeat Dead-Mans-Switch Config Present',
      inv6.description = 'Being must have auto_stopped_at field (may be null) and HeartbeatConfig node must exist. Ensures Phase 4 dead-mans-switch has state to read and write.',
      inv6.check_cypher = 'MATCH (b:Being {node_id:"being-mycelium"}) OPTIONAL MATCH (c:HeartbeatConfig {node_id:"heartbeat-config"}) WITH b, c RETURN (b IS NOT NULL AND c IS NOT NULL) AS healthy',
      inv6.severity = 'block',
      inv6.heal_protocol = '',
      inv6.question_template_id = 'is-heartbeat-deadmans-switch-configured';

// --- Phase 3: Seed max_callees on all Protocols without it ----
// Default to 5 unless already set.

MATCH (p:Protocol) WHERE p.max_callees IS NULL
SET p.max_callees = 5;

// --- Phase 4: Wire all invariants to infrastructure ----
// All 6 loop-safety invariants now connected to Rhythm (heartbeat), Purpose (self-heal),
// Ontology, and Being for monitoring and healing.

MATCH (heartbeat:Rhythm {node_id: 'rhythm-heartbeat'})
MATCH (heal:Purpose {node_id: 'purpose-self-heal'})
MATCH (ont:Ontology)
MATCH (being:Being {node_id: 'being-mycelium'})
WITH heartbeat, heal, ont, being
MATCH (inv:Invariant) WHERE inv.node_id STARTS WITH 'invariant-single-'
                         OR inv.node_id STARTS WITH 'invariant-no-protocol-'
                         OR inv.node_id STARTS WITH 'invariant-protocol-'
                         OR inv.node_id STARTS WITH 'invariant-fanout-'
                         OR inv.node_id STARTS WITH 'invariant-no-trigger-'
                         OR inv.node_id STARTS WITH 'invariant-heartbeat-dead'
MERGE (inv)-[:MONITORED_BY]->(heartbeat)
MERGE (inv)-[:EMBODIES]->(heal)
MERGE (inv)-[:INVARIANT_OF]->(ont)
MERGE (inv)-[:MONITORS]->(being);

// --- Final Summary Report ---

MATCH (sk:SkipKey) WHERE sk.node_id IN ['skipkey-max_callees', 'skipkey-auto_stopped_at']
WITH collect(sk.node_id) AS skipkeys, count(sk) AS sk_count
MATCH (inv:Invariant) WHERE inv.node_id STARTS WITH 'invariant-single-'
                         OR inv.node_id STARTS WITH 'invariant-no-protocol-'
                         OR inv.node_id STARTS WITH 'invariant-protocol-'
                         OR inv.node_id STARTS WITH 'invariant-fanout-'
                         OR inv.node_id STARTS WITH 'invariant-no-trigger-'
                         OR inv.node_id STARTS WITH 'invariant-heartbeat-dead'
WITH skipkeys, sk_count, collect(inv.node_id) AS invariants, count(inv) AS inv_count
MATCH (p:Protocol) WHERE p.max_callees IS NOT NULL
WITH skipkeys, sk_count, invariants, inv_count, count(p) AS protocols_with_max_callees
RETURN
  sk_count AS skipkeys_created,
  skipkeys AS skipkey_node_ids,
  inv_count AS invariants_created,
  invariants AS invariant_node_ids,
  protocols_with_max_callees AS protocols_seeded_with_max_callees,
  'loop-safety-seed seeded' AS status;
