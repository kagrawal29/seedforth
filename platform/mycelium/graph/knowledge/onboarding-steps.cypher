// Mycelium Team Onboarding — Step Sequence
// @node_id: workflow-onboarding
// Creates a linked chain of OnboardingStep nodes guiding teammates from fresh machine to full prod/dev access
// and a writable local copy of the graph.

// Step 1: Check prerequisites
MERGE (s:OnboardingStep {node_id: 'step-prereqs'})
SET s.label = 'Check Prerequisites',
    s.ordinal = 10,
    s.description = 'Verify your machine has OS, shell, and tool support. Run doctor.sh to check Neo4j, Cypher Shell, and Python 3.',
    s.action_command = 'bash doctor.sh',
    s.verification_command = 'which neo4j && which cypher-shell && python3 --version',
    s.expected_outcome = 'All three tools (neo4j, cypher-shell, python3) are installed and accessible in PATH.',
    s.target_os = 'all',
    s.required_tools = 'bash,uname',
    s.updated_at = datetime();

// Step 2: Clone the repository
MERGE (s:OnboardingStep {node_id: 'step-clone'})
SET s.label = 'Clone Repository',
    s.ordinal = 20,
    s.description = 'Clone the maverick repo which contains graph definitions, setup scripts, and documentation.',
    s.action_command = 'git clone https://github.com/Qubit-Capital/maverick.git && cd maverick',
    s.verification_command = 'ls -la | grep -E "setup-team.sh|install-deps.sh"',
    s.expected_outcome = 'maverick folder exists with setup-team.sh and install-deps.sh scripts.',
    s.target_os = 'all',
    s.required_tools = 'git',
    s.updated_at = datetime();

// Step 3: Run team setup
MERGE (s:OnboardingStep {node_id: 'step-setup'})
SET s.label = 'Run Team Setup',
    s.ordinal = 30,
    s.description = 'Interactive setup that asks for forest alias (team name), prod/dev passwords (from 1Password), and runs connectivity smoke tests to prod/dev.',
    s.action_command = 'bash setup-team.sh',
    s.verification_command = 'test -f ~/.mycelium/secrets.env && stat -c %a ~/.mycelium/secrets.env | grep -E "^600$|^0600$"',
    s.expected_outcome = '~/.mycelium/secrets.env exists with permissions 0600. Passwords are stored securely.',
    s.target_os = 'all',
    s.required_tools = 'bash,openssl',
    s.updated_at = datetime();

// Step 4: Verify connectivity to production
MERGE (s:OnboardingStep {node_id: 'step-verify-prod'})
SET s.label = 'Verify Production Access',
    s.ordinal = 40,
    s.description = 'Test read-only connection to prod graph on pulse-server. Confirms you can reach the canonical state.',
    s.action_command = 'source ~/.mycelium/secrets.env && cypher-shell -a bolt://5.78.206.137:7699 -u team -p "$MYCELIUM_PROD_PASS" "RETURN 1"',
    s.verification_command = 'mycelium --target prod shell "MATCH (n:Protocol) RETURN count(n) as protocol_count" | grep -v "protocol_count" | tail -1 | grep -E "^[0-9]+"',
    s.expected_outcome = 'Query returns protocol count (50+). You have read-only access to prod graph.',
    s.target_os = 'all',
    s.required_tools = 'cypher-shell',
    s.updated_at = datetime();

// Step 5: Verify connectivity to development
MERGE (s:OnboardingStep {node_id: 'step-verify-dev'})
SET s.label = 'Verify Development Access',
    s.ordinal = 50,
    s.description = 'Test read-only connection to dev graph on pulse-server. Confirms you can reach the development/experimental state.',
    s.action_command = 'source ~/.mycelium/secrets.env && cypher-shell -a bolt://5.78.206.137:7698 -u team -p "$MYCELIUM_DEV_PASS" "RETURN 1"',
    s.verification_command = 'mycelium --target dev shell "MATCH (n) RETURN count(n) as total_nodes" | grep -v "total_nodes" | tail -1 | grep -E "^[0-9]+"',
    s.expected_outcome = 'Query returns node count (around 9000+). You have read-only access to dev graph.',
    s.target_os = 'all',
    s.required_tools = 'cypher-shell',
    s.updated_at = datetime();

// Step 6: Install local dependencies
MERGE (s:OnboardingStep {node_id: 'step-install-local-deps'})
SET s.label = 'Install Local Dependencies',
    s.ordinal = 60,
    s.description = 'One-shot installer for local Neo4j 2026.03.1, APOC plugin, Ollama (local embeddings), and Qdrant (semantic index). Creates a writable sandbox on your laptop.',
    s.action_command = 'bash install-deps.sh',
    s.verification_command = 'neo4j status 2>/dev/null | grep -i running && curl -s http://localhost:11434/api/tags >/dev/null && echo "success"',
    s.expected_outcome = 'Neo4j runs on bolt://localhost:7687 with APOC. Ollama and Qdrant ready for embeddings.',
    s.target_os = 'all',
    s.required_tools = 'bash,brew',
    s.updated_at = datetime();

// Step 7: Bootstrap local graph
MERGE (s:OnboardingStep {node_id: 'step-bootstrap-local'})
SET s.label = 'Bootstrap Local Graph',
    s.ordinal = 70,
    s.description = 'Load all Protocol nodes from graph/protocols/*.cypher into local Neo4j. Initializes the autonomous heartbeat and triggers.',
    s.action_command = 'mycelium --target local bootstrap',
    s.verification_command = 'mycelium --target local shell "MATCH (p:Protocol) RETURN count(p) as protocols" | tail -1',
    s.expected_outcome = 'Local graph has 50+ Protocol nodes. Bootstrap outputs "atoms decomposed" and "triggers & invariants loaded".',
    s.target_os = 'all',
    s.required_tools = 'mycelium',
    s.updated_at = datetime();

// Step 8: Fork dev to local
MERGE (s:OnboardingStep {node_id: 'step-fork-dev'})
SET s.label = 'Fork Dev Graph to Local',
    s.ordinal = 80,
    s.description = 'Clone the dev graph state into local, creating a writable checkpoint. Enables safe experimentation and testing.',
    s.action_command = 'mycelium fork dev --yes',
    s.verification_command = 'mycelium --target local shell "MATCH (b:Being) RETURN b.label" | grep -i mycelium',
    s.expected_outcome = 'Local graph now has 9000+ nodes, matching dev state. You can write, test, and see results safely.',
    s.target_os = 'all',
    s.required_tools = 'mycelium',
    s.updated_at = datetime();

// Step 9: Make project mycelium-aware
MERGE (s:OnboardingStep {node_id: 'step-inject-project'})
SET s.label = 'Inject Mycelium into Your Project',
    s.ordinal = 90,
    s.description = 'Enable mycelium CLI in your own projects. Adds graph awareness to any repo so you can query and contribute knowledge.',
    s.action_command = 'cd ~/my-project && mycelium inject',
    s.verification_command = 'test -f .claude/rules/mycelium-capability.md && echo "success"',
    s.expected_outcome = '.claude/rules/mycelium-capability.md exists in your project. mycelium commands work in this directory.',
    s.target_os = 'all',
    s.required_tools = 'mycelium',
    s.updated_at = datetime();

// Step 10: Mint your first crystal (optional, future)
MERGE (s:OnboardingStep {node_id: 'step-first-crystal'})
SET s.label = 'Mint Your First Crystal (Future)',
    s.ordinal = 100,
    s.description = 'Make a change to local graph, then crystallize it. Creates immutable MintedCrystal node with proof of discovery.',
    s.action_command = 'mycelium mint "what you changed"',
    s.verification_command = 'mycelium --target local ask "what crystals did I mint" | grep -i "<your-name>"',
    s.expected_outcome = 'MintedCrystal node created with your proof and timestamp.',
    s.target_os = 'all',
    s.required_tools = 'mycelium',
    s.updated_at = datetime();

// Link steps in sequence
MATCH (s1:OnboardingStep {node_id: 'step-prereqs'}), (s2:OnboardingStep {node_id: 'step-clone'})
MERGE (s1)-[:NEXT_STEP]->(s2);

MATCH (s1:OnboardingStep {node_id: 'step-clone'}), (s2:OnboardingStep {node_id: 'step-setup'})
MERGE (s1)-[:NEXT_STEP]->(s2);

MATCH (s1:OnboardingStep {node_id: 'step-setup'}), (s2:OnboardingStep {node_id: 'step-verify-prod'})
MERGE (s1)-[:NEXT_STEP]->(s2);

MATCH (s1:OnboardingStep {node_id: 'step-verify-prod'}), (s2:OnboardingStep {node_id: 'step-verify-dev'})
MERGE (s1)-[:NEXT_STEP]->(s2);

MATCH (s1:OnboardingStep {node_id: 'step-verify-dev'}), (s2:OnboardingStep {node_id: 'step-install-local-deps'})
MERGE (s1)-[:NEXT_STEP]->(s2);

MATCH (s1:OnboardingStep {node_id: 'step-install-local-deps'}), (s2:OnboardingStep {node_id: 'step-bootstrap-local'})
MERGE (s1)-[:NEXT_STEP]->(s2);

MATCH (s1:OnboardingStep {node_id: 'step-bootstrap-local'}), (s2:OnboardingStep {node_id: 'step-fork-dev'})
MERGE (s1)-[:NEXT_STEP]->(s2);

MATCH (s1:OnboardingStep {node_id: 'step-fork-dev'}), (s2:OnboardingStep {node_id: 'step-inject-project'})
MERGE (s1)-[:NEXT_STEP]->(s2);

MATCH (s1:OnboardingStep {node_id: 'step-inject-project'}), (s2:OnboardingStep {node_id: 'step-first-crystal'})
MERGE (s1)-[:NEXT_STEP]->(s2);

// Create a Workflow container
MERGE (w:Workflow {node_id: 'workflow-onboarding'})
SET w.label = 'Teammate Onboarding',
    w.description = 'Complete flow from fresh machine to prod/dev access with writable local sandbox.',
    w.total_steps = 10,
    w.updated_at = datetime();

// Link all steps to the workflow container
MATCH (w:Workflow {node_id: 'workflow-onboarding'}), (s:OnboardingStep)
WHERE s.node_id STARTS WITH 'step-'
MERGE (w)-[:CONTAINS_STEP]->(s);

// Optional: Link to CLICommand nodes if they exist (soft dependency from Slice F-1)
MATCH (s:OnboardingStep {node_id: 'step-verify-prod'}), (c:CLICommand {node_id: 'cmd-ask'})
MERGE (s)-[:USES_COMMAND]->(c);

MATCH (s:OnboardingStep {node_id: 'step-verify-dev'}), (c:CLICommand {node_id: 'cmd-ask'})
MERGE (s)-[:USES_COMMAND]->(c);

// Return summary
MATCH (w:Workflow {node_id: 'workflow-onboarding'})-[:CONTAINS_STEP]->(steps:OnboardingStep)
RETURN w.label as workflow, count(steps) as step_count, "onboarding workflow ready" as status;
