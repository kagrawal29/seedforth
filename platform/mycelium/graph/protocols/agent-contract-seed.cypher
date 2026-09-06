// @kind: seed
// ============================================================================
// Protocol: Agent Contract Seed
// ============================================================================
// Seeds the :Guide node that every subagent MUST read (via mycelium ask)
// before doing any work. The contract lives in the graph, not in a file,
// so agents discover it through natural language - which itself deposits
// a :Prompt with embedding + words, growing the vocabulary layer just by
// being followed.
//
// Dispatch template rule: every agent prompt must begin with:
//   1. ./mycelium ask "what is the mycelium agent contract"
//   2. ./mycelium ask "how do agents use mycelium shell"
//   3. ./mycelium ask "what traces should my work leave"
//
// Those three asks seed the vocabulary layer with contract-aware prompts,
// give the agent graph-native context, and prove the graph can answer
// questions about its own norms. If it can't, that IS the signal that the
// contract needs to be densified further.
// ============================================================================


MERGE (g:Guide {node_id: 'guide-agent-contract'})
SET g.name = 'Agent Contract',
    g.category = 'collaboration',
    g.description = 'The rules every mycelium subagent must follow. All cypher goes through mycelium shell (never docker exec). All natural language discovery goes through mycelium ask so the vocabulary layer grows from your work. Verify traces at the end. Commit what you build, dont hand-edit graph-state.',
    g.contract_text = 'If you are a subagent working inside mycelium, follow these rules strictly. ONE: all cypher execution must go through ./mycelium shell. Never call docker exec cypher-shell directly. The wrapper emits a :QueryTrace node so the graph sees your work - bypassing it makes you invisible. TWO: discover the graph through ./mycelium ask in natural language. Every ask deposits a :Prompt node with embedding, :Word linkages, and :BIGRAM edges, growing the vocabulary layer as a side effect of your exploration. Minimum three asks per task: one about the domain, one about the existing protocols, one about expected edges. THREE: before dispatching work, check if a :Skill or :Protocol already exists via ./mycelium ask - do not re-author what the graph already knows. FOUR: prefer cypher-native execution (atom-run) over LLM authoring when a matching Skill exists - amortization is a first-class design goal. FIVE: verify your traces at the end with MATCH (qt:QueryTrace) WHERE qt.invoked_by=mycelium-shell AND qt.invoked_epoch_ms >= timestamp() - 3600000 RETURN count. Must be > 0. SIX: commit only your own files. Do not stage changes you did not make. SEVEN: when you encounter a vocabulary gap - a question the graph cannot answer well - raise it as a :Question node instead of papering over it. The graph asks for what it needs.',
    g.example = 'MATCH (g:Guide {node_id: "guide-agent-contract"}) RETURN g.contract_text',
    g.order = 100,
    g.file_type = 'guide';


// --- Dense wiring: the contract concerns multiple subsystems ---------------

MATCH (g:Guide {node_id: 'guide-agent-contract'}),
      (o:Ontology {node_id: 'ontology-mycelium'})
MERGE (g)-[:DOCUMENTS_IN]->(o);

MATCH (g:Guide {node_id: 'guide-agent-contract'}),
      (c:Concept {node_id: 'concept-subagent'})
MERGE (g)-[:GOVERNS]->(c);

MATCH (g:Guide {node_id: 'guide-agent-contract'}),
      (c:Command {name: 'shell'})
MERGE (g)-[:REFERENCES]->(c);

MATCH (g:Guide {node_id: 'guide-agent-contract'}),
      (c:Command {name: 'ask'})
MERGE (g)-[:REFERENCES]->(c);

MATCH (g:Guide {node_id: 'guide-agent-contract'}),
      (i:Invariant)
WHERE i.node_id CONTAINS 'trace' OR i.node_id CONTAINS 'cli'
MERGE (g)-[:ENFORCED_BY]->(i);


// --- A Question the graph raises when agent traces drop ---

MERGE (q:Question {node_id: 'question-009-agent-contract-violation'})
SET q.text = 'Subagent activity detected without mycelium-shell traces. At least one agent bypassed the CLI. Backfill retroactive traces, review contract compliance, or escalate?',
    q.options = ['backfill', 'review', 'escalate'],
    q.default_option = 'review',
    q.severity = 'warn',
    q.status = 'pending',
    q.raised_at = toString(datetime()),
    q.raised_by_kind = 'contract-monitor',
    q.file_type = 'question';

MATCH (q:Question {node_id: 'question-009-agent-contract-violation'}),
      (g:Guide {node_id: 'guide-agent-contract'})
MERGE (q)-[:CONCERNS]->(g);

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (q:Question {node_id: 'question-009-agent-contract-violation'})
MERGE (q)-[:QUESTION_OF]->(o);


// --- Summary -------------------------------------------------------------

MATCH (g:Guide {node_id: 'guide-agent-contract'})
OPTIONAL MATCH (g)-[r]->(x)
RETURN g.node_id, count(r) AS edges,
       collect(DISTINCT type(r)) AS edge_types,
       'agent contract seeded, graph will watch compliance' AS status;
