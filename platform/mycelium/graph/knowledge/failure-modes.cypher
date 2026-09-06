// @node_id: knowledge-failure-modes
// @label: Known Failure Modes and Diagnostics
// @kind: knowledge
// @description: Catalog of known system failures, root causes, symptoms, and fixes. Indexed for semantic discovery when teammates encounter errors.

// Atom 1: Port 7687 already in use
MERGE (f:FailureMode {node_id: 'failure-neo4j-port-7687-in-use'})
SET f.label = 'Neo4j Port 7687 Already In Use',
    f.symptom_pattern = 'Connection refused|address already in use|7687',
    f.symptom_example = 'cypher-shell -a bolt://localhost:7687: Connection refused (Connection refused)',
    f.root_cause = 'Another Neo4j instance or old Docker container holds port 7687',
    f.fix_command = 'lsof -i :7687 | grep LISTEN | awk "{print $2}" | xargs kill -9 || brew services stop neo4j',
    f.fix_explanation = 'Identifies and terminates the process holding the port. On macOS, Homebrew services auto-restart may hold the port.',
    f.affected_os = 'all',
    f.first_seen = datetime(),
    f.updated_at = datetime()
RETURN f.node_id AS result;

// Atom 2: Homebrew not installed on macOS
MERGE (f:FailureMode {node_id: 'failure-brew-not-installed-macos'})
SET f.label = 'Homebrew Not Installed',
    f.symptom_pattern = 'brew: command not found|no such file|homebrew',
    f.symptom_example = 'bash install-deps.sh: line 5: brew: command not found',
    f.root_cause = 'Homebrew package manager not installed on macOS system',
    f.fix_command = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
    f.fix_explanation = 'Installs Homebrew from official script. Required for all macOS package management in setup.',
    f.affected_os = 'macos',
    f.first_seen = datetime(),
    f.updated_at = datetime()
RETURN f.node_id AS result;

// Atom 3: Bash too old on macOS
MERGE (f:FailureMode {node_id: 'failure-bash-too-old-macos'})
SET f.label = 'Bash Version Too Old',
    f.symptom_pattern = 'bad substitution|unexpected syntax|bash.*3\\.2',
    f.symptom_example = 'setup-team.sh: line 42: ${var[@]}: bad substitution',
    f.root_cause = 'macOS ships bash 3.2 (2007), which lacks modern features like associative arrays and string manipulation',
    f.fix_command = 'brew install bash && exec /opt/homebrew/bin/bash setup-team.sh',
    f.fix_explanation = 'Installs bash 5+ via Homebrew, then re-invokes the script with the new shell. Homebrew installs to /opt/homebrew on M-series Macs, /usr/local on Intel.',
    f.affected_os = 'macos',
    f.first_seen = datetime(),
    f.updated_at = datetime()
RETURN f.node_id AS result;

// Atom 4: cypher-shell not on PATH
MERGE (f:FailureMode {node_id: 'failure-cypher-shell-not-on-path'})
SET f.label = 'cypher-shell Not Found',
    f.symptom_pattern = 'command not found: cypher-shell|cypher-shell.*not in|PATH',
    f.symptom_example = 'bash: cypher-shell: command not found',
    f.root_cause = 'Neo4j installed but shell symlink missing or not in PATH. Neo4j package installs the binary but does not auto-link it.',
    f.fix_command = 'brew link neo4j || apt install cypher-shell',
    f.fix_explanation = 'On macOS, `brew link` symlinks Neo4j binaries to /usr/local/bin. On Linux, apt installs the cypher-shell package directly.',
    f.affected_os = 'all',
    f.first_seen = datetime(),
    f.updated_at = datetime()
RETURN f.node_id AS result;

// Atom 5: Cloudflare WARP blocking remote Neo4j
MERGE (f:FailureMode {node_id: 'failure-pulse-unreachable-warp'})
SET f.label = 'Cloudflare WARP Blocking Remote Neo4j',
    f.symptom_pattern = 'timeout|hangs|unreachable|5\\.78\\.206\\.137.*refused',
    f.symptom_example = 'cypher-shell -a bolt://5.78.206.137:7699 ... hangs indefinitely then times out',
    f.root_cause = 'Cloudflare WARP VPN enabled. WARP routes all traffic through Cloudflare infrastructure, which blocks direct Hetzner server access.',
    f.fix_command = 'open -a /Applications/Cloudflare\\ WARP.app && click toggle off',
    f.fix_explanation = 'Disable Cloudflare WARP via menu bar toggle. Once disabled, direct TCP connections to Hetzner servers (5.78.206.137) work normally. Re-enable after work if needed.',
    f.affected_os = 'macos',
    f.first_seen = datetime(),
    f.updated_at = datetime()
RETURN f.node_id AS result;

// Atom 6: Ollama daemon not running
MERGE (f:FailureMode {node_id: 'failure-ollama-not-running'})
SET f.label = 'Ollama Daemon Not Running',
    f.symptom_pattern = 'connection refused|127\\.0\\.0\\.1:11434|ollama.*not running',
    f.symptom_example = 'mycelium ask "query": error: connection refused to 127.0.0.1:11434',
    f.root_cause = 'Ollama embedding service not started. Embedding operations require the Ollama daemon (nomic-embed-text model).',
    f.fix_command = 'brew services start ollama || systemctl start ollama',
    f.fix_explanation = 'On macOS, starts Ollama via Homebrew services. On Linux, starts via systemd. Ollama runs at 127.0.0.1:11434 by default.',
    f.affected_os = 'all',
    f.first_seen = datetime(),
    f.updated_at = datetime()
RETURN f.node_id AS result;

// Atom 7: Qdrant collection missing
MERGE (f:FailureMode {node_id: 'failure-qdrant-collection-missing'})
SET f.label = 'Qdrant Collection Not Found',
    f.symptom_pattern = 'collection not found|mycelium-embeddings|no such collection',
    f.symptom_example = 'mycelium ask "query": error: collection mycelium-embeddings not found at 127.0.0.1:6333',
    f.root_cause = 'Qdrant running but the semantic search collection (mycelium-embeddings) has not been created yet.',
    f.fix_command = 'curl -X PUT http://127.0.0.1:6333/collections/mycelium-embeddings -H "Content-Type: application/json" -d \'{"vectors":{"size":768,"distance":"Cosine"}}\'',
    f.fix_explanation = 'Creates a new Qdrant collection with 768-dimensional Cosine distance metric (matching Ollama nomic-embed-text output). One-time setup per Qdrant instance.',
    f.affected_os = 'all',
    f.first_seen = datetime(),
    f.updated_at = datetime()
RETURN f.node_id AS result;

// Atom 8: secrets.env insecure permissions
MERGE (f:FailureMode {node_id: 'failure-secrets-env-wrong-perms'})
SET f.label = 'Secrets File Has Insecure Permissions',
    f.symptom_pattern = 'insecure permissions|secrets\\.env.*644|world readable',
    f.symptom_example = 'mycelium bootstrap: warning: ~/.mycelium/secrets.env has insecure permissions (644)',
    f.root_cause = 'Configuration file created with default umask, exposing secrets to other users on the system.',
    f.fix_command = 'chmod 600 ~/.mycelium/secrets.env',
    f.fix_explanation = 'Sets file to user-read-only (600). Other users on the system cannot read it. Apply before first use or immediately after warning.',
    f.affected_os = 'all',
    f.first_seen = datetime(),
    f.updated_at = datetime()
RETURN f.node_id AS result;

// Atom 9: CLI not on PATH
MERGE (f:FailureMode {node_id: 'failure-global-cli-not-on-path'})
SET f.label = 'Mycelium CLI Not on PATH',
    f.symptom_pattern = 'mycelium.*command not found|not in.*PATH',
    f.symptom_example = 'mycelium status: command not found (after setup-team.sh completes)',
    f.root_cause = 'setup-team.sh installs to ~/.local/bin but PATH has not been updated, or shell session not restarted.',
    f.fix_command = 'export PATH="$HOME/.local/bin:$PATH" && source ~/.bashrc && mycelium status',
    f.fix_explanation = 'Adds ~/.local/bin to PATH in current shell, reloads shell config, then tests. Typically needs terminal restart for changes to persist across sessions.',
    f.affected_os = 'all',
    f.first_seen = datetime(),
    f.updated_at = datetime()
RETURN f.node_id AS result;

// Atom 10: Claude Code skills directory missing
MERGE (f:FailureMode {node_id: 'failure-skill-dir-missing'})
SET f.label = 'Claude Code Skills Directory Missing',
    f.symptom_pattern = 'skills directory|~/.claude|not found|no such file',
    f.symptom_example = 'setup-team.sh: warning: ~/.claude directory does not exist. Cannot install skills.',
    f.root_cause = 'Teammate does not use Claude Code yet (legitimate), or first-time setup not completed. Skills require ~/.claude/skills/ directory.',
    f.fix_command = 'mkdir -p ~/.claude/skills && bash skills/install.sh',
    f.fix_explanation = 'Creates the directory structure and re-runs skill installation. For teammates not using Claude Code, this is optional (they will not use graph-native commands).',
    f.affected_os = 'all',
    f.first_seen = datetime(),
    f.updated_at = datetime()
RETURN f.node_id AS result;

// Atom 11: Link failure modes to OnboardingStep nodes (soft dependency)
MATCH (f:FailureMode WHERE f.node_id IN [
  'failure-brew-not-installed-macos',
  'failure-bash-too-old-macos',
  'failure-cypher-shell-not-on-path',
  'failure-neo4j-port-7687-in-use'
])
OPTIONAL MATCH (s:OnboardingStep {node_id: 'step-prereqs'})
WHERE s IS NOT NULL
WITH f, s
MERGE (f)-[:BLOCKS]->(s)
RETURN count(*) AS prereq_blocks;

// Atom 12: Link failure modes to SystemRequirement nodes
MATCH (f:FailureMode WHERE f.affected_os = 'macos' OR f.affected_os = 'all')
OPTIONAL MATCH (o:SystemRequirement {node_id: 'os-macos'})
WHERE o IS NOT NULL
WITH f, o
MERGE (f)-[:AFFECTS]->(o)
RETURN count(*) AS os_links;

// Atom 13: Link embedding-related failures to embedding infrastructure
MATCH (f:FailureMode WHERE f.node_id IN [
  'failure-ollama-not-running',
  'failure-qdrant-collection-missing'
])
OPTIONAL MATCH (cap:Capability {node_id: 'cap-embed-text'})
WHERE cap IS NOT NULL
WITH f, cap
MERGE (f)-[:BLOCKS]->(cap)
RETURN count(*) AS embedding_blocks;

// Atom 14: Create semantic metadata for discovery
MATCH (f:FailureMode)
SET f.discoverable = true,
    f.query_aliases = split(replace(f.symptom_pattern, '|', ', '), ', ')
RETURN count(*) AS alias_count;

// Atom 15: Summary
MATCH (f:FailureMode)
WITH count(f) AS total,
     size([fm IN collect(f) WHERE fm.affected_os = 'all']) AS cross_platform,
     size([fm IN collect(f) WHERE fm.affected_os = 'macos']) AS macos_only,
     size([fm IN collect(f) WHERE fm.affected_os = 'linux']) AS linux_only
RETURN 'failure-modes|total:' + toString(total) + '|cross-platform:' + toString(cross_platform) + '|macos:' + toString(macos_only) + '|linux:' + toString(linux_only) AS result;
