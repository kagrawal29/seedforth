// @kind: seed
// ============================================================================
// Protocol: Docs Seed
// ============================================================================
// Seeds :Concept and :Guide nodes that carry the human-readable glossary
// and operator guides. `mycelium docs` queries these plus the live
// Protocol/Invariant/TestCase/Command nodes to generate a complete
// markdown manual on demand.
//
// Mycelium's self-describability principle:
//   "A system that can't explain itself can't be fully trusted."
//   Everything the graph is, does, and requires must be queryable as
//   text from the graph itself, not hardcoded in external documentation.
//
// Idempotent: all MERGEs are keyed on node_id, re-running updates descriptions.
// ============================================================================

// --- Concepts (the vocabulary) ----------------------------------------------

MERGE (c:Concept {node_id: 'concept-being'})
SET c.name = 'Being', c.order = 1, c.category = 'identity',
    c.description = 'The singleton identity anchor for the whole graph. One node (node_id = being-mycelium) that holds the current root_hash, heartbeat counter, chain pointer (CURRENT_SPECIES), and liveness flags. Every query about "where is the graph now?" starts here.',
    c.example = 'MATCH (b:Being) RETURN b.root_hash, b.heartbeat_count',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-species'})
SET c.name = 'Species', c.order = 2, c.category = 'chain',
    c.description = 'A block in the chain. Commits to the state of the graph at the moment it was minted via its manifest_root (sha256 of sorted leaf_hashes of all domain nodes). Species form a parent chain via :DESCENDED_FROM edges. canonical=true marks the current head.',
    c.example = 'MATCH (b:Being)-[:CURRENT_SPECIES]->(s:Species) RETURN s.node_id, s.manifest_root',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-witness'})
SET c.name = 'Witness', c.order = 3, c.category = 'chain',
    c.description = 'A cryptographic validator. Each Witness has an ed25519 public_key registered in the graph; the matching private key stays at ~/.mycelium/witness-<alias>.key outside the graph. Witnesses sign candidate species to promote them to canonical.',
    c.example = 'MATCH (w:Witness) RETURN w.alias, w.public_key',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-witnesssignature'})
SET c.name = 'WitnessSignature', c.order = 4, c.category = 'chain',
    c.description = 'A signed attestation linking a Witness to a Species. Carries the ed25519 signature over (manifest_root || parent_dna || species_node_id). verify-signatures.sh walks these and stamps verified=true; canonize only counts verified signatures.',
    c.example = 'MATCH (ws:WitnessSignature)-[:SIGNS]->(s:Species) RETURN ws.witness_alias, ws.algorithm, ws.verified',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-invariant'})
SET c.name = 'Invariant', c.order = 5, c.category = 'integrity',
    c.description = 'A rule that must always be healthy. Each Invariant has a check_cypher property (run by graph/runner/run-invariants.sh) and can optionally carry a heal_protocol that the immune system fires when the invariant goes unhealthy. The immune loop re-runs the check after heal and logs the outcome.',
    c.example = 'MATCH (i:Invariant) WHERE i.health = "unhealthy" RETURN i.node_id, i.check_cypher, i.heal_protocol',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-testcase'})
SET c.name = 'TestCase', c.order = 6, c.category = 'integrity',
    c.description = 'An assertion that is verified on the graph. Each TestCase carries an assertion_cypher that returns a boolean (or a value compared to expected). run-tests.sh executes every enabled TestCase and sets last_result to pass|fail. Failing tests block validate-merge.',
    c.example = 'MATCH (t:TestCase) WHERE t.last_result = "fail" RETURN t.node_id, t.label, t.actual, t.expected',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-protocol'})
SET c.name = 'Protocol', c.order = 7, c.category = 'behavior',
    c.description = 'A named executable routine. Protocols either hold their cypher inline (for short ones like heartbeat) or reference a .cypher file via file_path + file_sha256. Graph/runner scripts look up Protocol nodes and execute them. Protocols are decomposed into :CypherAtom chains for finer granularity (Phase 15).',
    c.example = 'MATCH (p:Protocol {enabled: true}) RETURN p.node_id, p.protocol_type, p.cadence',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-cypheratom'})
SET c.name = 'CypherAtom', c.order = 8, c.category = 'behavior',
    c.description = 'An atomic unit of cypher, one statement or one clause. Atoms compose into protocols via :FEEDS (variable threading) and :FOLLOWS (sequential) edges. Each atom carries a semantic (natural-language description), fire_count (Hebbian weight), and embedding (semantic search). Scripts become walks through the atom graph.',
    c.example = 'MATCH (p:Protocol)-[:FIRST_ATOM]->(first:CypherAtom) RETURN p.node_id, first.node_id, first.semantic',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-command'})
SET c.name = 'Command', c.order = 9, c.category = 'operator',
    c.description = 'A user-facing CLI action exposed by the `mycelium` binary. Each Command has a name, usage, description, example, and runner. The CLI reads :Command nodes at runtime and dispatches to the registered runner — adding a new command is a single MERGE, no code edit.',
    c.example = 'MATCH (c:Command) RETURN c.name, c.usage, c.description ORDER BY c.category, c.order',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-query'})
SET c.name = 'Query', c.order = 10, c.category = 'learning',
    c.description = 'A cypher query keyed by sha256 of its text. Same cypher = same Query node, with fire_count incremented on every invocation. This is the Hebbian layer: paths that fire together literally ARE the same node, and their strength is fire_count. Query.semantic holds a natural-language description for future NL lookup.',
    c.example = 'MATCH (q:Query) RETURN q.cypher_hash, q.fire_count, q.last_command ORDER BY q.fire_count DESC LIMIT 10',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-querytrace'})
SET c.name = 'QueryTrace', c.order = 11, c.category = 'learning',
    c.description = 'A per-invocation historical record of a Query firing. QueryTrace nodes link to their Query via :INSTANCE_OF and to the touched nodes via touched_ids. mycelium watching reads the last 10 seconds of QueryTraces to show live cognition.',
    c.example = 'MATCH (qt:QueryTrace) WHERE qt.invoked_epoch_ms > timestamp() - 10000 RETURN qt.command, qt.cypher_summary',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-skipkey'})
SET c.name = 'SkipKey', c.order = 12, c.category = 'integrity',
    c.description = 'A property name excluded from the leaf_hash computation. Used to keep Merkle root stable against high-churn, derived, or liveness properties. Categories: merkle-output, liveness, phase1-state, lifecycle, derived-output, chain-verification, immune, execution-telemetry, hebbian, synapse.',
    c.example = 'MATCH (sk:SkipKey) RETURN sk.category, sk.key, sk.reason',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-source'})
SET c.name = 'Source', c.order = 13, c.category = 'federation',
    c.description = 'An external graph authorized to import nodes into mycelium. Each Source has a public_key, schema_version, and description. Imports from a Source land as :Imported nodes with compound node_ids of the form <source_alias>:<original-id>.',
    c.example = 'MATCH (s:Source) RETURN s.alias, s.schema_version, s.public_key',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-imported'})
SET c.name = 'Imported', c.order = 14, c.category = 'federation',
    c.description = 'A secondary label on nodes that came from a Source. Imported nodes are read-only and isolated from core invariants by default. They carry provenance (the source alias) and imported_in_species (which candidate species the import landed in) for audit.',
    c.example = 'MATCH (n:Imported {provenance: "ember"}) RETURN n.node_id, n.imported_in_species',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-adopted'})
SET c.name = 'Adopted', c.order = 15, c.category = 'federation',
    c.description = 'A formerly-imported node promoted to a full citizen. Adoption removes :Imported, adds :Adopted, keeps provenance + adopted_from_provenance as audit trail. Adoption runs inside validate-merge, so if the adopted node would break any invariant, the adoption rolls back.',
    c.example = 'MATCH (n:Adopted) RETURN n.node_id, n.adopted_from_provenance, n.adopted_by, n.adopted_at',
    c.file_type = 'concept';


// --- Guides (the "how do I" answers) ----------------------------------------

MERGE (g:Guide {node_id: 'guide-propose-mutation'})
SET g.name = 'Propose a Mutation', g.order = 1, g.category = 'operator',
    g.description = 'How to submit a change to the graph.',
    g.steps = [
      '1. Write your change as a .cypher file under pr/ (e.g. pr/2026-04-16-add-principle.cypher). Use MERGE, not CREATE, and use compound node_ids if you are importing from an external source.',
      '2. Dry-run locally: graph/runner/validate-merge.sh pr/my-change.cypher — applies inside a transaction, runs all enabled invariants + tests + merkle, rolls back regardless of outcome unless --mint is passed.',
      '3. If green, open a PR to develop. GitHub Actions graph-validate workflow re-runs validate-merge in ephemeral Neo4j seeded from the base branch.',
      '4. On CI success, a candidate species is minted with the new manifest_root. The PR comment shows the candidate DNA and the signing command.',
      '5. Run graph/runner/witness-sign.sh <candidate-id> <your-alias> locally — your ed25519 private key signs the manifest.',
      '6. graph/runner/verify-signatures.sh <candidate-id> stamps the signature as verified.',
      '7. graph/runner/species-canonize.sh <candidate-id> promotes the candidate to canonical once quorum is met. Chain head advances. Merge the PR.'
    ],
    g.file_type = 'guide';

MERGE (g:Guide {node_id: 'guide-onboard-witness'})
SET g.name = 'Onboard a Witness', g.order = 2, g.category = 'operator',
    g.description = 'How to become a signer.',
    g.steps = [
      '1. Run graph/runner/witness-init.sh <your-alias>. This generates an ed25519 keypair and stores the private key at ~/.mycelium/witness-<alias>.key (chmod 600).',
      '2. The public key is automatically registered on a new :Witness node in the graph, with active=true and key_algorithm=ed25519.',
      '3. You can now sign candidate species: graph/runner/witness-sign.sh <species-id> <your-alias>. The runner reads your private key, signs "manifest_root|parent_dna|node_id", stores the signature as a WitnessSignature.',
      '4. Before canonize counts your signature, verify-signatures.sh runs mycelium-crypto.py verify on it. Invalid signatures are rejected.',
      '5. Your signing key stays on your machine forever. The graph never sees it.'
    ],
    g.file_type = 'guide';

MERGE (g:Guide {node_id: 'guide-import-external'})
SET g.name = 'Import an External Graph', g.order = 3, g.category = 'federation',
    g.description = 'How to flow another graph into mycelium.',
    g.steps = [
      '1. Register the source: graph/runner/source-register.sh <alias> <ed25519-public-key-hex> [schema_version] [description]. Creates a :Source node.',
      '2. Prepare the bundle: a .cypher file with MERGE statements using compound node_ids "<alias>:<original-id>". All MERGEs must be scoped; pre-check rejects any non-namespaced id.',
      '3. Drop the bundle at imports/<alias>/<date>.cypher + imports/<alias>/source.json (optional metadata).',
      '4. Run: graph/runner/import-external.sh <alias> imports/<alias>/<date>.cypher. The runner applies the bundle inside a validate-merge transaction, tags every new node with :Imported:<Source> labels and provenance/imported_at/imported_in_species properties.',
      '5. On success, a candidate species is minted capturing the new state. Witnesses sign as usual.',
      '6. Imported nodes are read-only by default. To adopt specific nodes into the core: graph/runner/adopt-node.sh <node-id> <your-alias>.'
    ],
    g.file_type = 'guide';

MERGE (g:Guide {node_id: 'guide-merkle-integrity'})
SET g.name = 'Merkle Integrity', g.order = 4, g.category = 'design',
    g.description = 'How the Merkle layer works.',
    g.steps = [
      'Every domain node has a leaf_hash property = sha256(label || sorted(k=json(v))) over the nodes own properties, excluding anything in SkipKey. Chain-layer nodes (Species, Witness, WitnessSignature) are excluded entirely so chain mutations do not drift root.',
      'Being.root_hash = sha256(sorted(collect(leaf_hash))). Updated by merkle-properties.cypher (two-pass: materialize all pairs, then UNWIND+SET — eliminates lazy evaluation drift).',
      'Adding/modifying any content property changes that nodes leaf_hash, which cascades into a new root. Changing a SkipKey property (heartbeat, embedding, health, enabled, etc.) does NOT change root.',
      'species.manifest_root = the root_hash at the moment the species was minted. Each species commits to a specific state. The chain is verifiable by walking DESCENDED_FROM and checking that each species manifest_root matches the expected state at mint time.',
      'Determinism is load-bearing. The two-pass materialization was the fix for a subtle lazy-eval bug that made single-pass SET non-deterministic across runs.'
    ],
    g.file_type = 'guide';

MERGE (g:Guide {node_id: 'guide-immune-system'})
SET g.name = 'Immune System', g.order = 5, g.category = 'design',
    g.description = 'How the auto-heal loop works.',
    g.steps = [
      'Each Invariant can carry a heal_protocol (node_id of a Protocol to fire on unhealthy) + heal_cooldown_sec + heal_params.',
      'graph/runner/immune.sh walks every enabled Invariant with a heal_protocol, checks the invariant via apoc.cypher.run, and if unhealthy with cooldown elapsed, fires the heal protocol.',
      'Heal protocols can be inline cypher (e.g. any APOC-based protocol) OR shell runners (e.g. graph/runner/embed-dirty.sh for embedding coverage). Immune dispatches based on file extension.',
      'Example: invariant-graph-density checks edges/nodes >= 3.0 threshold. If not, fires protocol-semantic-densify which creates INFERRED_SIMILAR edges from the vector index. Density recovers, invariant becomes healthy.',
      'Example: invariant-embedding-coverage checks all leaf_hashes match their embedding_for_leaf_hash. If drifted, fires graph/runner/embed-dirty.sh which re-embeds only the stale nodes.',
      'The cooldown prevents runaway loops — a failing heal attempt backs off for N seconds before retrying. Fires accumulate in heal_count for observability.'
    ],
    g.file_type = 'guide';

MERGE (g:Guide {node_id: 'guide-fire-together'})
SET g.name = 'Fire Together, Wire Together', g.order = 6, g.category = 'design',
    g.description = 'How the graph learns from its own operation.',
    g.steps = [
      'Every cypher query run via the mycelium CLI emits a QueryTrace node with cypher_summary, command, invoked_at, duration_ms.',
      'The emit-trace protocol MERGEs by sha256(cypher) into a canonical :Query node and increments fire_count on every invocation. Same cypher = same Query = accumulating strength.',
      'The per-atom traces from atom-run let the graph see which atoms are fired, when, and by whom. mycelium watching reads the last 10 seconds to show live cognition.',
      'strengthen-edges.cypher walks recent QueryTraces, collects touched_ids, and increments fire_count on edges between pairs of cited nodes. Over time, hot paths compound weight.',
      'Future work: a traversal helper that prefers edges with high fire_count when exploring. The graph will literally prefer the paths it has historically used — compounding intelligence.',
      'Query.semantic holds a natural-language description of the cypher. Combined with embeddings, this becomes a semantic search over what the graph has been asked: "find the cypher that mints a species" -> vector lookup over Query.semantic.'
    ],
    g.file_type = 'guide';


// --- Installation + quick start ---------------------------------------------

MERGE (g:Guide {node_id: 'guide-install'})
SET g.name = 'Installation + Quick Start', g.order = 0, g.category = 'getting-started',
    g.description = 'From zero to a live mycelium in ~10 minutes.',
    g.steps = [
      'Prerequisites: Docker (for Neo4j), Python 3.10+, Ollama (for embeddings), git, gh CLI (optional for PRs).',
      'Clone: git clone https://github.com/kagrawal29/mycelium.git && cd mycelium',
      'Bring up Neo4j with APOC: docker compose -f ../../tetrahedron/deploy/mycelium-neo4j/docker-compose.local.yml up -d (compose file lives in the tetrahedron repo deploy tree).',
      'Wait for ready: until docker exec mycelium-neo4j-local cypher-shell -u neo4j -p localtest12 "RETURN 1" >/dev/null 2>&1; do sleep 2; done',
      'Seed the canonical graph: docker exec -i mycelium-neo4j-local cypher-shell -u neo4j -p localtest12 --encryption false < graph-state.cypher',
      'Install Ollama embeddings model: ollama pull nomic-embed-text (first run downloads ~274 MB).',
      'Register yourself as a witness: graph/runner/witness-init.sh <your-alias> — generates an ed25519 keypair, stores private key at ~/.mycelium/witness-<alias>.key.',
      'Verify: ./mycelium verify — runs merkle + invariants + tests. Should report 21/21 invariants healthy and all active tests passing.',
      'Explore: ./mycelium status (current state), ./mycelium know-thyself (full self-model), ./mycelium help (all commands).'
    ],
    g.file_type = 'guide';

MERGE (g:Guide {node_id: 'guide-use-safely'})
SET g.name = 'Using Mycelium Safely', g.order = 7, g.category = 'operator',
    g.description = 'Principles and guardrails for operating the graph without breaking it.',
    g.steps = [
      'Always dry-run mutations first: graph/runner/validate-merge.sh <file>.cypher — applies inside a transaction, runs every invariant and test, rolls back on failure. Exit code 0 means it would pass CI.',
      'Prefer MERGE over CREATE so re-running a mutation is idempotent. CREATE should only be used for relationships that are semantically once-only.',
      'Never commit private keys. ~/.mycelium/ is gitignored by convention. Public keys go on Witness nodes; private keys stay on disk with chmod 600.',
      'Never edit Being.root_hash or any SkipKey-marked property directly. Those are derived. Change the underlying content and let merkle-properties recompute.',
      'Never delete a Species node. Chain history is append-only. To retire a species, flip canonical=false + set superseded_at/superseded_by.',
      'Never bypass validate-merge for a PR that touches domain state. The write gate is the single chokepoint that keeps the graph consistent.',
      'If you need to experiment, use the --mint flag deliberately (graph/runner/validate-merge.sh file --mint) — otherwise the default is dry-run.',
      'Watch live: ./mycelium watching shows what is firing right now. ./mycelium status shows aggregate health. ./mycelium verify runs the full check suite.',
      'On a destructive action (recreate container, rm -rf, force push), pause and confirm. Data on named docker volumes persists through container recreate; data in /tmp does not.'
    ],
    g.file_type = 'guide';

MERGE (g:Guide {node_id: 'guide-merge-protocol'})
SET g.name = 'Merge Protocol (end-to-end)', g.order = 8, g.category = 'operator',
    g.description = 'The complete flow from a mutation idea to a canonical chain advance.',
    g.steps = [
      'AUTHOR: Write the mutation as a .cypher file in pr/<date>-<topic>.cypher. Use MERGE + SET. Include comments explaining intent.',
      'LOCAL DRY-RUN: graph/runner/validate-merge.sh pr/<file>.cypher. If it passes (exit 0), proceed. If not, read the error — it names the failing invariant or test.',
      'OPEN PR: git add pr/<file>.cypher && git commit && gh pr create.',
      'CI VALIDATE: .github/workflows/graph-validate.yml spins ephemeral Neo4j from the base branch, runs validate-merge. Posts a sticky PR comment with success/failure + candidate species DNA.',
      'LOCAL SIGN: graph/runner/witness-sign.sh <candidate-id> <your-alias>. Your ed25519 key signs manifest_root|parent_dna|node_id.',
      'VERIFY SIGS: graph/runner/verify-signatures.sh <candidate-id>. Stamps verified=true on signatures that crypto-verify.',
      'COLLECT QUORUM: If quorum_required > 1, have other witnesses also sign. They each run witness-sign.sh + verify-signatures.sh. species-canonize blocks until quorum is reached.',
      'CANONIZE: graph/runner/species-canonize.sh <candidate-id>. Flips candidate to canonical, advances Being.CURRENT_SPECIES, demotes the previous head.',
      'EXPORT + MERGE: graph/runner/export-graph-state.sh regenerates graph-state.cypher from the new state. Merge the PR. CI re-seeds prod + staging instances.'
    ],
    g.file_type = 'guide';

MERGE (g:Guide {node_id: 'guide-daily-ops'})
SET g.name = 'Daily Operations', g.order = 9, g.category = 'operator',
    g.description = 'Common tasks after the graph is running.',
    g.steps = [
      './mycelium status — quick health + chain state snapshot',
      './mycelium verify — run all invariants + tests',
      './mycelium know-thyself — full self-model (concepts, protocols, duties, capabilities)',
      './mycelium search "<natural language>" — semantic search over node embeddings',
      './mycelium watching — live cognition snapshot (last 10s of QueryTraces)',
      './mycelium breathe — emit a heartbeat pulse (updates Being counters; auto-fired by the heartbeat-loop runner)',
      './mycelium embed — re-run embedding for any drifted nodes',
      './mycelium export — regenerate graph-state.cypher from live Neo4j',
      'graph/runner/immune.sh — manually run the auto-heal loop (otherwise runs from heartbeat cadence)',
      'graph/runner/atom-run.sh <protocol-id> — execute a protocol by walking its CypherAtom chain instead of its file'
    ],
    g.file_type = 'guide';


// --- UX Rubric (first-class evaluation) -------------------------------------
// Seven dimensions of user experience, each with criteria that carry a
// current_score (0-5), target_score, and evidence. Queryable to find
// weak spots: "which dimensions scored below 3?"

MERGE (r:UXRubric {node_id: 'ux-rubric'})
SET r.name = 'Mycelium UX Rubric',
    r.version = 'v1',
    r.description = 'Multidimensional evaluation of the mycelium operator experience. Every dimension has criteria scored 0-5. Aggregate score = average of all criterion scores.',
    r.file_type = 'ux-rubric';

// Dimension: Discoverability
MERGE (d:UXDimension {node_id: 'uxdim-discoverability'})
SET d.name = 'Discoverability',
    d.description = 'Can a new user find what they need without reading code? Is help visible, searchable, complete?',
    d.weight = 1.0;
MERGE (r1:UXRubric {node_id: 'ux-rubric'})-[:HAS_DIMENSION]->(d);

MERGE (c:UXCriterion {node_id: 'uxcrit-discoverability-help'})
SET c.text = 'Running `mycelium help` returns a full command list grouped by category', c.current_score = 5, c.target_score = 5,
    c.evidence = 'Implemented: reads :Command nodes at runtime, groups by category, prints usage + description.';
MERGE (d1:UXDimension {node_id: 'uxdim-discoverability'})-[:HAS_CRITERION]->(c);

MERGE (c:UXCriterion {node_id: 'uxcrit-discoverability-know-thyself'})
SET c.text = 'Running `mycelium know-thyself` returns the full self-model without external docs', c.current_score = 5, c.target_score = 5,
    c.evidence = 'Implemented: queries Being + Commands + Protocols + Invariants + TestCases + CypherAtoms.';
MERGE (d)-[:HAS_CRITERION]->(c);

MERGE (c:UXCriterion {node_id: 'uxcrit-discoverability-docs'})
SET c.text = 'Running `mycelium docs` generates a complete human-readable manual from the graph', c.current_score = 3, c.target_score = 5,
    c.evidence = 'Partial: Concepts + Guides + UX rubric seeded. Manual generation builtin still needs to compose markdown output.';
MERGE (d)-[:HAS_CRITERION]->(c);

// Dimension: Safety
MERGE (d:UXDimension {node_id: 'uxdim-safety'})
SET d.name = 'Safety',
    d.description = 'Can a user undo mistakes? Does the system refuse dangerous operations? Are state changes reversible?',
    d.weight = 1.2;
MERGE (r)-[:HAS_DIMENSION]->(d);

MERGE (c:UXCriterion {node_id: 'uxcrit-safety-dry-run'})
SET c.text = 'Every mutation has a dry-run mode that rolls back', c.current_score = 5, c.target_score = 5,
    c.evidence = 'validate-merge.sh applies inside a transaction by default, --mint is opt-in.';
MERGE (d)-[:HAS_CRITERION]->(c);

MERGE (c:UXCriterion {node_id: 'uxcrit-safety-chain-append-only'})
SET c.text = 'Species chain is append-only — history is preserved', c.current_score = 5, c.target_score = 5,
    c.evidence = 'Legacy species are relabeled :LegacySpecies, never deleted. Canonize demotes, does not delete.';
MERGE (d)-[:HAS_CRITERION]->(c);

MERGE (c:UXCriterion {node_id: 'uxcrit-safety-keys-offline'})
SET c.text = 'Private keys never enter the graph', c.current_score = 5, c.target_score = 5,
    c.evidence = 'ed25519 keys live at ~/.mycelium/ on disk. Only public keys on Witness nodes.';
MERGE (d)-[:HAS_CRITERION]->(c);

// Dimension: Explainability
MERGE (d:UXDimension {node_id: 'uxdim-explainability'})
SET d.name = 'Explainability',
    d.description = 'Do errors name the failing rule + how to fix? Can a user trace why a decision was made?',
    d.weight = 1.1;
MERGE (r)-[:HAS_DIMENSION]->(d);

MERGE (c:UXCriterion {node_id: 'uxcrit-explainability-named-failures'})
SET c.text = 'Failing invariants and tests name the specific rule in the error', c.current_score = 5, c.target_score = 5,
    c.evidence = 'validate-merge throws via apoc.util.validate with JSON payload listing failing invariants/tests with actual vs expected.';
MERGE (d)-[:HAS_CRITERION]->(c);

MERGE (c:UXCriterion {node_id: 'uxcrit-explainability-deferred-reasons'})
SET c.text = 'Deferred tests carry a deferred_reason + deferred_note', c.current_score = 5, c.target_score = 5,
    c.evidence = '25 tests + 0 invariants currently deferred with categorized reasons (frozen-write-path, data-cleanup, etc.) and free-text notes.';
MERGE (d)-[:HAS_CRITERION]->(c);

// Dimension: Observability
MERGE (d:UXDimension {node_id: 'uxdim-observability'})
SET d.name = 'Observability',
    d.description = 'Can a user see what the graph is doing right now? What it has been doing recently?',
    d.weight = 1.0;
MERGE (r)-[:HAS_DIMENSION]->(d);

MERGE (c:UXCriterion {node_id: 'uxcrit-observability-watching'})
SET c.text = 'mycelium watching shows currently-firing atoms', c.current_score = 5, c.target_score = 5,
    c.evidence = 'Implemented via QueryTrace query over last 10 seconds.';
MERGE (d)-[:HAS_CRITERION]->(c);

MERGE (c:UXCriterion {node_id: 'uxcrit-observability-history'})
SET c.text = 'Query history is queryable (every cypher is a :Query node)', c.current_score = 5, c.target_score = 5,
    c.evidence = 'Every CLI invocation emits a Query node keyed by cypher hash with accumulating fire_count.';
MERGE (d)-[:HAS_CRITERION]->(c);

// Dimension: Predictability
MERGE (d:UXDimension {node_id: 'uxdim-predictability'})
SET d.name = 'Predictability',
    d.description = 'Do the same inputs produce the same outputs? Is the system deterministic where it claims to be?',
    d.weight = 1.2;
MERGE (r)-[:HAS_DIMENSION]->(d);

MERGE (c:UXCriterion {node_id: 'uxcrit-predictability-merkle'})
SET c.text = 'Merkle root is deterministic across runs', c.current_score = 5, c.target_score = 5,
    c.evidence = 'Two-pass materialization fix in merkle-properties.cypher eliminates the lazy-eval drift. Verified byte-identical root across consecutive runs.';
MERGE (d)-[:HAS_CRITERION]->(c);

MERGE (c:UXCriterion {node_id: 'uxcrit-predictability-graph-state'})
SET c.text = 'graph-state.cypher re-export is byte-stable modulo timestamps', c.current_score = 4, c.target_score = 5,
    c.evidence = 'Export is deterministic except for the header timestamp line. Could be stabilized by pinning to the last canonize time.';
MERGE (d)-[:HAS_CRITERION]->(c);

// Dimension: Speed (time-to-useful)
MERGE (d:UXDimension {node_id: 'uxdim-speed'})
SET d.name = 'Speed',
    d.description = 'How fast can a new user get from clone to first successful mutation?',
    d.weight = 0.8;
MERGE (r)-[:HAS_DIMENSION]->(d);

MERGE (c:UXCriterion {node_id: 'uxcrit-speed-onboard'})
SET c.text = 'New user reaches first `mycelium verify` success within 10 minutes of clone', c.current_score = 3, c.target_score = 5,
    c.evidence = 'Installation guide documents 9 steps. Not yet tested with a fresh user. Dependencies (Ollama, Docker) add setup time.';
MERGE (d)-[:HAS_CRITERION]->(c);

// Dimension: Self-healing
MERGE (d:UXDimension {node_id: 'uxdim-self-healing'})
SET d.name = 'Self-Healing',
    d.description = 'Does the system recover from drift without human intervention?',
    d.weight = 1.0;
MERGE (r)-[:HAS_DIMENSION]->(d);

MERGE (c:UXCriterion {node_id: 'uxcrit-self-healing-density'})
SET c.text = 'Graph density auto-heals below threshold', c.current_score = 5, c.target_score = 5,
    c.evidence = 'invariant-graph-density + heal_protocol=semantic-densify auto-fires when density drops below 3.0 e/n.';
MERGE (d)-[:HAS_CRITERION]->(c);

MERGE (c:UXCriterion {node_id: 'uxcrit-self-healing-embedding'})
SET c.text = 'Embedding coverage auto-heals on drift', c.current_score = 5, c.target_score = 5,
    c.evidence = 'invariant-embedding-coverage + heal_protocol=embed-dirty auto-fires when leaf_hash drifts from embedding_for_leaf_hash.';
MERGE (d)-[:HAS_CRITERION]->(c);

MERGE (c:UXCriterion {node_id: 'uxcrit-self-healing-heartbeat'})
SET c.text = 'Heartbeat restart is automatic via systemd/launchd', c.current_score = 2, c.target_score = 5,
    c.evidence = 'Manual: run heartbeat-loop.sh by hand. Should be a systemd-user unit or equivalent.';
MERGE (d)-[:HAS_CRITERION]->(c);


// --- Principles (cross-cutting design choices) ------------------------------

MERGE (p:DesignPrinciple {node_id: 'design-graph-is-source'})
SET p.name = 'The graph is the source of truth',
    p.description = 'Everything the system knows, does, or enforces is represented as nodes and edges in Neo4j. Files in the repo are serialization formats for git persistence, not primary storage. If the graph and a file disagree, the graph wins — unless the file is a bootstrap that the graph has not yet been seeded from.',
    p.file_type = 'design-principle';

MERGE (p:DesignPrinciple {node_id: 'design-cypher-native'})
SET p.name = 'Cypher-native, not code-native',
    p.description = 'Behavior is expressed as cypher, not as Python/TypeScript/etc. The only non-cypher files are: 2 small Python sidecars (ed25519 crypto, Ollama embedding) that cross boundaries cypher cannot, and ~15 bash shell runners that pipe cypher files to cypher-shell. Everything else is graph-native.',
    p.file_type = 'design-principle';

MERGE (p:DesignPrinciple {node_id: 'design-merkle-properties'})
SET p.name = 'Merkle as properties, not as entities',
    p.description = 'Earlier design stored Merkle trees as graph entities (:MerkleNode, :MerkleTree). That created a recursive inflation bug where each new tree included prior MerkleNodes in its hash input — 7 generations compounded into 546,450 nodes. Properties cannot contain themselves, so storing leaf_hash as a property on each node eliminates the recursion by construction.',
    p.file_type = 'design-principle';

MERGE (p:DesignPrinciple {node_id: 'design-self-describe'})
SET p.name = 'Self-describability is trust',
    p.description = 'A system that cannot fully explain itself cannot be fully trusted. Mycelium must be able to generate a complete human-readable manual from its own graph — concepts, protocols, invariants, commands, guides, principles — with zero hardcoded external documentation. mycelium docs reads :Concept + :Guide + :DesignPrinciple nodes plus the live Protocol/Invariant/TestCase/Command sets and emits a full markdown manual. This file (docs-seed.cypher) is the only place where conceptual explanations are authored, and even those live in the graph after seeding.',
    p.file_type = 'design-principle';

MERGE (p:DesignPrinciple {node_id: 'design-auto-heal'})
SET p.name = 'Auto-heal via invariants',
    p.description = 'Anything that can be automatically repaired should be. Invariants with heal_protocols detect + fix their own unhealth without human intervention. Density drops, embeddings drift, orphans accumulate — the immune system compensates on its own cadence. Human attention reserved for structural decisions.',
    p.file_type = 'design-principle';


// --- Ontology hub --- wires Concept/Guide/DesignPrinciple/Report nodes
// together so they are not structural orphans (test-no-orphan-transients
// looks for unconnected nodes with file_type IN [concept, ...]).

MERGE (o:Ontology {node_id: 'ontology-mycelium'})
SET o.label = 'Mycelium Ontology (self-model hub)',
    o.description = 'Central hub linking concepts, guides, design principles, reports, and UX rubric nodes so they are not orphans. Every documentation node hangs off this node.',
    o.file_type = 'ontology';

MATCH (c:Concept) WHERE c.file_type = 'concept' AND c.name IS NOT NULL
MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MERGE (c)-[:DESCRIBES_IN]->(o);

MATCH (g:Guide)
MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MERGE (g)-[:DOCUMENTS_IN]->(o);

MATCH (p:DesignPrinciple)
MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MERGE (p)-[:PRINCIPLE_OF]->(o);

MATCH (r:Report)
MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MERGE (r)-[:REPORT_OF]->(o);

MATCH (u:UXRubric)
MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MERGE (u)-[:EVALUATES]->(o);

RETURN 'seeded ' + toString(count(*)) + ' concepts+guides+principles+ontology' AS status;
