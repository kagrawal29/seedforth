// V0048 — Module map schema (M2 of pipeline spine)
// Adds :Module / :LifecycleStage / :Feature / :QualityGate labels with unique-key constraints.
// Data-free. Safe to re-run.

CREATE CONSTRAINT module_slug IF NOT EXISTS FOR (m:Module) REQUIRE m.slug IS UNIQUE;
CREATE CONSTRAINT feature_slug IF NOT EXISTS FOR (f:Feature) REQUIRE f.slug IS UNIQUE;
CREATE CONSTRAINT lifecycle_stage_id IF NOT EXISTS FOR (s:LifecycleStage) REQUIRE (s.module_slug, s.slug) IS UNIQUE;
CREATE CONSTRAINT quality_gate_id IF NOT EXISTS FOR (g:QualityGate) REQUIRE (g.feature_slug, g.category) IS UNIQUE;
CREATE INDEX feature_module IF NOT EXISTS FOR (f:Feature) ON (f.module_slug);
CREATE INDEX quality_gate_feature IF NOT EXISTS FOR (g:QualityGate) ON (g.feature_slug);
