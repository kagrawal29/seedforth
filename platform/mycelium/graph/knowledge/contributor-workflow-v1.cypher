// @node_id: contributor-workflow-v1
// @label: "Contributor Workflow v1 — how local work becomes shared graph state"
// @kind: knowledge
//
// Maps the end-to-end path from a teammate's heavy local graph + scripts
// back to shared dev. Queryable so `mycelium --target dev ask "how do I
// contribute"` returns the map directly instead of pointing at a docs file.
// Each statement is self-contained (MATCH fresh after semicolons) so the
// file lands cleanly via both `cypher-shell --file` and `mycelium bootstrap`.
// ============================================================================

// Root: the workflow itself
MERGE (cw:ContributorWorkflow {node_id: 'contributor-workflow-v1'})
SET cw.project = 'mycelium',
    cw.declared_at = datetime(),
    cw.rationale = 'Local graphs grow heavy (GBs) with runtime noise. Dev stays lean (~200MB) so teammates can fork fast. So contribution is never a full snapshot sync — it is novel clean intent serialized as cypher files, PRed, merged, bootstrapped onto dev by autodeploy.',
    cw.docs_path = 'docs/contributor-workflow.md',
    cw.contribution_kinds = ['python-scripts','schema-cypher','protocol-cypher','test-case-cypher','sample-fixtures'];

// The three graphs teammates should know about
UNWIND [
  {name: 'local', size: 'grows to GB',       mode: 'rw', lifetime: 'as long as you keep it', use: 'private experimentation, runtime traces'},
  {name: 'dev',   size: 'lean (~50-200 MB)', mode: 'ro', lifetime: 'shared, persistent',     use: 'common ground — what the team agrees is real'},
  {name: 'prod',  size: 'lean, frozen',      mode: 'ro', lifetime: 'shared, stable',         use: 'product-facing, read-only'}
] AS g
MERGE (gs:GraphScope {node_id: 'graph-scope-' + g.name})
SET gs.project = 'mycelium',
    gs.name = g.name,
    gs.size_expectation = g.size,
    gs.mode = g.mode,
    gs.lifetime = g.lifetime,
    gs.use = g.use;

// Wire GraphScopes to the workflow
MATCH (cw:ContributorWorkflow {node_id: 'contributor-workflow-v1'}),
      (gs:GraphScope)
WHERE gs.node_id STARTS WITH 'graph-scope-'
MERGE (cw)-[:DESCRIBES]->(gs);

// The five contribution kinds
UNWIND [
  {kind: 'python-scripts',   location: 'scripts/<your-module>/ or graph/runner/',  header_required: false, gate: 'code review'},
  {kind: 'schema-cypher',    location: 'graph/knowledge/<area>-v1.cypher',         header_required: true,  gate: 'Forest Promise + idempotence'},
  {kind: 'protocol-cypher',  location: 'graph/protocols/protocol-<verb>.cypher',   header_required: true,  gate: 'must ship with matching :TestCase'},
  {kind: 'test-case-cypher', location: 'graph/knowledge/test-<verb>.cypher',       header_required: true,  gate: 'claims verifiable from graph nodes'},
  {kind: 'sample-fixtures',  location: 'graph/fixtures/<area>-examples.cypher',    header_required: true,  gate: 'MERGE only, small samples, not full corpus'}
] AS k
MERGE (ck:ContributionKind {node_id: 'contribution-kind-' + k.kind})
SET ck.project = 'mycelium',
    ck.kind = k.kind,
    ck.location = k.location,
    ck.header_required = k.header_required,
    ck.gate = k.gate;

// Wire ContributionKinds to workflow
MATCH (cw:ContributorWorkflow {node_id: 'contributor-workflow-v1'}),
      (ck:ContributionKind)
WHERE ck.node_id STARTS WITH 'contribution-kind-'
MERGE (cw)-[:ALLOWS]->(ck);

// The nine-step contribution sequence
UNWIND [
  {n: 1, step: 'mycelium drift --from dev',                                   purpose: 'see what is novel locally vs dev'},
  {n: 2, step: 'decide what to contribute',                                   purpose: 'schema / protocols / scripts / fixtures — extract novel clean parts'},
  {n: 3, step: 'author clean cypher files with // @node_id headers',          purpose: 'declarative intent, not snapshot diffs'},
  {n: 4, step: 'mycelium --target local shell < <file>.cypher',               purpose: 'verify each file lands cleanly against your local graph'},
  {n: 5, step: 'git checkout -b feature/<your-name>/<short-desc>',            purpose: 'feature branch, never push to main'},
  {n: 6, step: 'git add + commit + push',                                     purpose: 'commit scripts + cypher together when they belong together'},
  {n: 7, step: 'gh pr create --base main',                                    purpose: 'PR against kagrawal29/mycelium:main (upstream core)'},
  {n: 8, step: 'reviewer validates three merge gates',                        purpose: 'Forest Promise + test coverage + idempotence'},
  {n: 9, step: 'merge → autodeploy bootstraps dev → heartbeat fires at 30s', purpose: 'changes land on dev; every teammate sees them on next heartbeat'}
] AS s
MERGE (step:WorkflowStep {node_id: 'contrib-step-' + toString(s.n)})
SET step.project = 'mycelium',
    step.order = s.n,
    step.step = s.step,
    step.purpose = s.purpose;

// Wire steps to workflow
MATCH (cw:ContributorWorkflow {node_id: 'contributor-workflow-v1'}),
      (step:WorkflowStep)
WHERE step.node_id STARTS WITH 'contrib-step-'
MERGE (cw)-[:HAS_STEP]->(step);

// Link to merge gates (inherits from the Forest Promise)
MATCH (cw:ContributorWorkflow {node_id: 'contributor-workflow-v1'}),
      (promise:ForestPromise {node_id: 'forest-promise-sovereignty'})
MERGE (cw)-[:ENFORCED_BY]->(promise);

// Six antipatterns — what NOT to do
UNWIND [
  {id: 'never-commit-dumps',            rule: 'Never commit a mycelium dump (.dump) file — binary, version-tied, huge. Serialize as readable cypher instead.'},
  {id: 'never-use-CREATE-on-knowledge', rule: 'Use MERGE not CREATE on knowledge/schema nodes. Re-runs must be idempotent.'},
  {id: 'never-ship-full-corpus',        rule: 'Ship small samples (3-5 exemplars), not your full local accumulation. Dev accumulates real data organically.'},
  {id: 'never-sync-heavy-local',        rule: 'Your heavy local graph never syncs to dev. Only novel clean intent propagates.'},
  {id: 'never-skip-TestCase',           rule: 'Protocol PRs without a matching :TestCase get rejected. The test claims what the protocol does.'},
  {id: 'never-bypass-PR',               rule: 'Writes to dev are proxy-rejected. The only path is PR → merge → autodeploy bootstrap.'}
] AS a
MERGE (ap:ContributionAntipattern {node_id: 'antipattern-' + a.id})
SET ap.project = 'mycelium',
    ap.rule = a.rule,
    ap.declared_at = coalesce(ap.declared_at, datetime());

// Wire antipatterns to workflow
MATCH (cw:ContributorWorkflow {node_id: 'contributor-workflow-v1'}),
      (ap:ContributionAntipattern)
WHERE ap.node_id STARTS WITH 'antipattern-'
MERGE (cw)-[:WARNS_AGAINST]->(ap);
