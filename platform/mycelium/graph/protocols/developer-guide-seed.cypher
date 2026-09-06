// @kind: seed
// ============================================================================
// Protocol: Developer Guide Seed
// ============================================================================
// Seeds the developer-facing :Guide nodes specifically about integrating
// external workflows, skills, and systems with mycelium. These appear in
// `mycelium docs` under the "Developer Integration" section.
//
// Companion to docs-seed.cypher (operator guides) and subsystems-seed.cypher
// (the data model for subsystems, metaphors, integration points).
// ============================================================================

MERGE (g:Guide {node_id: 'devguide-01-mental-model'})
SET g.name = 'Dev Mental Model — Code is a Runtime for the Graph',
    g.category = 'developer',
    g.order = 100,
    g.description = 'The one idea you need before writing anything that touches mycelium.',
    g.steps = [
      'Mycelium is NOT a library you import into your code. It is a GRAPH MODEL of a system. Your code either mutates the graph or reads from it.',
      'You keep writing Python, TypeScript, shell, whatever — mycelium does not replace your tools. It replaces your DOCUMENTATION and your CONFIGURATION and your PLAN.',
      'Every operation your system performs should have a matching :CypherAtom in the graph. The atom describes WHAT the operation does semantically; your code IS one implementation of that atom.',
      'Multiple implementations of the same atom are allowed. A Python function, a shell script, and a pure-cypher protocol can all implement the same IntegrationPoint — the graph is the source of truth for what the operation means.',
      'Before you add a new behavior: first model it in the graph (an atom, a protocol, a concept). Then write the code. Then link the code to the atom via an :ExternalCode node.'
    ],
    g.file_type = 'guide';

MERGE (g:Guide {node_id: 'devguide-02-integrate-workflow'})
SET g.name = 'Integrate a Workflow',
    g.category = 'developer',
    g.order = 101,
    g.description = 'Add a new external workflow to mycelium in 6 steps.',
    g.steps = [
      'STEP 1: Describe the workflow in the graph. MERGE a :Subsystem node with name, description, primary_language, entry_point, external_repo. This is the "cell membrane" — everything else hangs off this.',
      'STEP 2: Identify the operations. For each meaningful thing your workflow does — ingest data, make a decision, emit a signal — MERGE a :CypherAtom with semantic = "what it does in plain English" and category = filter|compute|write|aggregate|branch|terminator.',
      'STEP 3: Wire the atoms. Use :FEEDS {var} edges when one atom produces a value the next consumes, or :FOLLOWS for pure ordering. This makes your workflow walkable from the outside.',
      'STEP 4: Register your code files. For every file your workflow lives in, MERGE an :ExternalCode node with file_path, language, purpose, and interfaces_with = <your subsystem node_id>. Link via :IMPLEMENTS → :Subsystem.',
      'STEP 5: Define the boundaries. For each place your workflow talks to the graph (inbound or outbound), MERGE an :IntegrationPoint node with direction, operation, trigger, and semantic. This is your public API.',
      'STEP 6: Add tests and invariants. At minimum: one :TestCase that asserts your workflow produced the expected outcome, and one :Invariant if there is a rule that must hold. If the invariant can auto-heal, set heal_protocol so the immune system catches drift.'
    ],
    g.file_type = 'guide';

MERGE (g:Guide {node_id: 'devguide-03-write-a-protocol'})
SET g.name = 'Write a Protocol',
    g.category = 'developer',
    g.order = 102,
    g.description = 'The anatomy of a cypher protocol that other developers can trust.',
    g.steps = [
      'File location: graph/protocols/<name>.cypher. Atomizer will auto-decompose semicolon-terminated statements.',
      'Header comment: name, purpose, why, idempotency guarantees, dependencies (which APOC procedures you need).',
      'Inputs as parameters: use $param_name and coalesce($param, default_value) for safe defaults. Makes the protocol invokable via --param JSON.',
      'Idempotency is mandatory. MERGE not CREATE. ON CREATE SET for first-time defaults, ON MATCH SET for updates. Re-running twice in a row must be a no-op.',
      'Determinism matters. If you compute a hash or set a leaf_hash, make sure your SET runs on a materialized view (collect → UNWIND → SET), not on a lazy MATCH. See the merkle-properties two-pass pattern.',
      'Return a meaningful status row. Downstream runners parse it for pass/fail. Always finish with RETURN (a status string at minimum).',
      'Add invariants and tests alongside. A protocol without an invariant is trust-on-faith. Seed them in the same migration where you add the protocol.',
      'Register as a :Protocol node when you commit (or let the atomizer auto-register). Include cadence, protocol_type, file_path, file_sha256.'
    ],
    g.file_type = 'guide';

MERGE (g:Guide {node_id: 'devguide-04-write-external-code'})
SET g.name = 'Write External Code (Python/Shell/Whatever)',
    g.category = 'developer',
    g.order = 103,
    g.description = 'When cypher cannot do it alone.',
    g.steps = [
      'Rule: write external code ONLY for things cypher cannot express. Right now that is crypto (ed25519), HTTP to Ollama, file parsing, anything crossing the graph<->filesystem boundary.',
      'Keep each external file minimal (ideally ≤150 lines). If it grows, you are probably doing logic that should live in cypher atoms.',
      'Every external file gets an :ExternalCode node with file_path, language, purpose, and :IMPLEMENTS → :Subsystem.',
      'Every external file should have a matching :CypherAtom or :Protocol node describing what it does semantically, even if the implementation is imperative. The atom is the contract; the code is one fulfillment.',
      'Communicate via Neo4j as much as possible. The Python sidecars read/write the graph; they do not pass data between each other over files or env vars.',
      'Stderr for human messages, stdout for data. Exit 0 = success, non-zero = failure with a descriptive line. Runners parse both.',
      'Put the file under graph/runner/ if it is a boundary-crosser. Put it under scripts/ (legacy path) only if you are maintaining frozen code.'
    ],
    g.file_type = 'guide';

MERGE (g:Guide {node_id: 'devguide-05-add-command'})
SET g.name = 'Add a CLI Command',
    g.category = 'developer',
    g.order = 104,
    g.description = 'Make your workflow invokable via `mycelium <name>`.',
    g.steps = [
      'Add a :Command node via a MERGE: node_id cmd-<name>, name = <name>, category, usage, description, example, runner.',
      'runner can be "mycelium__builtin_<fn>" (and you implement cmd_<fn> in the mycelium bash file) OR the full shell command to exec (like "bash graph/runner/foo.sh").',
      'Your command is now listed in `mycelium help` automatically — the CLI reads :Command nodes at runtime.',
      'Every invocation of your command is traced: the EXIT trap emits a :QueryTrace + updates the :Query node by cypher hash. Fire-together wiring happens for free.',
      'If your command runs a cypher protocol, prefer invoking it via atom-run.sh so atoms get fire_count increments — gives the graph learning signal about which code paths are used.',
      'Document it: MERGE a :Guide or :Concept node explaining the command if its behavior is non-obvious. It will show up in `mycelium docs`.'
    ],
    g.file_type = 'guide';

MERGE (g:Guide {node_id: 'devguide-06-best-practices'})
SET g.name = 'Best Practices',
    g.category = 'developer',
    g.order = 105,
    g.description = 'Learned-the-hard-way rules that keep the graph healthy.',
    g.steps = [
      'NEVER store derived state in content properties. Put it in SkipKey so leaf_hash is stable. If you forget, root_hash drifts every time the derived value updates.',
      'NEVER match by node_id without a label filter for MERGE or WRITE operations. Multi-label collisions (the embed-dirty bug) will silently overwrite the wrong nodes. Always MATCH (n:Label {node_id: ...}) or use elementId().',
      'NEVER commit cypher with non-deterministic ordering. Sort your collect()s. apoc.coll.sort is your friend.',
      'ALWAYS put new properties with high churn (counters, timestamps, health flags) in SkipKey BEFORE you start writing them. Otherwise the first run drifts root_hash and you have to fix it retroactively.',
      'ALWAYS add a test for a new protocol. A :TestCase with assertion_cypher that returns a boolean. Without a test, the protocol is not trusted.',
      'ALWAYS make new invariants auto-healable when possible. Set heal_protocol even if the heal is just "log and alert". The immune system is how the graph stays healthy without you.',
      'Prefer WITH boundaries over multi-statement scripts when variables need to thread. Use apoc.cypher.run when you need dynamic cypher (e.g. invariant check_cypher). Avoid stored procedures written in Java.',
      'Treat the graph as the spec. If you wrote code that is not reflected in the graph, someone else will not be able to trust it — including your future self.'
    ],
    g.file_type = 'guide';

MERGE (g:Guide {node_id: 'devguide-07-troubleshoot'})
SET g.name = 'Troubleshooting',
    g.category = 'developer',
    g.order = 106,
    g.description = 'What to check when something is wrong.',
    g.steps = [
      'Invariant unhealthy? Run ./mycelium verify — it lists the failing invariant and the actual vs expected values. Follow the check_cypher manually to see what it returns.',
      'Merkle root drifting across runs with no mutation? Check which properties are drifting: compare leaf_hashes before and after. Any property that changes between runs and is not in SkipKey is the culprit.',
      'Test failing after an upgrade? The test might be legacy-structural (e.g. test-zero-degree-querytrace). Check its deferred_reason if it exists, otherwise mark it enabled=false with a categorized deferred_reason + note.',
      'Embedding-coverage unhealthy? Run ./mycelium embed — re-runs embed-dirty for nodes where leaf_hash != embedding_for_leaf_hash. Should drop dirty count to 0. If not, there is a multi-label node_id collision (elementId bug).',
      'Species mint creating duplicates? Check if merkle chain-layer exclusion is working — species/witness/witness-signature should be excluded from leaf_hash, otherwise every mint drifts root which cascades into another mint.',
      'CI PR failing on validate-merge? The PR comment names the failing invariant or test. Fix locally (graph/runner/validate-merge.sh pr/<file>.cypher), push the fix, re-run CI.',
      'Graph feels slow? Check ./mycelium report hottest — see which atoms/queries are firing most. Heavy paths are candidates for caching, indexing, or atom-level optimization.',
      'Tracing gaps? ./mycelium watching shows last 10s of QueryTraces. If your new command is not showing up, check that the mycelium CLI sources trace.sh and has the EXIT trap — both are required for auto-tracing.'
    ],
    g.file_type = 'guide';


// --- Link these guides to the ontology hub so they are not orphans ---------
MATCH (g:Guide) WHERE g.category = 'developer'
MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MERGE (g)-[:DOCUMENTS_IN]->(o);

RETURN count(*) AS developer_guides_seeded;
