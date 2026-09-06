// V0049 — Seed deal-pipeline Module (first instance of module map)
// Creates :Module, 5 :LifecycleStage templates, 17 :Feature nodes,
// wires IMPLEMENTED_BY / RENDERED_BY / BACKED_BY edges by path prefix,
// seeds 8 :QualityGate nodes per feature with null thresholds,
// auto-computes gate status for spec/story/test/research-backed categories.
// Idempotent: all MERGE-based.

// Module
MERGE (m:Module {slug:'deal-pipeline'})
SET m.name='Deal Pipeline',
    m.repo_owner='vc-ai-associate',
    m.lifecycle_type='process',
    m.status='active',
    m.created_at=timestamp();

// LifecycleStages (5 templates)
UNWIND [
  {slug:'sourcing',        order:1, name:'Sourcing',        status:'not-built',  notes:'No sourcing-intelligence files in repo yet.'},
  {slug:'screening',       order:2, name:'Screening',       status:'built',      notes:'filter-deals, pipeline-board, AI deal card.'},
  {slug:'diligence',       order:3, name:'Diligence',       status:'built',      notes:'deal-workspace tabs, research-editor, calls.'},
  {slug:'ic',              order:4, name:'IC',              status:'built',      notes:'ic-packet feature, ICPacketTab, pass_invest permission.'},
  {slug:'post-investment', order:5, name:'Post-Investment', status:'not-built',  notes:'No portfolio/monitoring files in repo yet.'}
] AS s
MERGE (stage:LifecycleStage {module_slug:'deal-pipeline', slug:s.slug})
SET stage.order=s.order, stage.name=s.name, stage.status=s.status, stage.notes=s.notes, stage.is_template=true;

// Module -> Stages
MATCH (m:Module {slug:'deal-pipeline'}), (s:LifecycleStage {module_slug:'deal-pipeline'})
MERGE (m)-[:HAS_STAGE]->(s);

// Features (17, derived from code clustering + story inventory)
UNWIND [
  {slug:'pipeline-board',          stage:'screening', intent:'Kanban + list view of deals across stages, filter + reorder columns.',             path_prefix:'src/widgets/pipeline-board/'},
  {slug:'pipeline-settings',       stage:'screening', intent:'Per-fund stage configuration: add / archive / mark terminal.',                     path_prefix:'src/features/pipeline-settings/'},
  {slug:'move-pipeline',           stage:'screening', intent:'Stage selector used inline to move a deal between stages.',                         path_prefix:'src/features/move-pipeline/'},
  {slug:'filter-deals',            stage:'screening', intent:'Filter deals by stage, owner, sector, fit-score, date, natural-language query.',    path_prefix:'src/features/filter-deals/'},
  {slug:'deal-actions',            stage:'screening', intent:'Move-to-stage dialog and other deal-level actions.',                                path_prefix:'src/features/deal-actions/'},
  {slug:'create-deal',             stage:'sourcing',  intent:'Manual deal creation entry point.',                                                 path_prefix:'src/features/create-deal/'},
  {slug:'deal-workspace',          stage:'diligence', intent:'Per-deal surface with tabs: overview, calls, contacts, documents, timeline, IC, research.', path_prefix:'src/widgets/deal-workspace/'},
  {slug:'call-prep',               stage:'diligence', intent:'Pre-call preparation flow.',                                                        path_prefix:'src/features/call-prep/'},
  {slug:'call-scheduling',         stage:'diligence', intent:'Schedule calls from within a deal.',                                                path_prefix:'src/features/call-scheduling/'},
  {slug:'deal-research-editor',    stage:'diligence', intent:'TipTap-based investment-memo editor with metrics/timeline/collapsible blocks, presence.', path_prefix:'src/widgets/deal-research-editor/'},
  {slug:'deal-research-comments',  stage:'diligence', intent:'Inline + panel comments on research docs.',                                          path_prefix:'src/features/deal-research-comments/'},
  {slug:'deal-research-versioning',stage:'diligence', intent:'Version history, compare, restore for research docs.',                              path_prefix:'src/features/deal-research-versioning/'},
  {slug:'deal-research-export',    stage:'diligence', intent:'Export research doc to external format.',                                           path_prefix:'src/features/deal-research-export/'},
  {slug:'deal-sharing',            stage:'diligence', intent:'Share a deal (and its research) with a collaborator.',                              path_prefix:'src/features/deal-sharing/'},
  {slug:'ic-packet',               stage:'ic',        intent:'Produce and view the IC packet for a deal.',                                        path_prefix:'src/features/ic-packet/'},
  {slug:'fund-profile',            stage:'screening', intent:'Fund-level profile and thesis configuration (drives fit-score).',                   path_prefix:'src/features/fund-profile/'},
  {slug:'ai-deal-assistants',      stage:'screening', intent:'AI deal card + stage-requirements card compounds.',                                 path_prefix:'src/shared/ui/compounds/ai-'}
] AS f
MERGE (feat:Feature {slug:f.slug})
SET feat.module_slug='deal-pipeline',
    feat.name=f.slug,
    feat.intent=f.intent,
    feat.primary_stage=f.stage,
    feat.path_prefix=f.path_prefix,
    feat.status='ingested';

// Module -> Features
MATCH (m:Module {slug:'deal-pipeline'}), (feat:Feature {module_slug:'deal-pipeline'})
MERGE (m)-[:HAS_FEATURE]->(feat);

// Stage -> Feature (SERVED_BY)
MATCH (s:LifecycleStage {module_slug:'deal-pipeline'}), (f:Feature {module_slug:'deal-pipeline'})
WHERE s.slug = f.primary_stage
MERGE (s)-[:SERVED_BY]->(f);

// IMPLEMENTED_BY — code files matched by path prefix
MATCH (f:Feature {module_slug:'deal-pipeline'}), (c:CodeFile {repo:'vc-ai-associate'})
WHERE c.path STARTS WITH f.path_prefix
MERGE (f)-[:IMPLEMENTED_BY]->(c);

// RENDERED_BY — storybook stories matched by path prefix (via story_file, stripping leading slashes)
MATCH (f:Feature {module_slug:'deal-pipeline'}), (s:StorybookStory {repo:'vc-ai-associate'})
WHERE s.story_file STARTS WITH f.path_prefix
MERGE (f)-[:RENDERED_BY]->(s);

// BACKED_BY — db tables matched by name heuristic (deal-pipeline touches deals / deal_notes / funds)
MATCH (f:Feature {module_slug:'deal-pipeline'}), (t:DbTable)
WHERE (f.slug CONTAINS 'deal' AND t.name IN ['deals','deal_notes'])
   OR (f.slug CONTAINS 'fund' AND t.name IN ['funds','fund_permission_overrides'])
MERGE (f)-[:BACKED_BY]->(t);

// QualityGate seeding — 8 gates per feature, null threshold
UNWIND ['spec-approved','fr-coverage','story-coverage','test-coverage','a11y','perf-budget','sec-review','research-backed'] AS category
MATCH (f:Feature {module_slug:'deal-pipeline'})
MERGE (g:QualityGate {feature_slug:f.slug, category:category})
ON CREATE SET g.threshold=null, g.rubric=null, g.status='unassessed', g.created_at=timestamp();

// Feature -> QualityGate
MATCH (f:Feature {module_slug:'deal-pipeline'}), (g:QualityGate {feature_slug:f.slug})
MERGE (f)-[:GATED_BY]->(g);

// Auto-compute gate status for derivable categories
// story-coverage: green if ≥1 RENDERED_BY
MATCH (f:Feature {module_slug:'deal-pipeline'})-[:GATED_BY]->(g:QualityGate {category:'story-coverage'})
OPTIONAL MATCH (f)-[:RENDERED_BY]->(s:StorybookStory)
WITH g, count(s) AS n
SET g.status = CASE WHEN n > 0 THEN 'green' ELSE 'red' END, g.evidence_count = n;

// spec-approved: red (zero specs cover deal-pipeline today — honest signal)
MATCH (g:QualityGate {category:'spec-approved'})
WHERE (:Feature {module_slug:'deal-pipeline'})-[:GATED_BY]->(g)
SET g.status='red', g.evidence_count=0;

// fr-coverage: red (no FRs for deal-pipeline yet)
MATCH (g:QualityGate {category:'fr-coverage'})
WHERE (:Feature {module_slug:'deal-pipeline'})-[:GATED_BY]->(g)
SET g.status='red', g.evidence_count=0;
