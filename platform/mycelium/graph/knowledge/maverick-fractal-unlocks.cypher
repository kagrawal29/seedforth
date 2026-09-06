// @node_id: maverick-fractal-unlocks-v1
// @label: "What fractal manifestation unlocks for Maverick — session 2026-04-19"
// @kind: knowledge
//
// Captured during the session where we ran the first cross-scope semantic
// probe on pulse-dev and saw the fractal appear in embeddings:
//   - Mycelium :Being   ↔   Friend's agent-memory-cluster (16 instances)
//   - integration-card  ↔   permcat-integration + perm-integrations-view
//   - workflow-builder  ↔   role-associate + agent-memory-deck
//   - auth-pattern      ↔   invariant-graph-native-auth + membrane-auth
//
// These are the ten concrete product/organizational unlocks that
// :FractalEcho + :REFLECTS edges enable for Maverick.
// ============================================================================

MERGE (parent:MaverickUnlockSet {node_id: 'maverick-fractal-unlocks-v1'})
SET parent.project = 'mycelium',
    parent.session_date = '2026-04-19',
    parent.captured_at = datetime(),
    parent.seed_findings = [
      'being↔agent-memory-cluster',
      'integration-card↔permcat-integration',
      'workflow-builder↔role-associate',
      'auth↔invariant-graph-native-auth'
    ];

// Ten unlocks — each a measurable node that maverick can verify later
UNWIND [
  {n: 1, key: 'cross-scale-retrieval', title: 'Retrieval becomes cross-scale',
   why: 'Echo hits at every zoom simultaneously — company + founder + thesis + memo + rejection. Competitors do one layer at a time.',
   metric: 'avg #distinct scales per query result'},
  {n: 2, key: 'colony-of-beings', title: 'Maverick as a colony of sovereign Beings',
   why: 'Friend has 16 agents with their own memory clusters. Mycelium has 1 Being per project. Pattern is the same. Maverick scales with fund count, not context window.',
   metric: 'count of :Being nodes per fund; autonomous_score per Being'},
  {n: 3, key: 'implicit-decisions-captured', title: 'Implicit decisions surfaced retroactively',
   why: 'Echoes between Commits + Conversations + Decision archetypes catch decisions nobody wrote down. Every memo gets citations.',
   metric: '(# :Decision nodes with evidence edges) / (# commits touching product code)'},
  {n: 4, key: 'integration-velocity', title: 'New data-source integration in hours not weeks',
   why: 'Echo already knows the UI + permission fractal. PitchBook / Affinity / CRM onboarding inherits the pattern.',
   metric: 'days from new-source PR opened to first analyst query served'},
  {n: 5, key: 'roadmap-from-gaps', title: 'Roadmap writes itself from missing echoes',
   why: 'Feature dirs without a Spec Echo at sibling scale = the backlog. Asymmetry in the fractal IS the priority list.',
   metric: '(# feature dirs) - (# spec echoes at feature scale)'},
  {n: 6, key: 'cross-fund-intel-privacy-safe', title: 'Cross-fund intelligence without data leaks',
   why: 'Echo nodes carry pattern, not payload. Fund-A and Fund-B can share echoes without sharing deals.',
   metric: '# :FractalEcho nodes spanning >=2 fund scopes'},
  {n: 7, key: 'onboarding-one-question', title: 'New analyst: one question, not fifty',
   why: 'New hire drops their thesis node. Echo-detection attaches it to existing workstreams. Day-1 context instead of week-1.',
   metric: 'hours from new :Person node to first echo-anchored :Conversation'},
  {n: 8, key: 'fund-demo', title: 'The demo that wins fund sales calls',
   why: 'Competitor: 6 similar founders. Maverick: 6 similar founders + your prior decision pattern + your partner\'s memo style + the 2 declines and why + the signal you missed.',
   metric: 'conversion rate of demo → signed pilot'},
  {n: 9, key: 'graph-is-the-glue', title: 'Every agent feeds every agent, no pipeline code',
   why: ':REFLECTS + :ECHOES_AT_SCALE make findings from diligence strengthen assay, which updates thesis, which refocuses falcon — automatically.',
   metric: '# cross-agent :RESONATES edges per heartbeat'},
  {n: 10, key: 'fractal-dimension-as-kpi', title: 'Fractal dimension becomes a product metric',
   why: 'Per-Being box-counting gives each subsystem a number. Drop = actionable warning. Ties structural health to fund-visible KPIs.',
   metric: 'box-counting fractal_dim per :Being, tracked daily'}
] AS u
MERGE (unlock:MaverickUnlock {node_id: 'unlock-' + u.key})
SET unlock.project = 'mycelium',
    unlock.order = u.n,
    unlock.title = u.title,
    unlock.why = u.why,
    unlock.metric = u.metric,
    unlock.status = 'declared',
    unlock.declared_at = datetime();

// Wire unlocks to parent set (self-contained MATCH)
MATCH (parent:MaverickUnlockSet {node_id: 'maverick-fractal-unlocks-v1'}),
      (unlock:MaverickUnlock)
WHERE unlock.node_id STARTS WITH 'unlock-'
MERGE (parent)-[:CONTAINS]->(unlock);
