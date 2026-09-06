// @node_id: amendment-2026-04-20-wi-lf-07-architect-migration
// @target: WorkItem wi-lf-07 (Track E — docs integration)
// @type: acceptance-addendum
// @by: architect
// @reason: dogfood principle (design principle #6 in plan.md); architect migrates off brew-native Neo4j onto teammate Docker stack once Track E ships.
// ============================================================================
// First amendment using the graph/amendments/ mechanism (wi-gs-15).
// This file demonstrates the pattern: one atomic tweak, MERGE-idempotent,
// append-only to wi.amendments.
// ============================================================================

MATCH (wi:WorkItem {plan:'plan-v1.1-maverick', node_id:'wi-lf-07'})
SET wi.amendments = coalesce(wi.amendments, []) + [{
  ts: datetime('2026-04-20T18:30:00Z'),
  by: 'architect',
  type: 'acceptance-addendum',
  text: 'Architect migration: after wi-lf-02/04 merge and v1.1.0 ships, architect stops brew-native Neo4j (`brew services stop neo4j`), runs `bash install.sh` + `maverick local bootstrap` + `maverick fork maverick-dev`, and verifies `maverick --target maverick-local status` healthy. Dev-alias `~/SeedForth/tetrahedron/projects/mycelium/mycelium` is removed from PATH. A :DogfoodCheckpoint {kind:"architect-on-teammate-stack", ts} node is written as evidence.',
  amendment_id: 'amendment-2026-04-20-wi-lf-07-architect-migration',
  rationale: 'Design principle #6 (architect = contributor) requires the architect walks the same teammate path. This amendment makes the dogfood explicit + verifiable as part of wi-lf-07 acceptance, rather than inventing a separate operational WorkItem.'
}];

// --- Summary ---
RETURN
  'wi-lf-07 amended: architect-migration acceptance added (wi-gs-15 first dogfood)' AS status;
