# Portfolio, direction, and unattended mandates

Status: proposed. Covers U02–U04, U10–U11, S01–S03, S08.

## Portfolio decision

Flowing Indian and Cajon Sensei receive active product attention. SeedForth receives
platform maintenance and upgrade work. Other products enter an archival assessment;
their present execution is not changed during specification.

Current live fleet also includes ethos, two LinkedIn projects, seedforthing, zuuro,
and delta-hub. The hub is a platform role, not an archived product. Audioworld,
Website, Heritage Diaries, SolveOS, Ember, and other registry entries must also be
assessed even when no current delta2 process exists.

For each project record independent dimensions:

| Dimension | Values | Authority |
|---|---|---|
| Portfolio lifecycle | proposed / active / paused / archived | Owner decision |
| New work permitted | enabled / held / disabled | Mandate and holds |
| Service obligation | none / maintain / maintain-until-date | Owner and commitments |
| Process observation | ready / stopped / degraded / unknown | Runtime sensor |
| Evidence health | fresh / stale / conflicting / unknown | Reconciliation |

Sleeping a process cannot mutate portfolio lifecycle. A message can request work
but cannot automatically reactivate archived authority. Maintenance work for an
archived service is governed by a separate limited mandate.

## Archival worksheet and sequence

For each candidate record canonical identity, aliases, owner, pending work, latest
artifacts, repositories/dirty state, schedules, agents, external accounts, hosting,
domains, subscriptions, credentials, data retention, dependencies, and restoration.
Mark missing information unknown; do not infer no obligations from absent graph data.

Order: approve disposition → hold new work → drain/reconcile attempts → capture
history → disable applicable schedules → remove unnecessary credential access →
verify retained services → mark archived → test future ingestion cannot reactivate.
Repository deletion and provider cancellation are not default archival operations.

## Goal contract

Each goal contains owner, purpose, baseline, measure/rubric, target, time window,
source, freshness, acceptance authority, dependencies, and current version. A goal
may link several milestones; workstreams own execution lanes. Business targets are
unset until the owner approves them. Fixtures use explicitly synthetic targets.

Track delivered artifacts, accepted artifacts, observed outcomes, and attributable
contribution separately. A registration metric changing after a code commit is not
proof of causation. Missing valid measurement yields unknown achievement.

Changes create a new goal version and a reconciliation decision over affected
work. Preserve the original agreement and completed effects. No automatic goal
completion solely because a project changes lifecycle state.

## Mandate template

Required fields: mandate_id, version, project, owner, goal_versions, allowed work
classes, allowed repositories/tools/destinations, grants, exclusions, budget caps,
time horizon, maximum concurrent attempts, review policy, checkpoints, fallback
work, escalation owner, expiry, and stop conditions.

Proposed initial unattended envelope: project-scoped research, draft artifacts,
isolated code changes, and tests using already authorized tools. Production changes,
new external recipients, new spend, credential changes, and policy promotion need
specific authorization. This is a proposed policy, not a grant to current agents.

The mandate can preauthorize repeatable low-risk actions so autonomy does not require
approval of every step. Each invocation still checks the current grant and budget.
No response from a human invokes the written fallback or stops that work.

## Direction and decision ownership

Charlie discusses direction and prepares proposals. Accepted direction is written
through the same validated decision boundary as other human input. Delta schedules
and delegates against that version. A teammate may steer only within their grant.
Conflicting edits return the current version and require reconciliation.

Priorities: emergency holds/revocation → mandatory maintenance within grant →
accepted project priorities → eligible work. Fairness and reserved recovery capacity
apply across projects. Work cannot acquire authority by declaring itself urgent.

## Unattended return report

Report window begins at the user's last acknowledged review. Show goal changes,
accepted results, pending review, measured outcomes, spent/reserved budgets,
decisions under standing grants, incidents, unresolved dependencies, and next work.
Every claim links to evidence; duplicated events are grouped. Do not describe a
running process or a failed attempt as progress.

Acceptance: archive does not stop a retained service; silence never becomes
approval; budget exhausted means no newly authorized work; changed goals preserve
old decisions; both projects can advance without one starving the other.
