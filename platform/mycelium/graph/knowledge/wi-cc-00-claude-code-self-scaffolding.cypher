// @node_id: wi-cc-00-claude-code-self-scaffolding
// @label: WorkItem wi-cc-00 — graph-owned Claude Code integration (self-scaffolding, no hooks)
// @kind: work-item
// ============================================================================
// Parking the "graph IS the source of truth for Claude Code scaffolding" idea.
// Recorded 2026-04-21 during autodeploy repair session.
//
// Core thesis:
//   The graph knows how Claude Code must be configured, integrates it, and
//   verifies it. The Claude Code instance asks the graph what it needs to
//   know. No systemd/shell hooks — the graph is the integration layer.
//
// Dogfood rule (design principle #6): apply this to THIS Claude Code session
// first — end-to-end — before generalizing to teammates.
//
// Out of scope for this WorkItem but related:
//   - Track H (teammate Claude Code integration) — generalization target.
//   - Track I (graph self-scaffolding / :RepoFile) — shares the topology.
// ============================================================================

MERGE (wi:WorkItem {plan: 'plan-v1.1-maverick', node_id: 'wi-cc-00-claude-code-self-scaffolding'})
SET wi.track            = 'J',  // new track — graph-owned CC integration
    wi.title            = 'Graph-owned Claude Code integration (self-first)',
    wi.status           = 'parked',
    wi.created_at       = datetime('2026-04-21T10:00:00Z'),
    wi.parked_at        = datetime('2026-04-21T10:00:00Z'),
    wi.parked_by        = 'architect',
    wi.description      = 'The graph maps what Claude Code needs (CLAUDE.md contents, rules, skills, allowed tools, MCP servers, settings), integrates them into a running Claude Code instance, and verifies correctness — all without shell/systemd hooks. Onus is on the graph, not on the harness. Teammates (and the architect) never hand-edit .claude/; they pull from the graph.',
    wi.acceptance_criteria = [
      'Graph holds :ClaudeCodeConfig nodes describing what a given agent needs (scope-scoped).',
      'A `maverick --target local claude sync` or equivalent pulls config from graph into .claude/ idempotently.',
      'Graph holds :ClaudeCodeVerification nodes with checks (file exists, hash matches, rule loaded).',
      'Verification runs on every heartbeat; drift creates :ActionProposal.',
      'Self-first: architect Claude Code (this session) is driven entirely by graph — no hand-edited rules.',
      'No systemd/pre-commit/post-checkout hooks used for sync — graph pulls/pushes on demand.'
    ],
    wi.parked_rationale = 'Surfaced mid autodeploy repair 2026-04-21. User: "look at our own claude code scaffolding first, graph stays SoT, no hooks, apply on self end-to-end before generalizing". To ship after current autodeploy + merge cascade settles.',
    wi.related_tracks   = ['H', 'I'],
    wi.depends_on       = ['wi-gs-11-repofile-schema', 'wi-th-00-plan'];

// Surface as ActionProposal so dream round can route it when current blockers lift.
MERGE (ap:ActionProposal {node_id: 'ap-wi-cc-00-parked'})
SET ap.title      = 'Unpark wi-cc-00 once autodeploy green + Wave-6 done',
    ap.for_scope  = 'mycelium',
    ap.status     = 'queued',
    ap.created_at = datetime('2026-04-21T10:00:00Z'),
    ap.workitem   = 'wi-cc-00-claude-code-self-scaffolding';

MERGE (wi)-[:SURFACED_AS]->(ap);

RETURN 'wi-cc-00 parked — graph-owned Claude Code integration, self-first, no hooks' AS status;
