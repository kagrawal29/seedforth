// @node_id: protocol-fractal-lifecycle-wiring
// @label: "Fractal Lifecycle Wiring"
// ============================================================================
// Protocol: Fractal Lifecycle Wiring
// ============================================================================
// Closes lifecycle edge gaps across key labels. The fractal principle requires
// that every important node type (Concept, Persona, Subsystem, HealthMetric,
// Protocol, Question, Metaphor) has at least 3 of 4 lifecycle edge types:
//   - HEALED_BY: which Protocol heals this broken state?
//   - MONITORED_BY: which Rhythm or HealthMetric watches this?
//   - SERVES or EMBODIED_IN: which Purpose does this serve?
//   - ILLUMINATES: which Metaphor sheds light on this?
//
// Current state (audit):
//   - Concept: has_heal=NO, has_monitor=NO, has_purpose=NO (only ILLUMINATES)
//   - Persona: has_heal=NO, has_monitor=NO, has_purpose=NO
//   - Subsystem: has_heal=NO, has_monitor=NO, has_purpose=NO
//   - HealthMetric: has_heal=NO, has_purpose=NO
//   - Metaphor: has_heal=NO, has_monitor=NO
//   - Protocol: mostly has 0 lifecycle edges
//   - Question: has_monitor=NO, has_purpose=NO
//
// This protocol wires:
// 1. All Concepts/Personas/Subsystems HEALED_BY protocol-immune
// 2. All key labels MONITORED_BY rhythm-heartbeat (system-level) or specific HealthMetrics (subsystem-level)
// 3. All labels SERVES purposes based on function (structural, self-heal, learn, dense, speak, etc)
// 4. Metaphors already ILLUMINATE targets; add missing HEALED_BY and MONITORED_BY edges
//
// Idempotent: uses only MERGE, safe to re-run.
// ============================================================================

// === CONCEPTS: Wire HEALED_BY ===
// Most Concepts are architectural questions; protocol-immune handles them
MATCH (c:Concept), (proto:Protocol {node_id: 'protocol-immune'})
MERGE (c)-[:HEALED_BY]->(proto);

// === CONCEPTS: Wire MONITORED_BY ===
// System-level monitoring: rhythm-heartbeat
MATCH (c:Concept), (rhythm:Rhythm {node_id: 'rhythm-heartbeat'})
MERGE (c)-[:MONITORED_BY]->(rhythm);

// === CONCEPTS: Wire SERVES ===
// Different Concepts serve different Purposes based on function
// Concepts about understanding and design --> purpose-speak-about-itself
MATCH (c:Concept {node_id: 'concept-concept'}), (p:Purpose {node_id: 'purpose-speak-about-itself'})
MERGE (c)-[:SERVES]->(p);

MATCH (c:Concept {node_id: 'concept-question'}), (p:Purpose {node_id: 'purpose-speak-about-itself'})
MERGE (c)-[:SERVES]->(p);

MATCH (c:Concept {node_id: 'concept-being'}), (p:Purpose {node_id: 'purpose-structural-integrity-verification'})
MERGE (c)-[:SERVES]->(p);

// Concepts about healing and health --> purpose-self-heal
MATCH (c:Concept) WHERE c.node_id CONTAINS 'heal'
WITH c, c AS _c
MATCH (p:Purpose {node_id: 'purpose-self-heal'})
MERGE (c)-[:SERVES]->(p);

// Concepts about learning and growth --> purpose-learn-from-use
MATCH (c:Concept) WHERE c.node_id CONTAINS 'learn' OR c.node_id CONTAINS 'growth'
WITH c, c AS _c
MATCH (p:Purpose {node_id: 'purpose-learn-from-use'})
MERGE (c)-[:SERVES]->(p);

// Catch-all: other concepts serve structural-integrity-verification
MATCH (c:Concept)
OPTIONAL MATCH (c)-[:SERVES]->(existing:Purpose)
WITH c, count(existing) as has_serves
WHERE has_serves = 0
MATCH (p:Purpose {node_id: 'purpose-structural-integrity-verification'})
MERGE (c)-[:SERVES]->(p);

// === PERSONAS: Wire HEALED_BY ===
MATCH (per:Persona), (proto:Protocol {node_id: 'protocol-immune'})
MERGE (per)-[:HEALED_BY]->(proto);

// === PERSONAS: Wire MONITORED_BY ===
// Personas are system roles; monitored by rhythm-heartbeat
MATCH (per:Persona), (rhythm:Rhythm {node_id: 'rhythm-heartbeat'})
MERGE (per)-[:MONITORED_BY]->(rhythm);

// === PERSONAS: Wire SERVES ===
// All Personas serve the purpose of speaking-about-itself (they are agents that narrate/explain)
MATCH (per:Persona), (p:Purpose {node_id: 'purpose-speak-about-itself'})
MERGE (per)-[:SERVES]->(p);

// === SUBSYSTEM: Wire HEALED_BY ===
MATCH (sub:Subsystem), (proto:Protocol {node_id: 'protocol-immune'})
MERGE (sub)-[:HEALED_BY]->(proto);

// === SUBSYSTEM: Wire MONITORED_BY ===
MATCH (sub:Subsystem), (rhythm:Rhythm {node_id: 'rhythm-heartbeat'})
MERGE (sub)-[:MONITORED_BY]->(rhythm);

// === SUBSYSTEM: Wire SERVES ===
MATCH (sub:Subsystem), (p:Purpose {node_id: 'purpose-structural-integrity-verification'})
MERGE (sub)-[:SERVES]->(p);

// === HEALTHMETRIC: Wire HEALED_BY ===
// HealthMetrics inform healing but are not directly healed; wire to protocol-immune for anomaly response
MATCH (hm:HealthMetric), (proto:Protocol {node_id: 'protocol-immune'})
MERGE (hm)-[:HEALED_BY]->(proto);

// === HEALTHMETRIC: Wire SERVES ===
// HealthMetrics serve self-heal and structural-integrity purposes
MATCH (hm:HealthMetric), (p:Purpose {node_id: 'purpose-self-heal'})
MERGE (hm)-[:SERVES]->(p);

MATCH (hm:HealthMetric), (p:Purpose {node_id: 'purpose-structural-integrity-verification'})
MERGE (hm)-[:SERVES]->(p);

// === METAPHOR: Wire HEALED_BY ===
// Metaphors are healed through protocol-immune when the reality they describe breaks
MATCH (m:Metaphor), (proto:Protocol {node_id: 'protocol-immune'})
MERGE (m)-[:HEALED_BY]->(proto);

// === METAPHOR: Wire MONITORED_BY ===
// Metaphors are validated by rhythm-heartbeat (system checks if reality matches metaphor)
MATCH (m:Metaphor), (rhythm:Rhythm {node_id: 'rhythm-heartbeat'})
MERGE (m)-[:MONITORED_BY]->(rhythm);

// === PROTOCOL: Wire HEALED_BY ===
// Protocols that break are healed by protocol-immune (recursive but valid)
MATCH (p:Protocol), (proto:Protocol {node_id: 'protocol-immune'})
WHERE p.node_id <> 'protocol-immune'
MERGE (p)-[:HEALED_BY]->(proto);

// === PROTOCOL: Wire MONITORED_BY ===
// All protocols are monitored by rhythm-heartbeat
MATCH (p:Protocol), (rhythm:Rhythm {node_id: 'rhythm-heartbeat'})
MERGE (p)-[:MONITORED_BY]->(rhythm);

// === PROTOCOL: Wire SERVES ===
// Protocols about safety/immunity --> purpose-self-heal
MATCH (p:Protocol) WHERE p.node_id CONTAINS 'immune' OR p.node_id CONTAINS 'decay' OR p.node_id CONTAINS 'validation'
WITH p
MATCH (purpose:Purpose {node_id: 'purpose-self-heal'})
MERGE (p)-[:SERVES]->(purpose);

// Protocols about learning and execution --> purpose-learn-from-use
MATCH (p:Protocol) WHERE p.node_id CONTAINS 'embed' OR p.node_id CONTAINS 'fire' OR p.node_id CONTAINS 'trace'
WITH p
MATCH (purpose:Purpose {node_id: 'purpose-learn-from-use'})
MERGE (p)-[:SERVES]->(purpose);

// Protocols about structure and merkle --> purpose-structural-integrity-verification
MATCH (p:Protocol) WHERE p.node_id CONTAINS 'merkle' OR p.node_id CONTAINS 'boundary' OR p.node_id CONTAINS 'crystal'
WITH p
MATCH (purpose:Purpose {node_id: 'purpose-structural-integrity-verification'})
MERGE (p)-[:SERVES]->(purpose);

// Catch-all: other protocols serve structural integrity
MATCH (p:Protocol)
OPTIONAL MATCH (p)-[:SERVES]->(existing:Purpose)
WITH p, count(existing) as has_serves
WHERE has_serves = 0
MATCH (purpose:Purpose {node_id: 'purpose-structural-integrity-verification'})
MERGE (p)-[:SERVES]->(purpose);

// === PROTOCOL: Wire ILLUMINATES (for protocols that lack them) ===
// Protocols that illuminate their implementation domain
MATCH (p:Protocol {node_id: 'protocol-immune'}), (m:Metaphor {node_id: 'metaphor-immune'})
MERGE (p)-[:ILLUMINATES]->(m);

MATCH (p:Protocol {node_id: 'protocol-merkle-properties'}), (m:Metaphor {node_id: 'metaphor-dna'})
MERGE (p)-[:ILLUMINATES]->(m);

MATCH (p:Protocol {node_id: 'protocol-crystal-replication'}), (m:Metaphor {node_id: 'metaphor-cell'})
MERGE (p)-[:ILLUMINATES]->(m);

// === QUESTION: Wire HEALED_BY ===
// Questions are raised when things break; healed by protocol-immune addressing the issue
MATCH (q:Question), (proto:Protocol {node_id: 'protocol-immune'})
MERGE (q)-[:HEALED_BY]->(proto);

// === QUESTION: Wire MONITORED_BY ===
// Questions are surfaced by rhythm-heartbeat (system asking "is this OK?")
MATCH (q:Question), (rhythm:Rhythm {node_id: 'rhythm-heartbeat'})
MERGE (q)-[:MONITORED_BY]->(rhythm);

// === QUESTION: Wire SERVES ===
// Questions serve the purpose of speaking-about-itself (they are inquiries into the system)
MATCH (q:Question), (p:Purpose {node_id: 'purpose-speak-about-itself'})
MERGE (q)-[:SERVES]->(p);

// === INVARIANT: Wire HEALED_BY ===
// Invariants that break are healed by protocol-immune
MATCH (i:Invariant), (proto:Protocol {node_id: 'protocol-immune'})
MERGE (i)-[:HEALED_BY]->(proto);

// === INVARIANT: Wire MONITORED_BY ===
// Invariants are monitored by rhythm-heartbeat (system enforces them)
MATCH (i:Invariant), (rhythm:Rhythm {node_id: 'rhythm-heartbeat'})
MERGE (i)-[:MONITORED_BY]->(rhythm);

// === INVARIANT: Wire SERVES ===
// Invariants serve structural-integrity-verification (they are the rules that maintain structure)
MATCH (i:Invariant), (p:Purpose {node_id: 'purpose-structural-integrity-verification'})
MERGE (i)-[:SERVES]->(p);

// === RHYTHM: Wire MONITORED_BY ===
// Rhythms are self-referential: each rhythm monitors itself (e.g., heartbeat checks heartbeat)
MATCH (r:Rhythm {node_id: 'rhythm-heartbeat'})
MERGE (r)-[:MONITORED_BY]->(r);

MATCH (r:Rhythm {node_id: 'rhythm-realtime'})
MERGE (r)-[:MONITORED_BY]->(r);

// === RHYTHM: Wire SERVES ===
// Rhythms serve multiple purposes based on their function
MATCH (r:Rhythm {node_id: 'rhythm-heartbeat'}), (p:Purpose {node_id: 'purpose-structural-integrity-verification'})
MERGE (r)-[:SERVES]->(p);

MATCH (r:Rhythm {node_id: 'rhythm-prompt-ingest'}), (p:Purpose {node_id: 'purpose-learn-from-use'})
MERGE (r)-[:SERVES]->(p);

MATCH (r:Rhythm) WHERE r.node_id CONTAINS 'trace'
WITH r
MATCH (p:Purpose {node_id: 'purpose-learn-from-use'})
MERGE (r)-[:SERVES]->(p);

// === CYPHER_ATOM: Wire HEALED_BY ===
// Atoms (executed cypher) are healed by protocol-immune when they produce wrong results
MATCH (a:CypherAtom), (proto:Protocol {node_id: 'protocol-immune'})
MERGE (a)-[:HEALED_BY]->(proto);

// === CYPHER_ATOM: Wire MONITORED_BY ===
// Atoms are monitored by health metrics and rhythms that track their execution
MATCH (a:CypherAtom), (hm:HealthMetric {node_id: 'hm-atom-liveness'})
MERGE (a)-[:MONITORED_BY]->(hm);

MATCH (a:CypherAtom), (rhythm:Rhythm {node_id: 'rhythm-realtime'})
MERGE (a)-[:MONITORED_BY]->(rhythm);

// === CYPHER_ATOM: Wire SERVES ===
// Atoms serve multiple purposes: learning (they fire and update state) and execution
MATCH (a:CypherAtom), (p:Purpose {node_id: 'purpose-learn-from-use'})
MERGE (a)-[:SERVES]->(p);

MATCH (a:CypherAtom), (p:Purpose {node_id: 'purpose-structural-integrity-verification'})
MERGE (a)-[:SERVES]->(p);

// === WORD: Wire HEALED_BY ===
MATCH (w:Word), (proto:Protocol {node_id: 'protocol-immune'})
MERGE (w)-[:HEALED_BY]->(proto);

// === WORD: Wire MONITORED_BY ===
MATCH (w:Word), (hm:HealthMetric {node_id: 'hm-vocabulary-word-count'})
MERGE (w)-[:MONITORED_BY]->(hm);

// === WORD: Wire SERVES ===
MATCH (w:Word), (p:Purpose {node_id: 'purpose-dense-by-design'})
MERGE (w)-[:SERVES]->(p);

MATCH (w:Word), (p:Purpose {node_id: 'purpose-speak-about-itself'})
MERGE (w)-[:SERVES]->(p);
