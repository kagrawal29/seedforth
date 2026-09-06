// @kind: seed
// ============================================================================
// Protocol: Question Layer Seed
// ============================================================================
// Introduces the :Question layer as a densely-wired graph citizen.
//
// New node types:
//   :QuestionTemplate   reusable pattern. text/options/default/heal_protocol.
//                       Questions are INSTANCE_OF a template.
//   :Question           a live instance the user must answer (or defer).
//   :QuestionSession    a batch answered together by one user.
//   :Answer             the user's response (separate so we can track who,
//                       when, and allow multiple answers over time).
//   :Consent            explicit authorization record for destructive or
//                       costly heals.
//
// New edge types (all densely wired to existing graph):
//   RAISED_BY        Question → Invariant | Protocol | TestCase | Subagent
//   CONCERNS         Question → any node the question is about
//   HEALED_BY        Question → Protocol that fires when authorized
//   BLOCKS           Question → Feature | Workflow | Invariant waiting on it
//   INSTANCE_OF      Question → QuestionTemplate
//   ANSWERED_BY      Question → Answer
//   GRANTED_BY       Consent → Person | Subagent
//   APPLIES_TO       QuestionTemplate → label string (as property, not edge)
//   COSTS            Question → CostEstimate (optional, when heal is priced)
//   PART_OF          Question → QuestionSession
//
// Wiring into existing graph:
//   - Every :Invariant gets a question_template_id property pointing at
//     the QuestionTemplate to instantiate when it fails (instead of just
//     going red).
//   - Every :Protocol with destructive action gets authorization_required
//     = true and a question_template_id.
//   - Real current questions are seeded for known gaps so the layer is
//     populated from first run.
//   - Everything links to :Ontology so no orphans.
//
// The entire question layer lives in the graph. Cross-system reproduction
// = restore graph-state.cypher. No code outside the graph needs to know
// about questions except the thin `mycelium questions` CLI reader/writer.
//
// Idempotent (MERGE only). Safe to re-run.
// ============================================================================


// --- Part 1: Indexes for performance ---------------------------------------

CREATE INDEX question_severity_raised IF NOT EXISTS
  FOR (q:Question) ON (q.severity, q.raised_at);

CREATE INDEX question_template_id IF NOT EXISTS
  FOR (q:QuestionTemplate) ON (q.template_id);


// --- Part 2: QuestionTemplate vocabulary (6 reusable patterns) -------------

MERGE (t:QuestionTemplate {node_id: 'qtpl-password-rotation'})
SET t.template_id = 'password-rotation',
    t.text_pattern = 'Neo4j password is still the install-time default. Rotate to a random 32-char password now?',
    t.options = ['yes', 'no', 'defer'],
    t.default_option = 'defer',
    t.severity = 'warn',
    t.heal_protocol = 'protocol-rotate-neo4j-password',
    t.authorization_required = true,
    t.applies_to_labels = ['Subsystem'],
    t.description = 'Triggered when the install-time default password is still in use. Rotation requires restart so authorization is explicit.',
    t.file_type = 'question-template';

MERGE (t:QuestionTemplate {node_id: 'qtpl-community-rebuild'})
SET t.template_id = 'community-rebuild',
    t.text_pattern = 'semantic_community is {pct}% singleton - label propagation did not converge. Re-run semantic-cluster with more iterations?',
    t.options = ['yes', 'skip', 'tune'],
    t.default_option = 'yes',
    t.severity = 'warn',
    t.heal_protocol = 'protocol-semantic-cluster',
    t.authorization_required = false,
    t.applies_to_labels = ['Invariant'],
    t.description = 'Triggered by community-coherence protocol when >90% of nodes are singleton clusters.',
    t.file_type = 'question-template';

MERGE (t:QuestionTemplate {node_id: 'qtpl-cli-bypass-drift'})
SET t.template_id = 'cli-bypass-drift',
    t.text_pattern = '{n} cypher runs in the last hour produced no QueryTrace. Something is bypassing the CLI. Backfill retroactive traces?',
    t.options = ['yes', 'no', 'investigate'],
    t.default_option = 'investigate',
    t.severity = 'warn',
    t.heal_protocol = 'protocol-backfill-traces',
    t.authorization_required = false,
    t.applies_to_labels = ['Invariant'],
    t.description = 'Triggered by invariant-cli-only-access when trace count trails protocol activity.',
    t.file_type = 'question-template';

MERGE (t:QuestionTemplate {node_id: 'qtpl-missing-connective'})
SET t.template_id = 'missing-connective',
    t.text_pattern = 'New edge type :{edge_type} appeared {n} times but has no EdgeConnective phrase. Suggest {suggested}. Accept?',
    t.options = ['yes', 'edit', 'skip'],
    t.default_option = 'yes',
    t.severity = 'info',
    t.heal_protocol = 'protocol-register-connective',
    t.authorization_required = false,
    t.applies_to_labels = ['EdgeConnective'],
    t.description = 'Triggered when compose-reply encounters an untranslated edge type.',
    t.file_type = 'question-template';

MERGE (t:QuestionTemplate {node_id: 'qtpl-missing-embedding'})
SET t.template_id = 'missing-embedding',
    t.text_pattern = '{n} nodes with leaf_hash drift have no embedding. Re-embed via Ollama (~{sec}s)?',
    t.options = ['yes', 'skip', 'schedule'],
    t.default_option = 'yes',
    t.severity = 'info',
    t.heal_protocol = 'protocol-embed-dirty',
    t.authorization_required = false,
    t.applies_to_labels = ['GraphNode'],
    t.description = 'Triggered when embed-dirty scan finds nodes whose leaf_hash changed since their last embedding.',
    t.file_type = 'question-template';

MERGE (t:QuestionTemplate {node_id: 'qtpl-install-gap'})
SET t.template_id = 'install-gap',
    t.text_pattern = 'Install artifact missing: {artifact}. Without it, a fresh clone cannot boot. Generate default?',
    t.options = ['yes', 'no', 'defer'],
    t.default_option = 'yes',
    t.severity = 'block',
    t.heal_protocol = 'protocol-scaffold-install',
    t.authorization_required = true,
    t.applies_to_labels = ['Subsystem'],
    t.description = 'Triggered by mycelium doctor when docker-compose.yml, install.sh, or Ollama container are missing.',
    t.file_type = 'question-template';


// --- Part 3: Real questions for gaps found this session --------------------
// Each is an INSTANCE_OF a template and CONCERNS the nodes it is about.

MERGE (q:Question {node_id: 'question-001-password-default'})
SET q.text = 'Neo4j password is still the install-time default (localtest12). Rotate to a random 32-char password now?',
    q.options = ['yes', 'no', 'defer'],
    q.default_option = 'defer',
    q.severity = 'warn',
    q.status = 'pending',
    q.raised_at = toString(datetime()),
    q.raised_by_kind = 'audit',
    q.file_type = 'question';

MERGE (q:Question {node_id: 'question-002-community-singleton'})
SET q.text = 'semantic_community is 97% singleton - label propagation did not converge. Re-run semantic-cluster with 10 iterations to build real clusters?',
    q.options = ['yes', 'skip', 'tune'],
    q.default_option = 'yes',
    q.severity = 'warn',
    q.status = 'pending',
    q.raised_at = toString(datetime()),
    q.raised_by_kind = 'community-coherence',
    q.file_type = 'question';

MERGE (q:Question {node_id: 'question-003-cli-bypass-patterns'})
SET q.text = 'Several cypher execution paths bypass the mycelium CLI (embed-dirty.py, atom-run.sh, direct docker exec). Wire them through mycelium shell so every invocation produces a QueryTrace?',
    q.options = ['yes', 'partial', 'no'],
    q.default_option = 'yes',
    q.severity = 'warn',
    q.status = 'pending',
    q.raised_at = toString(datetime()),
    q.raised_by_kind = 'audit',
    q.file_type = 'question';

MERGE (q:Question {node_id: 'question-004-docker-compose-stale'})
SET q.text = 'docker-compose.yml still points at the pre-migration FalkorDB stack. No Neo4j+Ollama compose file exists. A fresh clone cannot boot. Generate docker-compose.yml at repo root?',
    q.options = ['yes', 'no', 'defer'],
    q.default_option = 'yes',
    q.severity = 'block',
    q.status = 'pending',
    q.raised_at = toString(datetime()),
    q.raised_by_kind = 'install-audit',
    q.file_type = 'question';

MERGE (q:Question {node_id: 'question-005-install-script'})
SET q.text = 'No install.sh exists at the repo root. A zero-setup install path is required before distribution. Scaffold install.sh now?',
    q.options = ['yes', 'no', 'defer'],
    q.default_option = 'yes',
    q.severity = 'block',
    q.status = 'pending',
    q.raised_at = toString(datetime()),
    q.raised_by_kind = 'install-audit',
    q.file_type = 'question';

MERGE (q:Question {node_id: 'question-006-mycelium-doctor'})
SET q.text = 'mycelium doctor command does not exist. Users have no way to self-diagnose install health. Scaffold the doctor command now?',
    q.options = ['yes', 'no', 'defer'],
    q.default_option = 'yes',
    q.severity = 'warn',
    q.status = 'pending',
    q.raised_at = toString(datetime()),
    q.raised_by_kind = 'install-audit',
    q.file_type = 'question';

MERGE (q:Question {node_id: 'question-007-subagent-cost-tracking'})
SET q.text = 'Subagent invocations are not tracked in the graph. ~$1.34 spent this session is visible only in ephemeral task-notification messages. Add :SubagentInvocation schema + mycelium cost command?',
    q.options = ['yes', 'no', 'defer'],
    q.default_option = 'yes',
    q.severity = 'warn',
    q.status = 'pending',
    q.raised_at = toString(datetime()),
    q.raised_by_kind = 'audit',
    q.file_type = 'question';

MERGE (q:Question {node_id: 'question-008-graph-state-prehook'})
SET q.text = 'graph-state.cypher drifts from live graph whenever protocols run without a re-export. Add a pre-commit hook that auto-exports on protocol-file changes?',
    q.options = ['yes', 'no', 'defer'],
    q.default_option = 'yes',
    q.severity = 'info',
    q.status = 'pending',
    q.raised_at = toString(datetime()),
    q.raised_by_kind = 'audit',
    q.file_type = 'question';


// --- Part 4: Dense wiring (this is where the graph gets its density) -------

// INSTANCE_OF edges: each question to its template
MATCH (q:Question {node_id: 'question-001-password-default'}),
      (t:QuestionTemplate {template_id: 'password-rotation'})
MERGE (q)-[:INSTANCE_OF]->(t);

MATCH (q:Question {node_id: 'question-002-community-singleton'}),
      (t:QuestionTemplate {template_id: 'community-rebuild'})
MERGE (q)-[:INSTANCE_OF]->(t);

MATCH (q:Question {node_id: 'question-003-cli-bypass-patterns'}),
      (t:QuestionTemplate {template_id: 'cli-bypass-drift'})
MERGE (q)-[:INSTANCE_OF]->(t);

MATCH (q:Question {node_id: 'question-004-docker-compose-stale'}),
      (t:QuestionTemplate {template_id: 'install-gap'})
MERGE (q)-[:INSTANCE_OF]->(t);

MATCH (q:Question {node_id: 'question-005-install-script'}),
      (t:QuestionTemplate {template_id: 'install-gap'})
MERGE (q)-[:INSTANCE_OF]->(t);

MATCH (q:Question {node_id: 'question-006-mycelium-doctor'}),
      (t:QuestionTemplate {template_id: 'install-gap'})
MERGE (q)-[:INSTANCE_OF]->(t);


// CONCERNS edges: each question to the nodes it is actually about
// question-002 concerns the semantic-cluster protocol + every singleton node
MATCH (q:Question {node_id: 'question-002-community-singleton'}),
      (p:Protocol {node_id: 'protocol-semantic-cluster'})
MERGE (q)-[:CONCERNS]->(p);

// question-003 concerns the atom-run runner + the embed-dirty runner
MATCH (q:Question {node_id: 'question-003-cli-bypass-patterns'}),
      (ec:ExternalCode)
WHERE ec.node_id IN ['ec-atom-run', 'ec-embed-dirty', 'ec-export-graph-state']
   OR ec.file_path CONTAINS 'atom-run'
   OR ec.file_path CONTAINS 'embed-dirty'
MERGE (q)-[:CONCERNS]->(ec);

// question-007 concerns every :Subagent node if they exist
MATCH (q:Question {node_id: 'question-007-subagent-cost-tracking'}),
      (sa:Subagent)
MERGE (q)-[:CONCERNS]->(sa);

// question-004/005/006 concern the tetrahedron + mycelium-core subsystems
MATCH (q:Question), (s:Subsystem)
WHERE q.node_id IN ['question-004-docker-compose-stale',
                    'question-005-install-script',
                    'question-006-mycelium-doctor']
  AND s.node_id IN ['subsystem-mycelium-core', 'subsystem-tetrahedron']
MERGE (q)-[:CONCERNS]->(s);


// HEALED_BY edges: each question to the protocol that fires on yes
MATCH (q:Question {node_id: 'question-002-community-singleton'}),
      (p:Protocol {node_id: 'protocol-semantic-cluster'})
MERGE (q)-[:HEALED_BY]->(p);


// BLOCKS edges: questions that block other work
// question-004/005 block any Feature that depends on distribution-readiness
MATCH (q:Question)
WHERE q.node_id IN ['question-004-docker-compose-stale', 'question-005-install-script']
WITH q
MATCH (f:Feature)
WHERE f.status = 'experimental' OR f.status = 'released'
MERGE (q)-[:BLOCKS]->(f);


// RAISED_BY edges: connect each question to the audit Protocol or Invariant
// (For now we link them to the Protocol that would have raised them, if one
// exists. As real invariants get rewritten to raise questions, these edges
// get replaced with more specific RAISED_BY links.)
MATCH (q:Question {node_id: 'question-002-community-singleton'}),
      (p:Protocol {node_id: 'protocol-community-coherence'})
MERGE (q)-[:RAISED_BY]->(p);


// --- Part 5: Wire invariants to raise questions instead of just failing ---
// Add question_template_id property to existing invariants so that when they
// fail, they can instantiate a question instead of just going red.

MATCH (inv:Invariant)
WHERE inv.node_id CONTAINS 'density'
SET inv.question_template_id = 'community-rebuild',
    inv.authorization_required = false;

MATCH (inv:Invariant)
WHERE inv.node_id CONTAINS 'trace' OR inv.node_id CONTAINS 'cli-only'
SET inv.question_template_id = 'cli-bypass-drift',
    inv.authorization_required = false;


// --- Part 6: Ontology linkage (no orphans) ---------------------------------

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (t:QuestionTemplate)
MERGE (t)-[:TEMPLATE_OF]->(o);

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (q:Question)
MERGE (q)-[:QUESTION_OF]->(o);


// --- Part 7: Concept definitions so the docs layer knows about Questions --

MERGE (c:Concept {node_id: 'concept-question'})
SET c.name = 'Question',
    c.order = 28,
    c.category = 'collaboration',
    c.description = 'A first-class graph citizen that represents something the system needs from a human. Raised by invariants, protocols, or tests when a gap is detected. Carries a template, options, severity, heal_protocol, and edges to the nodes it concerns. Answered via mycelium questions. The question layer turns the graph from a reporter into a collaborator - it asks for what it needs instead of just logging gaps.',
    c.example = 'MATCH (q:Question {status: "pending"})-[:CONCERNS]->(target) RETURN q.text, q.severity, target.node_id ORDER BY q.severity DESC',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-question-template'})
SET c.name = 'QuestionTemplate',
    c.order = 29,
    c.category = 'collaboration',
    c.description = 'A reusable pattern for raising a Question. Defines the text pattern (with parameters), options, default, severity, and heal_protocol. Questions INSTANCE_OF a template inherit these and fill in the parameters. Templates let the graph raise consistent, predictable questions across many scenarios without duplicating text.',
    c.example = 'MATCH (t:QuestionTemplate)<-[:INSTANCE_OF]-(q:Question) RETURN t.template_id, count(q) AS uses ORDER BY uses DESC',
    c.file_type = 'concept';

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (c:Concept) WHERE c.category = 'collaboration'
MERGE (c)-[:DESCRIBES_IN]->(o);


// --- Part 8: Register question-raise as a reusable protocol ----------------
// Other protocols will call this via apoc.cypher.doIt or similar to raise
// their own questions. For now, just register the Protocol node.

MERGE (p:Protocol {node_id: 'protocol-question-raise'})
SET p.label = 'Question Raise',
    p.description = 'Reusable cypher that takes $template_id, $params, $raised_by and MERGEs a :Question instance with all required edges. Called by invariants and other protocols when they detect a gap that needs user input.',
    p.source_file = 'graph/protocols/question-raise.cypher',
    p.file_type = 'protocol';

MERGE (p:Protocol {node_id: 'protocol-question-list'})
SET p.label = 'Question List',
    p.description = 'Reads the pending question queue ordered by severity (block > warn > info) and age. Used by mycelium questions and mycelium status.',
    p.source_file = 'graph/protocols/question-list.cypher',
    p.file_type = 'protocol';


// --- Summary ---------------------------------------------------------------

MATCH (t:QuestionTemplate) WITH count(t) AS templates
MATCH (q:Question) WITH templates, count(q) AS questions
MATCH (q:Question)-[r:INSTANCE_OF|CONCERNS|HEALED_BY|BLOCKS|RAISED_BY]->()
WITH templates, questions, count(r) AS question_edges
MATCH (inv:Invariant)
WHERE inv.question_template_id IS NOT NULL
WITH templates, questions, question_edges, count(inv) AS invariants_wired
RETURN templates, questions, question_edges, invariants_wired,
       'question layer seeded + densely wired' AS status;
