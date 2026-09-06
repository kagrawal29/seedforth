# graph/amendments/

Append-only tweaks to existing graph nodes — acceptance addenda, scope tweaks, rationale captured post-hoc, dependency additions, blocker notes.

## Rules

1. **One amendment per file.** Small, atomic, PR-gated.
2. **Never edited after landing.** If an amendment was wrong, add a new amendment that supersedes (`type: 'supersede'`, `supersedes: 'previous-amendment-id'`).
3. **File naming**: `YYYY-MM-DD-<target-node-id>-<slug>.cypher` (e.g. `2026-04-20-wi-lf-07-architect-migration.cypher`).
4. **Shape**: each file appends one entry to the target node's `amendments` array using `SET n.amendments = coalesce(n.amendments, []) + [{...}]`.
5. **Required fields per entry**: `ts` (datetime), `by` (who), `type` (category), `text` (the addition). Optional: `reason`, `supersedes`, `pr_number`.

## Amendment types

- `acceptance-addendum` — a new acceptance criterion line
- `scope-tweak` — narrowed or broadened scope
- `rationale` — reasoning discovered post-hoc
- `dependency-added` / `dependency-removed`
- `blocker-noted` / `blocker-cleared`
- `supersede` — cancels or updates a prior amendment

## Projection

`maverick export-guide` (wi-cg-03) and `maverick export-plan` render WorkItem sections with amendments inline, chronologically, under the base acceptance criteria.

## Why append-only

Amendments ARE history. Mutating or deleting them loses the trace of how a WI evolved. If a mistake was made, supersede it; don't rewrite it.
