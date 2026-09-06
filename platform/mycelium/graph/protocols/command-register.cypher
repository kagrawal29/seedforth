// @kind: seed
// ============================================================================
// Protocol: Command Register
// ============================================================================
// Seeds Command nodes that describe every operator-level action exposed by
// the `mycelium` CLI. The CLI reads these nodes at runtime — the graph is
// the authoritative source for "what commands exist and how they work".
//
// Each Command has:
//   node_id       'cmd-<name>'
//   name          short name used as the CLI subcommand (e.g. 'status')
//   usage         one-line usage string shown in help
//   description   what it does
//   example       example invocation
//   runner        the shell command to execute (relative to repo root)
//   category      grouping for help output
//   order         display ordering within category
//
// Idempotent by MERGE. Re-running this protocol updates descriptions and
// runners without creating duplicates.
// ============================================================================

MERGE (c:Command {node_id: 'cmd-help'})
SET c.name = 'help', c.order = 10, c.category = 'info',
    c.usage = 'mycelium help',
    c.description = 'List all commands registered in the graph.',
    c.example = 'mycelium help',
    c.runner = 'mycelium__builtin_help',
    c.file_type = 'command';

MERGE (c:Command {node_id: 'cmd-status'})
SET c.name = 'status', c.order = 20, c.category = 'info',
    c.usage = 'mycelium status',
    c.description = 'Current chain head, invariant health, test status, pending candidates, Merkle root.',
    c.example = 'mycelium status',
    c.runner = 'mycelium__builtin_status',
    c.file_type = 'command';

MERGE (c:Command {node_id: 'cmd-heartbeat'})
SET c.name = 'breathe', c.order = 30, c.category = 'liveness',
    c.usage = 'mycelium breathe',
    c.description = 'Run the heartbeat protocol once. (Loop: graph/runner/heartbeat-loop.sh)',
    c.example = 'mycelium breathe',
    c.runner = 'docker exec -i mycelium-neo4j-local cypher-shell -u neo4j -p localtest12 --encryption false < graph/protocols/heartbeat.cypher',
    c.file_type = 'command';

MERGE (c:Command {node_id: 'cmd-verify'})
SET c.name = 'verify', c.order = 40, c.category = 'integrity',
    c.usage = 'mycelium verify',
    c.description = 'Run merkle-properties + invariants + tests. Exits non-zero if anything is unhealthy.',
    c.example = 'mycelium verify',
    c.runner = 'mycelium__builtin_verify',
    c.file_type = 'command';

MERGE (c:Command {node_id: 'cmd-proof-of-merge'})
SET c.name = 'proof-of-merge', c.order = 50, c.category = 'write',
    c.usage = 'mycelium proof-of-merge <file.cypher>',
    c.description = 'Dry-run a proposed cypher mutation against the current state. Applies inside a transaction that rolls back regardless of outcome. Answers: "would this PR pass CI?"',
    c.example = 'mycelium proof-of-merge pr/my-change.cypher',
    c.runner = 'bash graph/runner/validate-merge.sh',
    c.file_type = 'command';

MERGE (c:Command {node_id: 'cmd-mint'})
SET c.name = 'mint', c.order = 60, c.category = 'chain',
    c.usage = 'mycelium mint',
    c.description = 'Mint a candidate species from the current graph state. No-op if no drift.',
    c.example = 'mycelium mint',
    c.runner = 'bash graph/runner/species-mint.sh',
    c.file_type = 'command';

MERGE (c:Command {node_id: 'cmd-sign'})
SET c.name = 'sign', c.order = 70, c.category = 'chain',
    c.usage = 'mycelium sign <candidate-id> <witness-alias>',
    c.description = 'Sign a candidate species with your local ed25519 key.',
    c.example = 'mycelium sign species-candidate-abc123 Mycelium',
    c.runner = 'bash graph/runner/witness-sign.sh',
    c.file_type = 'command';

MERGE (c:Command {node_id: 'cmd-canonize'})
SET c.name = 'canonize', c.order = 80, c.category = 'chain',
    c.usage = 'mycelium canonize <candidate-id>',
    c.description = 'Verify signatures + promote a signed candidate to canonical. Advances chain head.',
    c.example = 'mycelium canonize species-candidate-abc123',
    c.runner = 'mycelium__builtin_canonize',
    c.file_type = 'command';

MERGE (c:Command {node_id: 'cmd-witness-init'})
SET c.name = 'witness-init', c.order = 90, c.category = 'chain',
    c.usage = 'mycelium witness-init <alias>',
    c.description = 'Generate an ed25519 keypair and register as a Witness node.',
    c.example = 'mycelium witness-init Mycelium',
    c.runner = 'bash graph/runner/witness-init.sh',
    c.file_type = 'command';

MERGE (c:Command {node_id: 'cmd-import'})
SET c.name = 'import', c.order = 100, c.category = 'federation',
    c.usage = 'mycelium import <source-alias> <bundle.cypher>',
    c.description = 'Import an external graph bundle under a namespaced Source. Runs validate-merge internally.',
    c.example = 'mycelium import ember imports/ember/2026-04-16-batch.cypher',
    c.runner = 'bash graph/runner/import-external.sh',
    c.file_type = 'command';

MERGE (c:Command {node_id: 'cmd-adopt'})
SET c.name = 'adopt', c.order = 110, c.category = 'federation',
    c.usage = 'mycelium adopt <node-id> <your-alias>',
    c.description = 'Promote an imported node to a full citizen. Runs validate-merge scoped to the node.',
    c.example = 'mycelium adopt ember:user-rajesh Kshitiz',
    c.runner = 'bash graph/runner/adopt-node.sh',
    c.file_type = 'command';

MERGE (c:Command {node_id: 'cmd-register-source'})
SET c.name = 'register-source', c.order = 120, c.category = 'federation',
    c.usage = 'mycelium register-source <alias> <public-key> [schema] [desc]',
    c.description = 'Register an external Source with its public key.',
    c.example = 'mycelium register-source ember 48aa3825... v1 "Ember LinkedIn graph"',
    c.runner = 'bash graph/runner/source-register.sh',
    c.file_type = 'command';

MERGE (c:Command {node_id: 'cmd-semantic-query'})
SET c.name = 'search', c.order = 130, c.category = 'query',
    c.usage = 'mycelium search <text query>',
    c.description = 'Semantic similarity search over node embeddings. Returns top 10.',
    c.example = 'mycelium search "auth token handling"',
    c.runner = 'bash graph/runner/semantic-query.sh',
    c.file_type = 'command';

MERGE (c:Command {node_id: 'cmd-export'})
SET c.name = 'export', c.order = 140, c.category = 'state',
    c.usage = 'mycelium export',
    c.description = 'Regenerate graph-state.cypher from current Neo4j state (skip-key aware).',
    c.example = 'mycelium export',
    c.runner = 'bash graph/runner/export-graph-state.sh',
    c.file_type = 'command';

MERGE (c:Command {node_id: 'cmd-embed'})
SET c.name = 'embed', c.order = 150, c.category = 'query',
    c.usage = 'mycelium embed',
    c.description = 'Regenerate embeddings for any nodes whose leaf_hash changed. O(dirty nodes).',
    c.example = 'mycelium embed',
    c.runner = 'bash graph/runner/embed-dirty.sh',
    c.file_type = 'command';

RETURN count(*) AS commands_registered;
