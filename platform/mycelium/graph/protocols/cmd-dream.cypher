// @node_id: protocol-cmd-dream
// @label: Dream Command
// @kind: command
// @description: Scan gaps across fractal scales, create DreamProposal nodes for unblocked items

// Atom 1: Query fractal structure - all scales present
MATCH (ss:Subsystem) WHERE coalesce(ss.fractal_scale, -1) >= 0
WITH count(DISTINCT ss.fractal_scale) AS scale_count
RETURN 'dream|fractal-scales|count:' + toString(scale_count) AS result;

// Atom 2: Identify gaps at scale 0 (atoms)
MATCH (g:Gap) WHERE g.fractal_scale = 0
WITH count(g) AS gap_count_0
RETURN 'dream|gaps-scale-0|count:' + toString(gap_count_0) AS result;

// Atom 3: Identify gaps at scale 1 (molecules)
MATCH (g:Gap) WHERE g.fractal_scale = 1
WITH count(g) AS gap_count_1
RETURN 'dream|gaps-scale-1|count:' + toString(gap_count_1) AS result;

// Atom 4: Identify unblocked WorkItems that relate to gaps
MATCH (wi:WorkItem) WHERE wi.status = 'open' OR wi.status = 'unblocked'
WITH count(wi) AS unblocked_count
RETURN 'dream|unblocked-items|count:' + toString(unblocked_count) AS result;

// Atom 5: Create DreamProposal nodes for convergent gaps
WITH timestamp() AS ts
MATCH (g:Gap) WHERE g.fractal_scale IS NOT NULL AND g.priority IS NOT NULL
WITH g, ts, rand() AS rand_score
WHERE rand_score > 0.5
MERGE (dp:DreamProposal {node_id: 'dream-' + toString(ts) + '-' + toString(rand_score)})
SET dp.created_at = ts, dp.status = 'proposed'
WITH dp, collect(g.node_id) AS gap_ids
RETURN 'dream|proposals|created:' + toString(count(dp)) AS result;

// Atom 6: Summary of dream round
MATCH (dp:DreamProposal) WHERE dp.status = 'proposed'
WITH count(dp) AS proposal_count
RETURN 'dream-complete|proposals:' + toString(proposal_count) + '|status:ready-for-action' AS result;
