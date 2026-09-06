// @node_id: protocol-commands-heal
// @label: "Commands Heal"
// ============================================================================
// Protocol: Commands Heal
// ============================================================================
// Fixes two gaps surfaced by commands-wire.cypher:
//
//   1. Eight shell-runner commands (adopt, import, mint, proof-of-merge,
//      register-source, search, sign, witness-init) point at .sh scripts that
//      wrap .cypher protocols, but the matching :Protocol nodes were never
//      seeded. MERGE them here so commands-wire's INVOKES pass can find them.
//
//   2. Alias pairs (q↔query, whoami↔know-thyself, swarms↔swarm-status,
//      --help↔help, -h↔help) live only in the bash dispatcher, not as graph
//      rows. Create explicit :ALIAS_OF edges between the existing Command
//      nodes so NL dispatch and compose-reply can reason about synonyms.
//
// Idempotent (MERGE only). Safe to re-run.
// ============================================================================


// --- Part 1: Missing Protocol nodes for shell-runner commands --------------
// These protocols exist as .cypher files on disk but were never registered
// as :Protocol graph rows. Create the rows with minimal metadata so the
// INVOKES wiring can find them. The atomize-protocol.py runner can later
// atomize them if needed.

MERGE (p:Protocol {node_id: 'protocol-adopt-node'})
SET p.label = 'Adopt Node',
    p.description = 'Adopt an imported node as a first-class citizen. Promotes :Imported nodes to owned state after validation.',
    p.source_file = 'graph/protocols/adopt-node.cypher',
    p.file_type = 'protocol';

MERGE (p:Protocol {node_id: 'protocol-import-external'})
SET p.label = 'Import External',
    p.description = 'Import nodes from an external authorized :Source. Labels them :Imported until adoption.',
    p.source_file = 'graph/protocols/import-external.cypher',
    p.file_type = 'protocol';

MERGE (p:Protocol {node_id: 'protocol-species-mint'})
SET p.label = 'Species Mint',
    p.description = 'Mint a new :Species candidate node committing to the current graph state via manifest_root.',
    p.source_file = 'graph/protocols/species-mint.cypher',
    p.file_type = 'protocol';

MERGE (p:Protocol {node_id: 'protocol-validate-merge'})
SET p.label = 'Validate Merge',
    p.description = 'Write-gate protocol. Runs invariants + tests + merkle inside a transaction. apoc.util.validate throws on failure.',
    p.source_file = 'graph/protocols/validate-merge.cypher',
    p.file_type = 'protocol';

MERGE (p:Protocol {node_id: 'protocol-source-register'})
SET p.label = 'Source Register',
    p.description = 'Register an external graph as an authorized :Source. Records public_key, schema_version, description.',
    p.source_file = 'graph/protocols/source-register.cypher',
    p.file_type = 'protocol';

MERGE (p:Protocol {node_id: 'protocol-semantic-query'})
SET p.label = 'Semantic Query',
    p.description = 'Embed a text query via Ollama, vector-search node_embeddings index, return top matches.',
    p.source_file = 'graph/runner/semantic-query.sh',
    p.file_type = 'protocol';

MERGE (p:Protocol {node_id: 'protocol-witness-sign'})
SET p.label = 'Witness Sign',
    p.description = 'Sign a species candidate with a witness ed25519 key. Produces a :WitnessSignature.',
    p.source_file = 'graph/protocols/species-sign.cypher',
    p.file_type = 'protocol';

MERGE (p:Protocol {node_id: 'protocol-witness-init'})
SET p.label = 'Witness Init',
    p.description = 'Initialize a new witness. Generates ed25519 keypair, registers :Witness node with public key.',
    p.source_file = 'graph/runner/witness-init.sh',
    p.file_type = 'protocol';


// --- Part 1b: Wire the newly-seeded Protocols to their Commands -----------

MATCH (c:Command {name: 'adopt'})
MATCH (p:Protocol {node_id: 'protocol-adopt-node'})
MERGE (c)-[:INVOKES]->(p);

MATCH (c:Command {name: 'import'})
MATCH (p:Protocol {node_id: 'protocol-import-external'})
MERGE (c)-[:INVOKES]->(p);

MATCH (c:Command {name: 'mint'})
MATCH (p:Protocol {node_id: 'protocol-species-mint'})
MERGE (c)-[:INVOKES]->(p);

MATCH (c:Command {name: 'proof-of-merge'})
MATCH (p:Protocol {node_id: 'protocol-validate-merge'})
MERGE (c)-[:INVOKES]->(p);

MATCH (c:Command {name: 'register-source'})
MATCH (p:Protocol {node_id: 'protocol-source-register'})
MERGE (c)-[:INVOKES]->(p);

MATCH (c:Command {name: 'search'})
MATCH (p:Protocol {node_id: 'protocol-semantic-query'})
MERGE (c)-[:INVOKES]->(p);

MATCH (c:Command {name: 'sign'})
MATCH (p:Protocol {node_id: 'protocol-witness-sign'})
MERGE (c)-[:INVOKES]->(p);

MATCH (c:Command {name: 'witness-init'})
MATCH (p:Protocol {node_id: 'protocol-witness-init'})
MERGE (c)-[:INVOKES]->(p);


// --- Part 2: Alias rows for dispatcher-only aliases -----------------------
// The bash dispatcher case-block treats these as synonyms, but only the
// primary form exists as a :Command row. Create the alias rows as first-
// class Commands that point at their primary via :ALIAS_OF. This makes
// every alias NL-discoverable and compose-reply can collapse them.

MERGE (c:Command {name: 'query'})
ON CREATE SET c.node_id = 'command-query',
              c.description = 'Alias of q. Ad-hoc cypher query with pretty-printed output.',
              c.usage = 'mycelium query <cypher>',
              c.example = 'mycelium query "MATCH (n:Invariant) RETURN count(n)"',
              c.category = 'introspect',
              c.runner = 'builtin:cmd_q',
              c.file_type = 'command',
              c.is_alias = true;

MERGE (c:Command {name: 'whoami'})
ON CREATE SET c.node_id = 'command-whoami',
              c.description = 'Alias of know-thyself. Prints the graph self-report — who am I, what do I know.',
              c.usage = 'mycelium whoami',
              c.example = 'mycelium whoami',
              c.category = 'introspect',
              c.runner = 'builtin:cmd_know_thyself',
              c.file_type = 'command',
              c.is_alias = true;

MERGE (c:Command {name: 'swarms'})
ON CREATE SET c.node_id = 'command-swarms',
              c.description = 'Alias of swarm-status. List recent swarms or inspect one.',
              c.usage = 'mycelium swarms [swarm_id]',
              c.example = 'mycelium swarms',
              c.category = 'swarm',
              c.runner = 'builtin:cmd_swarm_status',
              c.file_type = 'command',
              c.is_alias = true;

// Wire alias → primary both directions
MATCH (a:Command {name: 'query'}), (b:Command {name: 'q'})
MERGE (a)-[:ALIAS_OF]->(b)
MERGE (b)-[:ALIAS_OF]->(a);

MATCH (a:Command {name: 'whoami'}), (b:Command {name: 'know-thyself'})
MERGE (a)-[:ALIAS_OF]->(b)
MERGE (b)-[:ALIAS_OF]->(a);

MATCH (a:Command {name: 'swarms'}), (b:Command {name: 'swarm-status'})
MERGE (a)-[:ALIAS_OF]->(b)
MERGE (b)-[:ALIAS_OF]->(a);


// --- Summary -------------------------------------------------------------
MATCH (c:Command) WITH count(c) AS total_commands
OPTIONAL MATCH ()-[r1:INVOKES]->(:Protocol)
WITH total_commands, count(r1) AS invoke_count
OPTIONAL MATCH (:Command)-[r2:ALIAS_OF]-(:Command)
RETURN total_commands,
       invoke_count AS total_invokes,
       count(r2)/2 AS total_alias_pairs,
       'commands-heal complete' AS status;
