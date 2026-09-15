// @node_id: protocol-system-constraint-observer
// @label: "System Constraint Observer — shadow-mode cross-workstream diagnosis"
//
// This protocol observes repeated provider silence across WorkItems and
// persists one advisory GapSignal. It is deliberately non-interventionist:
// it never changes WorkItem/RunAttempt lifecycle, provider selection, leases,
// or execution eligibility. A later, separately governed protocol may consume
// the signal as an InterventionProposal.

MATCH (w:WorkItem)-[:HAS_ATTEMPT]->(a:RunAttempt)
WHERE a.finished_at > datetime() - duration({hours: 24})
  AND (a.failure_reason = 'provider_watchdog'
       OR a.error CONTAINS 'provider emitted no event')
WITH coalesce(w.project, 'unknown') AS project,
     'provider_watchdog' AS cause,
     count(a) AS occurrences,
     collect(DISTINCT w.node_id) AS workitems,
     max(a.finished_at) AS latest
WHERE occurrences >= 2
MERGE (g:GapSignal {node_id: 'gap-system-provider-watchdog-' + project})
ON CREATE SET g.created_at = datetime()
SET g.kind = 'system_constraint',
    g.cause = cause,
    g.project = project,
    g.occurrences = occurrences,
    g.affected_workitems = workitems,
    g.latest_observation = latest,
    g.mode = 'shadow',
    g.status = 'advisory',
    g.intervention_enabled = false,
    g.source = 'protocol-system-constraint-observer',
    g.updated_at = datetime()
WITH g, workitems
UNWIND workitems AS workitem_id
MATCH (w:WorkItem {node_id: workitem_id})
MERGE (g)-[:AFFECTS]->(w)
RETURN g.node_id AS advisory, g.project AS project,
       g.occurrences AS occurrences, g.affected_workitems AS workitems;
