// @node_id: knowledge-cli-commands
// @label: CLI Commands Reference
// @kind: knowledge
// @description: Complete catalog of mycelium CLI subcommands with semantic metadata for discovery

// Special Commands - Non-Protocol Operations

// Atom 1: bootstrap command
MERGE (c:CLICommand {node_id: 'cmd-bootstrap'})
SET c.label = 'mycelium bootstrap',
    c.name = 'bootstrap',
    c.description = 'Load Protocols and Knowledge from graph/*.cypher files into graph. Idempotent node creation.',
    c.usage = 'mycelium [--target <t>] bootstrap',
    c.args = 'none',
    c.target_constraints = 'rw',
    c.category = 'special',
    c.requires_write = true,
    c.example = 'mycelium --target local bootstrap',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 2: start command
MERGE (c:CLICommand {node_id: 'cmd-start'})
SET c.label = 'mycelium start',
    c.name = 'start',
    c.description = 'Arm graph-native heartbeat scheduler. Registers apoc.periodic.repeat inside Neo4j at 10s cadence.',
    c.usage = 'mycelium [--target <t>] start',
    c.args = 'none',
    c.target_constraints = 'rw',
    c.category = 'special',
    c.requires_write = true,
    c.example = 'mycelium --target local start',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 3: stop command
MERGE (c:CLICommand {node_id: 'cmd-stop'})
SET c.label = 'mycelium stop',
    c.name = 'stop',
    c.description = 'Stop all scheduler jobs. Disarm the graph-native heartbeat scheduler.',
    c.usage = 'mycelium [--target <t>] stop',
    c.args = 'none',
    c.target_constraints = 'rw',
    c.category = 'special',
    c.requires_write = true,
    c.example = 'mycelium --target local stop',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 4: dump command
MERGE (c:CLICommand {node_id: 'cmd-dump'})
SET c.label = 'mycelium dump',
    c.name = 'dump',
    c.description = 'Snapshot Neo4j database to ~/mycelium-dumps/ as binary dump. Fast backup and recovery.',
    c.usage = 'mycelium [--target <t>] dump',
    c.args = 'none',
    c.target_constraints = 'rw',
    c.category = 'special',
    c.requires_write = true,
    c.example = 'mycelium --target local dump',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 5: restore command
MERGE (c:CLICommand {node_id: 'cmd-restore'})
SET c.label = 'mycelium restore',
    c.name = 'restore',
    c.description = 'Restore Neo4j database from a binary dump file. Quick recovery from snapshots.',
    c.usage = 'mycelium [--target <t>] restore <dump-file>',
    c.args = 'dump-file (path to .dump file)',
    c.target_constraints = 'rw',
    c.category = 'special',
    c.requires_write = true,
    c.example = 'mycelium --target local restore ~/mycelium-dumps/mycelium-1234567890.dump',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 6: shell command
MERGE (c:CLICommand {node_id: 'cmd-shell'})
SET c.label = 'mycelium shell',
    c.name = 'shell',
    c.description = 'Execute raw Cypher query with fast HTTP transport. Read-only on prod/dev, read-write on local.',
    c.usage = 'mycelium [--target <t>] shell <cypher-query>',
    c.args = 'cypher-query (string)',
    c.target_constraints = 'ro|rw',
    c.category = 'special',
    c.example = 'mycelium --target prod shell "MATCH (p:Protocol) RETURN p.node_id LIMIT 10"',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 7: fork command
MERGE (c:CLICommand {node_id: 'cmd-fork'})
SET c.label = 'mycelium fork',
    c.name = 'fork',
    c.description = 'Fork writable copy from target (dev only) to local. Export, wipe local, reimport.',
    c.usage = 'mycelium fork <target> [--yes]',
    c.args = 'target (dev), --yes (skip confirmation)',
    c.target_constraints = 'rw',
    c.category = 'special',
    c.requires_write = true,
    c.example = 'mycelium fork dev --yes',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 8: inject command
MERGE (c:CLICommand {node_id: 'cmd-inject'})
SET c.label = 'mycelium inject',
    c.name = 'inject',
    c.description = 'Install mycelium capability awareness into a project. Adds .claude/rules and CLAUDE.md section.',
    c.usage = 'mycelium inject [--project <dir>] [--force]',
    c.args = '--project <dir>, --force',
    c.target_constraints = 'ro',
    c.category = 'special',
    c.example = 'mycelium inject --project /path/to/proj --force',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Protocol Commands - Routed Through Graph

// Atom 9: ask command
MERGE (c:CLICommand {node_id: 'cmd-ask'})
SET c.label = 'mycelium ask',
    c.name = 'ask',
    c.description = 'Semantic search across Prompt/Concept/Atom nodes. Returns top matches by embedding similarity.',
    c.usage = 'mycelium [--target <t>] ask "<question>"',
    c.args = 'question (string)',
    c.target_constraints = 'ro|rw',
    c.category = 'protocol',
    c.example = 'mycelium --target prod ask "how do I fork dev"',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 10: status command
MERGE (c:CLICommand {node_id: 'cmd-status'})
SET c.label = 'mycelium status',
    c.name = 'status',
    c.description = 'Graph vitals: autonomous score, active invariants, unhealthy invariants, pending proposals, heartbeat state.',
    c.usage = 'mycelium [--target <t>] status',
    c.args = 'none',
    c.target_constraints = 'ro|rw',
    c.category = 'protocol',
    c.example = 'mycelium --target prod status',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 11: health command
MERGE (c:CLICommand {node_id: 'cmd-health'})
SET c.label = 'mycelium health',
    c.name = 'health',
    c.description = 'Check all active invariant health status. Returns health_status for each invariant.',
    c.usage = 'mycelium [--target <t>] health',
    c.args = 'none',
    c.target_constraints = 'ro|rw',
    c.category = 'protocol',
    c.example = 'mycelium --target prod health',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 12: doctor command
MERGE (c:CLICommand {node_id: 'cmd-doctor'})
SET c.label = 'mycelium doctor',
    c.name = 'doctor',
    c.description = 'Infrastructure health checks. Validates Neo4j connectivity, disk space, memory, Qdrant availability.',
    c.usage = 'mycelium [--target <t>] doctor',
    c.args = 'none',
    c.target_constraints = 'ro|rw',
    c.category = 'protocol',
    c.example = 'mycelium --target prod doctor',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 13: test command
MERGE (c:CLICommand {node_id: 'cmd-test'})
SET c.label = 'mycelium test',
    c.name = 'test',
    c.description = 'Run all ClaimTest nodes. Reports pass/fail status and test coverage.',
    c.usage = 'mycelium [--target <t>] test',
    c.args = 'none',
    c.target_constraints = 'ro|rw',
    c.category = 'protocol',
    c.example = 'mycelium --target prod test',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 14: swarm command
MERGE (c:CLICommand {node_id: 'cmd-swarm'})
SET c.label = 'mycelium swarm',
    c.name = 'swarm',
    c.description = 'Dispatch parallel Cypher workers from seed prompt. Zero LLM cost reasoning. Default health sweep if no prompt.',
    c.usage = 'mycelium [--target <t>] swarm [--from-prompt "<task>"]',
    c.args = '--from-prompt <task> (optional)',
    c.target_constraints = 'rw',
    c.category = 'protocol',
    c.requires_write = true,
    c.example = 'mycelium --target local swarm --from-prompt "find all unhealthy invariants"',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 15: verify command
MERGE (c:CLICommand {node_id: 'cmd-verify'})
SET c.label = 'mycelium verify',
    c.name = 'verify',
    c.description = 'Verify a species file (DNA). Check structure, hash, and lineage.',
    c.usage = 'mycelium [--target <t>] verify <dna>',
    c.args = 'dna (species identifier)',
    c.target_constraints = 'ro|rw',
    c.category = 'protocol',
    c.example = 'mycelium --target prod verify 07d7a5360835e19d',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 16: audit command
MERGE (c:CLICommand {node_id: 'cmd-audit'})
SET c.label = 'mycelium audit',
    c.name = 'audit',
    c.description = 'Walk the lineage of a species (DNA) or all species if no DNA specified. Show minting history.',
    c.usage = 'mycelium [--target <t>] audit [<dna>]',
    c.args = 'dna (optional, species identifier)',
    c.target_constraints = 'ro|rw',
    c.category = 'protocol',
    c.example = 'mycelium --target prod audit 07d7a5360835e19d',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 17: tip command
MERGE (c:CLICommand {node_id: 'cmd-tip'})
SET c.label = 'mycelium tip',
    c.name = 'tip',
    c.description = 'Show canonical tip DNA. Returns the most recent species minted.',
    c.usage = 'mycelium [--target <t>] tip',
    c.args = 'none',
    c.target_constraints = 'ro|rw',
    c.category = 'protocol',
    c.example = 'mycelium --target prod tip',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 18: target command
MERGE (c:CLICommand {node_id: 'cmd-target'})
SET c.label = 'mycelium target',
    c.name = 'target',
    c.description = 'Print currently selected target and its connection URL. Shows all available targets from config.',
    c.usage = 'mycelium target',
    c.args = 'none',
    c.target_constraints = 'ro|rw',
    c.category = 'special',
    c.example = 'mycelium target',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 19: help command
MERGE (c:CLICommand {node_id: 'cmd-help'})
SET c.label = 'mycelium help',
    c.name = 'help',
    c.description = 'Show CLI help text. Lists all subcommands, flags, available targets, and usage examples.',
    c.usage = 'mycelium help',
    c.args = 'none',
    c.target_constraints = 'ro|rw',
    c.category = 'special',
    c.example = 'mycelium help',
    c.updated_at = datetime()
RETURN c.node_id AS result;

// Atom 20: Create onboarding workflow relationship
MATCH (cmd:CLICommand WHERE cmd.node_id IN [
  'cmd-target', 'cmd-bootstrap', 'cmd-start', 'cmd-ask', 'cmd-status', 'cmd-health'
])
MERGE (wf:Workflow {node_id: 'workflow-onboarding'})
SET wf.label = 'Mycelium Onboarding',
    wf.description = 'Sequence of commands for first-time setup and graph health check'
WITH cmd, wf
MERGE (wf)-[:INCLUDES]->(cmd)
RETURN count(*) AS commands_linked;

// Atom 21: Create diagnostic workflow relationship
MATCH (cmd:CLICommand WHERE cmd.node_id IN [
  'cmd-target', 'cmd-status', 'cmd-health', 'cmd-doctor', 'cmd-test'
])
MERGE (wf:Workflow {node_id: 'workflow-diagnostics'})
SET wf.label = 'Mycelium Diagnostics',
    wf.description = 'Commands for troubleshooting system health and infrastructure'
WITH cmd, wf
MERGE (wf)-[:INCLUDES]->(cmd)
RETURN count(*) AS commands_linked;

// Atom 22: Create development workflow relationship
MATCH (cmd:CLICommand WHERE cmd.node_id IN [
  'cmd-fork', 'cmd-bootstrap', 'cmd-shell', 'cmd-ask', 'cmd-swarm', 'cmd-test'
])
MERGE (wf:Workflow {node_id: 'workflow-development'})
SET wf.label = 'Mycelium Development',
    wf.description = 'Commands for graph development, testing, and query execution'
WITH cmd, wf
MERGE (wf)-[:INCLUDES]->(cmd)
RETURN count(*) AS commands_linked;

// Atom 23: Create backup/recovery workflow relationship
MATCH (cmd:CLICommand WHERE cmd.node_id IN [
  'cmd-dump', 'cmd-restore', 'cmd-fork', 'cmd-bootstrap'
])
MERGE (wf:Workflow {node_id: 'workflow-backup-recovery'})
SET wf.label = 'Mycelium Backup & Recovery',
    wf.description = 'Commands for backing up, restoring, and syncing graph state'
WITH cmd, wf
MERGE (wf)-[:INCLUDES]->(cmd)
RETURN count(*) AS commands_linked;

// Atom 24: Create species/version tracking workflow
MATCH (cmd:CLICommand WHERE cmd.node_id IN [
  'cmd-verify', 'cmd-audit', 'cmd-tip'
])
MERGE (wf:Workflow {node_id: 'workflow-species-tracking'})
SET wf.label = 'Mycelium Species Tracking',
    wf.description = 'Commands for verifying, auditing, and tracking graph species (versions)'
WITH cmd, wf
MERGE (wf)-[:INCLUDES]->(cmd)
RETURN count(*) AS commands_linked;

// Atom 25: Link each CLICommand to its Protocol counterpart (if exists)
MATCH (cmd:CLICommand WHERE cmd.category = 'protocol')
MATCH (proto:Protocol {node_id: 'protocol-' + cmd.name})
MERGE (cmd)-[:DISPATCHES_TO]->(proto)
RETURN count(*) AS protocol_links;

// Atom 26: Summary stats
MATCH (c:CLICommand)
WITH count(c) AS total_cmds,
     size([cmd IN collect(c) WHERE cmd.category = 'special']) AS special_cmds,
     size([cmd IN collect(c) WHERE cmd.category = 'protocol']) AS protocol_cmds
RETURN 'cli-commands|total:' + toString(total_cmds) + '|special:' + toString(special_cmds) + '|protocol:' + toString(protocol_cmds) AS result;
