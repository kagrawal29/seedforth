// @node_id: decision-deploy-flow-v1
// @label: Decision — Deploy flow: teammates push to dev, admin promotes to prod
// @kind: decision
// @scope: team
// ============================================================================
// Codifies the team-facing deploy policy surfaced 2026-04-21 during the
// autodeploy-repair session. Replaces the implicit, undocumented prior
// behaviour (webhook auto-firing both dev + prod on every push to main).
// ============================================================================

MERGE (d:Decision {node_id: 'decision-deploy-flow-v1'})
SET d.scope              = 'team',
    d.area               = 'deploy',
    d.label              = 'Deploy flow: dev-first, admin-gated promotion to prod',
    d.status             = 'settled',
    d.decided_at         = datetime('2026-04-21T11:00:00Z'),
    d.decided_by         = 'architect',
    d.rationale          = 'Prod is product-facing; any change must pass through a human review step, not an automated merge-to-main webhook. Dev is the shared team surface; teammates iterate there freely. Reversing the default (prod auto-deploys) keeps a gated airlock between team experimentation and product behaviour.',
    d.flow_steps         = [
      '1. Teammate default target: dev. (`maverick --target dev`)',
      '2. Fork dev to local: `maverick fork dev`. Edit locally.',
      '3. Open PR against `dev` branch on Qubit-Capital/maverick.',
      '4. Merge to `dev` → webhook → autodeploy-dev → dev Neo4j bootstraps.',
      '5. Admin reviews dev, opens PR `dev → main`.',
      '6. Admin merges `dev → main`.',
      '7. Admin MANUALLY triggers prod autodeploy via `maverick promote` (verb TBD) OR `ssh pulse sudo systemctl start mycelium-autodeploy-prod`.',
      '8. Prod Neo4j bootstraps only when admin says so.'
    ],
    d.what_this_rules_out = [
      'Webhook autodeploying prod on any event (push, workflow_run, etc).',
      'PRs being merged directly to main bypassing the dev → main promotion step.',
      'Any CLI path that writes to prod without an admin identity check.'
    ],
    d.enforcement_invariant  = 'invariant-prod-admin-only',
    d.propagation_invariant  = 'invariant-scope-isolation',
    d.related_open_question  = 'oq-maverick-promote-auth',
    d.references = [
      '2026-04-21 conversation: architect flagged webhook auto-firing prod as a violation of the intended flow',
      'CLAUDE.md: prod is product-facing, read-only via bolt-proxy',
      'Earlier implicit: only architect had `maverick promote` access, but it was undocumented'
    ];

// ---- Open question blocking the `maverick promote` verb implementation ----
MERGE (oq:OpenQuestion {node_id: 'oq-maverick-promote-auth'})
SET oq.scope             = 'team',
    oq.ts                = datetime('2026-04-21T11:00:00Z'),
    oq.raised_by         = 'claude-code',
    oq.status            = 'open',
    oq.waiting_on        = 'architect conversation',
    oq.question          = 'What is the auth surface for `maverick promote` (the CLI verb that triggers prod autodeploy)?',
    oq.options_under_consideration = [
      '(a) Architect-only via existing maverick-dev SSH key on pulse — simplest, mirrors today s implicit model.',
      '(b) GitHub team membership check — receiver verifies the user who merged the dev→main PR is in a designated team.',
      '(c) Separate maverick-admin OAuth role with a short-lived token.',
      '(d) No CLI verb; admin runs `ssh pulse sudo systemctl start mycelium-autodeploy-prod` by hand. Friction by design.'
    ],
    oq.tradeoff_notes = 'Option (a) ships fastest; (c) scales best across multiple admins; (d) enforces the gate by hand-friction without adding code. Team should decide before wi-sync-07 enforcement work starts.',
    oq.blocks = ['decision-deploy-flow-v1 step 7 implementation'],
    oq.must_be_resolved_before = 'building maverick promote verb';

MERGE (d)-[:HAS_OPEN_QUESTION]->(oq);

RETURN
  'decision-deploy-flow-v1 + oq-maverick-promote-auth registered (team scope)' AS status;
