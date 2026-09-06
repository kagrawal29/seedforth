// @kind: seed
// ============================================================================
// Protocol: Missing Schemas Seed
// ============================================================================
// Closes three density gaps surfaced by the Question layer:
//
//   :Credential  - one node for the Neo4j password config, so
//                  question-001-password-default can CONCERNS it.
//   :Subagent    - one node per parallel agent dispatched this session,
//                  with real model/token/cost/duration/authored data, so
//                  question-007-subagent-cost-tracking can CONCERNS them
//                  and the cost layer becomes graph-native immediately.
//   :GitHook     - minimal nodes for pre-commit hooks we need, so
//                  question-008-graph-state-prehook can CONCERNS them.
//
// Plus retroactive edges:
//   - Each Subagent :AUTHORED its protocols (real provenance for cost
//     amortization math: cost / fire_count of authored protocols)
//   - Each Subagent :USED_MODEL a :Model node (new label, captures
//     pricing tier so mycelium cost can roll up by model)
//   - Questions 001/007/008 gain CONCERNS edges to the new nodes
//   - Subagents -[:PART_OF]-> ontology-mycelium
//
// The cost layer lives in the graph from now on - no separate feature,
// just the natural density completion of what was already implied.
//
// Idempotent (MERGE only). Safe to re-run.
// ============================================================================


// --- Part 1: :Model nodes (pricing tiers) ---------------------------------

MERGE (m:Model {node_id: 'model-claude-haiku-4-5'})
SET m.name = 'Claude Haiku 4.5',
    m.model_id = 'claude-haiku-4-5',
    m.vendor = 'Anthropic',
    m.input_price_per_1m = 1.0,
    m.output_price_per_1m = 5.0,
    m.blended_rate_per_1m = 2.0,
    m.tier = 'fast',
    m.description = 'Small fast model. Good for focused cypher-native tasks with short context.',
    m.file_type = 'model';

MERGE (m:Model {node_id: 'model-claude-sonnet-4-5'})
SET m.name = 'Claude Sonnet 4.5',
    m.model_id = 'claude-sonnet-4-5',
    m.vendor = 'Anthropic',
    m.input_price_per_1m = 3.0,
    m.output_price_per_1m = 15.0,
    m.blended_rate_per_1m = 6.0,
    m.tier = 'balanced',
    m.description = 'Mid-tier model. Good for design-heavy cypher authoring and multi-step reasoning.',
    m.file_type = 'model';

MERGE (m:Model {node_id: 'model-claude-opus-4-6'})
SET m.name = 'Claude Opus 4.6',
    m.model_id = 'claude-opus-4-6',
    m.vendor = 'Anthropic',
    m.input_price_per_1m = 15.0,
    m.output_price_per_1m = 75.0,
    m.blended_rate_per_1m = 30.0,
    m.tier = 'deep',
    m.description = 'Top-tier model. Reserved for architectural reasoning and open-ended research.',
    m.file_type = 'model';


// --- Part 2: :Subagent nodes (real session data) --------------------------

MERGE (sa:Subagent {node_id: 'subagent-edge-connectives-2026-04-16'})
SET sa.name = 'Unused Edge Type Harvester',
    sa.role = 'cypher-native-author',
    sa.model_id = 'claude-haiku-4-5',
    sa.total_tokens = 62832,
    sa.tool_uses = 13,
    sa.duration_ms = 97987,
    sa.cost_usd = 0.126,
    sa.dispatched_at = '2026-04-16T05:30:00Z',
    sa.authored_files = ['graph/protocols/edge-connectives-expand.cypher'],
    sa.dispatched_by = 'mycelium-cli-session',
    sa.file_type = 'subagent';

MERGE (sa:Subagent {node_id: 'subagent-community-coherence-2026-04-16'})
SET sa.name = 'Community Coherence Scorer',
    sa.role = 'cypher-native-author',
    sa.model_id = 'claude-haiku-4-5',
    sa.total_tokens = 61563,
    sa.tool_uses = 24,
    sa.duration_ms = 100963,
    sa.cost_usd = 0.123,
    sa.dispatched_at = '2026-04-16T05:30:00Z',
    sa.authored_files = ['graph/protocols/community-coherence.cypher'],
    sa.dispatched_by = 'mycelium-cli-session',
    sa.file_type = 'subagent';

MERGE (sa:Subagent {node_id: 'subagent-metaphor-densify-2026-04-16'})
SET sa.name = 'Metaphor Densification Protocol',
    sa.role = 'cypher-native-author',
    sa.model_id = 'claude-sonnet-4-5',
    sa.total_tokens = 47748,
    sa.tool_uses = 35,
    sa.duration_ms = 288177,
    sa.cost_usd = 0.286,
    sa.dispatched_at = '2026-04-16T05:30:00Z',
    sa.authored_files = ['graph/protocols/metaphor-densify.cypher'],
    sa.dispatched_by = 'mycelium-cli-session',
    sa.file_type = 'subagent';

MERGE (sa:Subagent {node_id: 'subagent-commands-wire-2026-04-16'})
SET sa.name = 'Commands Wire + Multi-Angle Explanations',
    sa.role = 'cypher-native-author',
    sa.model_id = 'claude-sonnet-4-5',
    sa.total_tokens = 40030,
    sa.tool_uses = 21,
    sa.duration_ms = 117093,
    sa.cost_usd = 0.240,
    sa.dispatched_at = '2026-04-16T05:40:00Z',
    sa.authored_files = ['graph/protocols/commands-wire.cypher'],
    sa.dispatched_by = 'mycelium-cli-session',
    sa.file_type = 'subagent';

MERGE (sa:Subagent {node_id: 'subagent-verbalize-lineage-2026-04-16'})
SET sa.name = 'Path-Verbalization Protocol',
    sa.role = 'cypher-native-author',
    sa.model_id = 'claude-sonnet-4-5',
    sa.total_tokens = 94219,
    sa.tool_uses = 64,
    sa.duration_ms = 706871,
    sa.cost_usd = 0.565,
    sa.dispatched_at = '2026-04-16T05:30:00Z',
    sa.authored_files = ['graph/protocols/verbalize-lineage.cypher'],
    sa.dispatched_by = 'mycelium-cli-session',
    sa.file_type = 'subagent';


// --- Part 3: :Credential nodes --------------------------------------------

MERGE (cr:Credential {node_id: 'credential-neo4j-local'})
SET cr.purpose = 'Neo4j bolt protocol auth for the local mycelium graph container.',
    cr.container = 'mycelium-neo4j-local',
    cr.port = 7687,
    cr.install_default = true,
    cr.default_value_hash = 'sha256:7aa41fc5...',
    cr.rotated_at = null,
    cr.source_file_target = 'graph/auth.env',
    cr.description = 'The password the CLI uses to talk to Neo4j. Must be rotated on first install - the default value is shared across all developer machines and would let any bypass-CLI caller in.',
    cr.file_type = 'credential';


// --- Part 4: :GitHook nodes -----------------------------------------------

MERGE (gh:GitHook {node_id: 'githook-pre-commit-export-state'})
SET gh.hook_type = 'pre-commit',
    gh.target_file = '.git/hooks/pre-commit',
    gh.action = 'Run graph/runner/export-graph-state.sh if any graph/protocols/*.cypher file changed',
    gh.status = 'not-installed',
    gh.description = 'Prevents graph-state.cypher drift. When a protocol file is staged for commit, the exporter runs and the updated graph-state.cypher is added to the same commit.',
    gh.file_type = 'git-hook';

MERGE (gh:GitHook {node_id: 'githook-pre-commit-atomize-protocols'})
SET gh.hook_type = 'pre-commit',
    gh.target_file = '.git/hooks/pre-commit',
    gh.action = 'Run graph/runner/atomize-protocol.py on any staged graph/protocols/*.cypher file',
    gh.status = 'not-installed',
    gh.description = 'Ensures the :CypherAtom decomposition stays in sync with the .cypher file. Every protocol change produces updated atoms automatically.',
    gh.file_type = 'git-hook';


// --- Part 5: Dense wiring -------------------------------------------------

// Subagents -> Model
MATCH (sa:Subagent), (m:Model)
WHERE sa.model_id = m.model_id
MERGE (sa)-[:USED_MODEL]->(m);

// Subagents -> authored :Protocol (derived from authored_files)
// For each subagent, find the :Protocol node whose source_file matches.
MATCH (sa:Subagent)
UNWIND sa.authored_files AS fpath
MATCH (p:Protocol)
WHERE p.source_file = fpath
MERGE (sa)-[:AUTHORED]->(p);

// Also link subagents to any :CypherAtom whose source_protocol was
// authored by them (finer-grained provenance).
MATCH (sa:Subagent)-[:AUTHORED]->(p:Protocol)
MATCH (a:CypherAtom {source_protocol: p.node_id})
MERGE (sa)-[:AUTHORED_ATOM]->(a);


// Retroactive CONCERNS edges for the sparse questions

// question-001-password-default -> :Credential
MATCH (q:Question {node_id: 'question-001-password-default'}),
      (cr:Credential {node_id: 'credential-neo4j-local'})
MERGE (q)-[:CONCERNS]->(cr);

// question-007-subagent-cost-tracking -> all :Subagent nodes
MATCH (q:Question {node_id: 'question-007-subagent-cost-tracking'}),
      (sa:Subagent)
MERGE (q)-[:CONCERNS]->(sa);

// question-008-graph-state-prehook -> :GitHook nodes
MATCH (q:Question {node_id: 'question-008-graph-state-prehook'}),
      (gh:GitHook)
MERGE (q)-[:CONCERNS]->(gh);


// --- Part 6: Ontology linkage (no orphans) --------------------------------

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (m:Model) MERGE (m)-[:MODEL_OF]->(o);

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (sa:Subagent) MERGE (sa)-[:SUBAGENT_OF]->(o);

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (cr:Credential) MERGE (cr)-[:CREDENTIAL_OF]->(o);

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (gh:GitHook) MERGE (gh)-[:GITHOOK_OF]->(o);


// --- Part 7: Concept definitions so the docs layer covers the new types --

MERGE (c:Concept {node_id: 'concept-subagent'})
SET c.name = 'Subagent',
    c.order = 30,
    c.category = 'collaboration',
    c.description = 'An autonomous LLM-backed agent dispatched to author cypher protocols. Carries model, token counts, cost, duration, and AUTHORED edges to the protocols and atoms it produced. Every subagent invocation is first-class in the graph so mycelium cost can roll up spend by protocol, by model, by session. Cost/fire_count gives amortization per protocol use.',
    c.example = 'MATCH (sa:Subagent)-[:AUTHORED]->(p:Protocol) RETURN sa.name, sa.cost_usd, p.node_id ORDER BY sa.cost_usd DESC',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-model'})
SET c.name = 'Model',
    c.order = 31,
    c.category = 'collaboration',
    c.description = 'A language model tier with pricing. Subagents USED_MODEL a Model node. Roll-ups by model tell you how much Sonnet vs Haiku vs Opus cost across the session.',
    c.example = 'MATCH (sa:Subagent)-[:USED_MODEL]->(m:Model) RETURN m.name, sum(sa.cost_usd) AS spent, sum(sa.total_tokens) AS tokens',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-credential'})
SET c.name = 'Credential',
    c.order = 32,
    c.category = 'security',
    c.description = 'Auth material used to talk to an external system (Neo4j, Ollama, etc). Carries install_default flag, rotated_at, and source_file_target. Questions CONCERNS a Credential when rotation is required.',
    c.example = 'MATCH (cr:Credential) WHERE cr.install_default = true RETURN cr.node_id AS needs_rotation',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-githook'})
SET c.name = 'GitHook',
    c.order = 33,
    c.category = 'infrastructure',
    c.description = 'A git hook declaration. Carries hook_type, target_file, action, status. Install-time scaffolding creates the actual hook file from the graph row so hooks are reproducible across clones.',
    c.example = 'MATCH (gh:GitHook) RETURN gh.node_id, gh.hook_type, gh.status',
    c.file_type = 'concept';

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (c:Concept) WHERE c.node_id IN ['concept-subagent', 'concept-model', 'concept-credential', 'concept-githook']
MERGE (c)-[:DESCRIBES_IN]->(o);


// --- Summary -------------------------------------------------------------

MATCH (sa:Subagent) WITH count(sa) AS subagents, sum(sa.cost_usd) AS total_cost, sum(sa.total_tokens) AS total_tokens
MATCH (m:Model) WITH subagents, total_cost, total_tokens, count(m) AS models
MATCH (cr:Credential) WITH subagents, total_cost, total_tokens, models, count(cr) AS credentials
MATCH (gh:GitHook) WITH subagents, total_cost, total_tokens, models, credentials, count(gh) AS git_hooks
MATCH (sa:Subagent)-[r:AUTHORED]->(:Protocol)
WITH subagents, total_cost, total_tokens, models, credentials, git_hooks, count(r) AS authored_edges
RETURN subagents, total_cost, total_tokens, models, credentials, git_hooks, authored_edges,
       'density gap closed: subagent/cost layer now graph-native' AS status;
