// V0050 — Tag module-map nodes with project:'maverick'
// maverick is the umbrella project covering product (vc-ai-associate repo),
// research, SEO, marketing, and brand. Sub-repos stay on the `repo` property.
// Satisfies SovereigntyRule rule-namespace-integrity (forest promise).
// Idempotent.

MATCH (n) WHERE (n:Module OR n:LifecycleStage OR n:Feature OR n:QualityGate) AND n.project IS NULL
SET n.project = 'maverick'
RETURN labels(n)[0] AS label, count(*) AS tagged;
