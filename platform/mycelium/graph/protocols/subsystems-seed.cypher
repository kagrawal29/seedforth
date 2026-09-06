// @kind: seed
// ============================================================================
// Protocol: Subsystems Seed
// ============================================================================
// Seeds the developer-integration layer: :Subsystem, :ExternalCode,
// :IntegrationPoint, :Metaphor. These let any external workflow, tool, or
// system be modeled in the graph without rewriting it — the code stays in
// its native form, but its semantics are mapped to :CypherAtoms and its
// boundaries are first-class nodes.
//
// Philosophy: "developers still have the code artifacts, but everything is
// mapped to atomic cypher." Code is a runtime for the graph model, not the
// model itself. The graph is the canonical description of what the system
// does; code is one way to execute it. A Python script and a cypher atom
// can implement the same operation as long as they share an :IntegrationPoint.
//
// Idempotent: all MERGEs keyed on node_id.
// ============================================================================


// --- Metaphors (the philosophical layer) ------------------------------------
// Biological and mental analogs that anchor the design. Each metaphor links
// the technical mechanism to its inspiration, so a new reader can grasp the
// why before the how.

MERGE (m:Metaphor {node_id: 'metaphor-heartbeat'})
SET m.name = 'Heartbeat',
    m.biological_analog = 'Cardiac pulse — autonomic rhythm maintained by a distributed pacemaker.',
    m.applied_to = 'protocol-heartbeat + heartbeat-loop.sh',
    m.explanation = 'Every N seconds the graph updates Being.heartbeat_count and last_heartbeat. The pulse is how external observers confirm the system is alive. Skipping a beat is a signal to restart the loop, not to panic about data integrity.',
    m.file_type = 'metaphor';

MERGE (m:Metaphor {node_id: 'metaphor-immune'})
SET m.name = 'Immune System',
    m.biological_analog = 'Antibody-mediated response — recognize a deviation, produce a counter, return to homeostasis.',
    m.applied_to = 'graph/protocols/immune.cypher + invariant heal_protocol field',
    m.explanation = 'An Invariant that goes unhealthy triggers its linked heal_protocol autonomously. Density drops → semantic-densify. Embedding drifts → embed-dirty. The graph maintains itself without human intervention, with cooldowns to prevent runaway.',
    m.file_type = 'metaphor';

MERGE (m:Metaphor {node_id: 'metaphor-synapse'})
SET m.name = 'Synapse',
    m.biological_analog = 'Neural junction — signal passes from one neuron to another and strengthens the connection if co-fired.',
    m.applied_to = 'CypherAtom + FEEDS edges + fire_count + strengthen-edges.cypher',
    m.explanation = 'Every atom execution fires a synapse (emits a QueryTrace). Atoms fire via FEEDS connections that thread variables between them. Over repeated co-firing, edge fire_counts accumulate. Hot paths compound weight. mycelium watching shows which synapses are firing right now.',
    m.file_type = 'metaphor';

MERGE (m:Metaphor {node_id: 'metaphor-dna'})
SET m.name = 'DNA',
    m.biological_analog = 'Genetic material — hashed, signed, inherited, replicated with fidelity.',
    m.applied_to = 'Species.manifest_root + merkle-properties + species lifecycle',
    m.explanation = 'Each species carries a manifest_root = sha256 commitment to the state of the graph at its mint time. Species descend from parents via DESCENDED_FROM edges, inheriting their lineage. Witnesses sign species to attest to their validity — the chain is effectively the graph reproducing itself across time.',
    m.file_type = 'metaphor';

MERGE (m:Metaphor {node_id: 'metaphor-speciation'})
SET m.name = 'Speciation',
    m.biological_analog = 'New species branch from a parent when conditions change — genesis event marks divergence.',
    m.applied_to = 'species-mint + fresh genesis under phase-b algorithm',
    m.explanation = 'Mycelium speciated once (from the legacy falkor-era chain to phase-b-v1) via genesis-phase-b.cypher. Every candidate species thereafter is an incremental mutation — not a new species in the biological sense, but a step in the same lineage. True speciation happens when the algorithm or invariant set changes materially.',
    m.file_type = 'metaphor';

MERGE (m:Metaphor {node_id: 'metaphor-cell'})
SET m.name = 'Cell',
    m.biological_analog = 'Membrane-bounded unit with internal state and external interfaces.',
    m.applied_to = 'Subsystem + IntegrationPoint',
    m.explanation = 'A Subsystem is a cell: it has internal code (its own files + protocols), its own state, and explicit membrane points (IntegrationPoints) where it talks to other cells. Cells communicate in cypher. Multicellular mycelium = many Subsystems, each with its own metabolism, coexisting in one graph substrate.',
    m.file_type = 'metaphor';

MERGE (m:Metaphor {node_id: 'metaphor-forest-mycelium'})
SET m.name = 'Forest Mycelium',
    m.biological_analog = 'Underground fungal network — individual organisms linked through shared substrate, exchanging signals and nutrients.',
    m.applied_to = 'the whole system, its name',
    m.explanation = 'Mycelium is the substrate that lets separate projects, teams, and agents exchange knowledge without merging into one organism. Forest aliases (Banyan, Sequoia, Birch, Cedar, Oak, Mycelium) refer to team members in signals, respecting identity while allowing cross-pollination through the graph.',
    m.file_type = 'metaphor';


// --- Subsystems (named external units that integrate with mycelium) ---------

MERGE (s:Subsystem {node_id: 'subsystem-mycelium-core'})
SET s.name = 'mycelium-core',
    s.description = 'The graph itself — Neo4j database, APOC plugin, all protocols, all invariants, all runners. The thing everything else integrates with.',
    s.primary_language = 'cypher',
    s.entry_point = 'mycelium (CLI)',
    s.external_repo = 'github.com/kagrawal29/mycelium',
    s.owner = 'Mycelium',
    s.status = 'active',
    s.file_type = 'subsystem';

MERGE (s:Subsystem {node_id: 'subsystem-tetrahedron'})
SET s.name = 'tetrahedron',
    s.description = 'The parent orchestration repo — houses the Docker compose files, deploy scripts, and CI workflows that bring up and maintain a running mycelium instance. Mycelium itself is one project inside tetrahedron.',
    s.primary_language = 'bash+docker+yaml',
    s.entry_point = 'deploy/mycelium-neo4j/docker-compose.local.yml',
    s.external_repo = 'github.com/kagrawal29/tetrahedron',
    s.owner = 'Mycelium',
    s.status = 'active',
    s.file_type = 'subsystem';

MERGE (s:Subsystem {node_id: 'subsystem-crypto-sidecar'})
SET s.name = 'crypto-sidecar',
    s.description = 'ed25519 signing and verification via the Python cryptography library. A thin boundary layer that crosses the graph<->filesystem line because asymmetric crypto cannot live inside cypher.',
    s.primary_language = 'python',
    s.entry_point = 'graph/runner/mycelium-crypto.py',
    s.external_repo = '(in-tree)',
    s.owner = 'Mycelium',
    s.status = 'active',
    s.file_type = 'subsystem';

MERGE (s:Subsystem {node_id: 'subsystem-embed-sidecar'})
SET s.name = 'embed-sidecar',
    s.description = 'Ollama-backed local embeddings via nomic-embed-text. Reads dirty nodes, embeds text, writes vectors back. Needed because embedding models cannot run inside cypher.',
    s.primary_language = 'python',
    s.entry_point = 'graph/runner/embed-dirty.py',
    s.external_repo = '(in-tree)',
    s.owner = 'Mycelium',
    s.status = 'active',
    s.file_type = 'subsystem';


// --- ExternalCode (the files that implement subsystems) --------------------
// File path + language + purpose + link back to the subsystem. Developers
// can query "show me every external file in mycelium" and get an inventory.

MERGE (ec:ExternalCode {node_id: 'xcode-mycelium-crypto-py'})
SET ec.file_path = 'graph/runner/mycelium-crypto.py',
    ec.language = 'python',
    ec.purpose = 'ed25519 keygen/sign/verify CLI with cryptography lib. Stores private keys at ~/.mycelium/witness-<alias>.key.',
    ec.interfaces_with = 'subsystem-crypto-sidecar',
    ec.file_type = 'external-code';

MERGE (ec:ExternalCode {node_id: 'xcode-embed-dirty-py'})
SET ec.file_path = 'graph/runner/embed-dirty.py',
    ec.language = 'python',
    ec.purpose = 'Reads dirty nodes from Neo4j, calls Ollama /api/embeddings for each, writes 768d vectors back via the neo4j driver.',
    ec.interfaces_with = 'subsystem-embed-sidecar',
    ec.file_type = 'external-code';

MERGE (ec:ExternalCode {node_id: 'xcode-atomize-protocol-py'})
SET ec.file_path = 'graph/runner/atomize-protocol.py',
    ec.language = 'python',
    ec.purpose = 'Statement-level cypher file parser. Splits on semicolons, collects preceding // comments as semantic, emits :CypherAtom nodes wired by :FOLLOWS edges.',
    ec.interfaces_with = 'subsystem-mycelium-core',
    ec.file_type = 'external-code';

MERGE (ec:ExternalCode {node_id: 'xcode-mycelium-cli'})
SET ec.file_path = 'mycelium',
    ec.language = 'bash',
    ec.purpose = 'Top-level CLI. Reads :Command nodes at runtime, dispatches to either a builtin handler or the command runner field. Traces every invocation as a :QueryTrace. Zero hardcoded command list.',
    ec.interfaces_with = 'subsystem-mycelium-core',
    ec.file_type = 'external-code';


// --- IntegrationPoints (how subsystems talk to mycelium) -------------------

MERGE (ip:IntegrationPoint {node_id: 'ipoint-sign-species'})
SET ip.name = 'sign-species',
    ip.direction = 'inbound-to-graph',
    ip.operation = 'record a WitnessSignature on a candidate Species',
    ip.trigger = 'witness-sign.sh <species-id> <alias>',
    ip.semantic = 'The developer runs the shell wrapper with their alias. It reads the local private key, computes an ed25519 signature over the species commitment fields, and MERGEs a :WitnessSignature node into the graph via the species-sign.cypher protocol.',
    ip.file_type = 'integration-point';

MERGE (ip:IntegrationPoint {node_id: 'ipoint-embed-dirty'})
SET ip.name = 'embed-dirty',
    ip.direction = 'bidirectional',
    ip.operation = 're-embed nodes whose leaf_hash has drifted',
    ip.trigger = 'embed-dirty.sh or immune auto-fire',
    ip.semantic = 'Query the graph for nodes where leaf_hash != embedding_for_leaf_hash, send their text to Ollama, write the resulting 768d vectors back. No human intervention needed — the immune system fires this when invariant-embedding-coverage goes unhealthy.',
    ip.file_type = 'integration-point';

MERGE (ip:IntegrationPoint {node_id: 'ipoint-import-external-graph'})
SET ip.name = 'import-external-graph',
    ip.direction = 'inbound-to-graph',
    ip.operation = 'flow a foreign graph bundle into mycelium under a namespaced :Imported label',
    ip.trigger = 'import-external.sh <source-alias> <bundle.cypher>',
    ip.semantic = 'External developer registers their Source (with an ed25519 public key), prepares a bundle using compound node_ids <source>:<original>, and runs the import. Mycelium validates via the write gate, tags everything with :Imported:<Source>, and mints a candidate species.',
    ip.file_type = 'integration-point';

MERGE (ip:IntegrationPoint {node_id: 'ipoint-atomize-cypher'})
SET ip.name = 'atomize-cypher',
    ip.direction = 'outbound-from-disk',
    ip.operation = 'parse a .cypher file into :CypherAtom nodes in the graph',
    ip.trigger = 'python3 graph/runner/atomize-protocol.py <protocol-id> <file.cypher>',
    ip.semantic = 'Developer writes a .cypher file on disk. The atomizer reads it, splits into statements, emits one :CypherAtom per statement with preceding comments as semantic, wires :FOLLOWS edges in file order, and links the Protocol to its :FIRST_ATOM.',
    ip.file_type = 'integration-point';


// --- Ontology wiring --------------------------------------------------------

MERGE (o:Ontology {node_id: 'ontology-mycelium'});
MATCH (s:Subsystem), (o:Ontology {node_id: 'ontology-mycelium'}) MERGE (s)-[:PART_OF]->(o);
MATCH (m:Metaphor), (o:Ontology {node_id: 'ontology-mycelium'}) MERGE (m)-[:METAPHOR_OF]->(o);
MATCH (ec:ExternalCode), (o:Ontology {node_id: 'ontology-mycelium'}) MERGE (ec)-[:EXTERNAL_CODE_OF]->(o);
MATCH (ip:IntegrationPoint), (o:Ontology {node_id: 'ontology-mycelium'}) MERGE (ip)-[:BOUNDARY_OF]->(o);

// Link ExternalCode → Subsystem explicitly
MATCH (ec:ExternalCode), (s:Subsystem) WHERE ec.interfaces_with = s.node_id MERGE (ec)-[:IMPLEMENTS]->(s);

RETURN 'seeded metaphors + subsystems + external code + integration points' AS status;
