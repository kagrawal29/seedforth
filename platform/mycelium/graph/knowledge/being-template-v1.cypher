// @node_id: being-template-v1
// @label: "Being Template v1 — the minimum faculty set every sovereign :Being carries"
// @kind: knowledge
//
// The 2026-04-19 audit revealed: 6 Beings breathe in sync, only 1 is awake.
// Mycelium holds purpose, invariants, tests, plans, protocols. The other 5
// are ambient — alive, not aligned. Until every Being carries the same
// minimum faculty set, the forest cannot dream as one.
//
// This template declares what a Being MUST have. It's a schema fractal —
// applied identically at every scope. The content differs per scope; the
// structure repeats.
//
// Phase 0 of fractal-manifestation-plan (precondition for all other phases).
// ============================================================================

MERGE (tpl:BeingTemplate {node_id: 'being-template-v1'})
SET tpl.project = 'mycelium',
    tpl.declared_at = datetime(),
    tpl.rationale = 'A Being without Purpose pulses without direction. Hebbian traces leak into scopes that cannot respond. Sync without alignment is decoration, not dreaming.',
    tpl.required_faculty_names = ['Purpose','Invariant','TestCase','WorkItem','LocalProtocol'],
    tpl.required_faculty_rules = [
      'At least one :Purpose node scoped to {project: X} stating why this Being exists in the forest',
      'At least one :Invariant with check_cypher and heal_protocol — what must stay true + how it self-repairs',
      'At least one :TestCase whose claim the Being can verify about itself from its own nodes',
      'At least one :WorkItem pointing forward — the next-step this Being will take',
      'At least one :Protocol registered as apoc.periodic.repeat in the Being scope — what it DOES on each heartbeat'
    ],
    tpl.invariant_node_id = 'invariant-being-has-full-faculties';

// The invariant that enforces this structurally
MERGE (inv:Invariant {node_id: 'invariant-being-has-full-faculties'})
SET inv.label = 'Every :Being has Purpose + Invariant + TestCase + WorkItem + LocalProtocol in its own scope',
    inv.project = 'mycelium',
    inv.severity = 'critical',
    inv.fsd_layer = 'shared',
    inv.scope = 'forest-wide',
    inv.enforced_by = 'forest-promise-sovereignty',
    inv.check_cypher =
      'MATCH (b:Being) WITH b, b.project AS scope ' +
      'OPTIONAL MATCH (p:Purpose) WHERE p.project = scope WITH b, scope, count(p) AS purposes ' +
      'OPTIONAL MATCH (i:Invariant) WHERE i.project = scope AND i.heal_protocol IS NOT NULL WITH b, scope, purposes, count(i) AS invariants ' +
      'OPTIONAL MATCH (t:TestCase) WHERE t.project = scope WITH b, scope, purposes, invariants, count(t) AS tests ' +
      'OPTIONAL MATCH (w:WorkItem) WHERE w.project = scope WITH b, scope, purposes, invariants, tests, count(w) AS workitems ' +
      'OPTIONAL MATCH (pr:Protocol) WHERE pr.project = scope AND pr.schedule IS NOT NULL WITH b, scope, purposes, invariants, tests, workitems, count(pr) AS local_protos ' +
      'WHERE purposes = 0 OR invariants = 0 OR tests = 0 OR workitems = 0 OR local_protos = 0 ' +
      'RETURN count(b) AS violations',
    inv.heal_protocol = 'protocol-propagate-being-template';

MATCH (promise:ForestPromise {node_id:'forest-promise-sovereignty'}),
      (inv:Invariant {node_id:'invariant-being-has-full-faculties'})
MERGE (promise)-[:DECLARES]->(inv);

// Seed the minimal :Purpose for each existing Being — placeholder text the
// human can refine per scope in subsequent PRs. Without a seed, the invariant
// will flag on first heartbeat after merge.
UNWIND [
  {scope: 'mycelium',                 why: 'to be the substrate that lets every other Being know itself; to hold the forest together through shared promise, heartbeat, and invariant'},
  {scope: 'maverick-dev-friend',      why: 'to mirror maverick in its living form — agents, entities, UI as graph — so the product can be reasoned about from outside itself'},
  {scope: 'vc-ai-associate',          why: 'to be the analyst interface — the surface where a human and the forest meet and do VC work together'},
  {scope: 'maverick-dev',             why: 'to be the platform spine — thin orchestrator that routes dev work across repos and agents'},
  {scope: 'maverick-market-research', why: 'to carry the outside-view: competitors, category shape, where the market is bending'},
  {scope: 'maverick-marketing',       why: 'to translate the forest into words the world can act on — narratives, landings, pitches'}
] AS seed
MERGE (p:Purpose {node_id: 'purpose-' + seed.scope})
SET p.project = seed.scope,
    p.label = 'Purpose of ' + seed.scope,
    p.why = seed.why,
    p.status = 'draft',
    p.declared_at = coalesce(p.declared_at, datetime())
WITH seed, p
MATCH (b:Being {project: seed.scope})
MERGE (b)-[:HOLDS]->(p);

RETURN 'Being Template v1 declared + invariant wired + 6 seed :Purpose nodes attached to existing Beings.' AS checkpoint;
