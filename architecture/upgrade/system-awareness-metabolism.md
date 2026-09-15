# System Awareness & Metabolism

This is a graph-native, advisory workstream serving
`goal-seedforth-upgrade-20260906`. Its purpose is to help the system observe
itself, connect evidence across workstreams, and propose improvements without
becoming an unreviewed second scheduler.

## Operating contract

- The workstream and its WorkItems are graph state, authored by
  `platform/mycelium/graph/knowledge/system-awareness-metabolism-workstream.cypher`.
- The first implementation stages are shadow-only. Observations may create
  `GapSignal` nodes and advisory context, but may not change WorkItem status,
  leases, assignment, provider selection, or execution eligibility.
- Agents may create `PriorityProposal` nodes through
  `delta.priority_proposals.GraphPriorityProposalController`.
- A priority proposal must identify one project, Goal, WorkItem, proposer,
  rationale, requested priority, and evidence references.
- Proposals are `proposed`, `advisory`, `requires_review`, and
  `execution_eligible=false`. Only a separately governed decision can admit a
  priority change.
- Evidence remains attributable to its source and timestamp. Similarity,
  activation, or repeated observation is never authority by itself.

## Promotion sequence

1. Run the focused tests and the platform integration suite against a restored
   graph fixture.
2. Build an immutable SeedForth release containing the knowledge source, the
   shadow observer protocol, and the Delta runtime adapter.
3. Run the reviewed graph migration. The migration source list must include
   `system-awareness-metabolism-workstream.cypher`.
4. Bootstrap and decompose the observer protocol on canonical delta2.
5. Verify the workstream, milestone, eight proposed WorkItems, dependency edges,
   and `execution_eligible=false` directly on delta2.
6. Observe one bounded window. Confirm advisories improve worker context and
   that no lifecycle, lease, assignment, provider, or schedule mutations occur.
7. Review the resulting `PriorityProposal` and `GapSignal` evidence before any
   later admission or intervention protocol is authored.

Live promotion is intentionally separate from source authoring. It must use an
immutable release and leave the active worker's current lease and priority
untouched.
