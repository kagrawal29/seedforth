# System-wide contracts and combined-failure acceptance

Status: proposed v0.1, 2026-09-06. Documentation only; no runtime verification.
Parent: [integrated upgrade plan](../seedforth-upgrade-plan.md).

These requirements extend the audit with cross-component failure analysis. They
are proposed design obligations, not newly observed production defects. S01–S10
must be traced into supporting specifications, implementation, and verification.
All numeric bounds below must be chosen during specification review, not inferred
from example scenarios or claimed as existing guarantees.

## S01 — goal evaluation and independent outcome evidence

Each active goal declares owner, baseline, target, units, measurement source,
evaluation window, eligible population, freshness, acceptance authority, and
version. Qualitative goals use an explicit rubric and reviewer. Missing baseline
or invalid measurement makes achievement unknown rather than automatically zero.

Separate attempted work, delivered artifact, accepted artifact, observed business
outcome, and attributed contribution. A verified website change does not establish
increased registrations. Correlation alone cannot establish that an agent caused
an observed improvement. Record attribution method and uncertainty where relevant.

The producer cannot prove completion merely by writing its own success property.
Verification must inspect independent evidence appropriate to the acceptance
criterion. Reuse of the same model is not by itself independent verification.
Changes to targets or measures preserve old versions and affected decisions.

Acceptance: a completed artifact with failed tests remains unaccepted; improved
metrics with missing attribution are reported as observed improvement; changing
a target does not rewrite historical achievement.

## S02 — control-loop precedence and stability

Identify each controller: human direction, Charlie planning, Delta scheduling,
project execution, reconciliation, healing, and learning. Specify its authority,
inputs, writable state, cadence, objective, and permitted interaction with others.

Proposed precedence: governing policy and revocation constrain all actions;
authorized emergency stop and explicit scoped human holds constrain automated
planning; accepted mandates constrain scheduling; observations update beliefs
without granting new authority. Conflicting authorized human decisions require
version checks and reconciliation rather than silent last-write-wins.

An explicit hold persists until its authorized release or declared expiry.
Liveness repair may restore an allowed service but cannot release a work hold.
New goals invalidate affected future plans through an explicit reconciliation
step. Already committed effects remain recorded.

Define cooldowns, retry budgets, reassignment limits, stale-input exclusion, and
threshold hysteresis where noisy observations could repeatedly toggle decisions.
Stop recurring failure loops with an owned incident, not new identical proposals.

Acceptance: pause plus heartbeat/healing cannot restart work; two schedulers cannot
claim the same exclusive work; alternating noisy metrics do not cause unbounded
replanning or spawning. Measure useful outcomes separately from controller activity.

## S03 — independent lifecycle dimensions

Represent strategic attention, permission to execute new work, required service
availability, and retained obligations separately. Labels and field names remain
to be selected in the graph contract. An archive decision specifies each dimension.

For every retiring project inventory running work, customer services, domains,
payments, notifications, data retention, credentials, dependencies, and owners.
Service-only maintenance needs its own limited mandate and budget. Cross-project
dependencies may retain a service without reactivating strategic work.

Acceptance: archiving a project removes it from autonomous development queues while
an explicitly retained service remains monitored. Historical data ingestion cannot
reactivate the project. Resumption requires an authorized lifecycle decision.

## S04 — observability coverage and negative evidence

Every observation has a defined population and claim boundary. Record complete,
partial, failed, or unavailable collection separately from observed object state.
Source snapshots include coverage and exclusions. An absent object is evidence
of deletion only when the collection contract establishes complete enumeration
or receives an authoritative deletion event.

Track collection success, consumption success, processing lag, coverage, and
freshness separately. A healthy process probe establishes process liveness only.
List important unobserved domains in project and administrator state projections.

Acceptance: partial Graphify extraction cannot remove unseen source symbols;
provider pagination failure cannot delete accounts; a recent process observation
cannot establish current goal progress. Recovered snapshots reconcile explicitly.

## S05 — operation while graph or control services are unavailable

Specify online, degraded, and recovering modes. Proposed default: stop admitting
new mutating work when current authority cannot be checked. Only previously
authorized, bounded in-flight operations may finish according to an explicit
action-class policy; do not renew expired authority from an offline cache.

Where a short-lived execution grant is used, record its scope, epoch, expiry, and
maximum offline exposure. Revocation during a partition cannot be claimed to take
instantaneous effect at a disconnected executor. Choose acceptable exposure or
require online checks for the action class.

Buffer necessary receipts in durable restricted external-I/O storage with event
IDs, causal references, redaction, ordering, capacity bounds, and acknowledgement.
This buffer is not an alternate planning authority. If receipt durability cannot
be maintained, stop affected work. On reconnection, reconcile policy, intent,
leases, and external outcomes before resuming or replaying anything.

Independent operator access must support stopping processes and restoring the
graph. Bound buffering and test storage exhaustion. Define recovery-time and
data-loss objectives based on actual backup and provider capabilities.

Acceptance: graph loss stops prohibited new effects; permitted in-flight work
retains receipts; replay never repeats external effects; changed policy is honored
on reconnection; emergency stop remains usable without the model or graph.

## S06 — authority root and protected promotion

Identify the principals that can change policies, deploy executors, promote
protocols, administer credentials, and modify scope. Ordinary execution principals
must not alter the rules used to authorize themselves or forge approval evidence.

Graph policy definitions remain authored and reviewed. Deployment and database
permissions enforce which identities can change their active generations. The
executor checks authority through a protected boundary; graph-native behavior does
not imply arbitrary graph-write access. Restrict dangerous procedures and I/O paths.

Delta's privileged maintenance functions must use explicit scoped execution paths,
not ambient administrator credentials available to every conversational session.
Audit exceptional recovery access and reconcile it after an outage.

Acceptance: a compromised task agent cannot edit policy, mint grants, rewrite
approval history, suppress receipts, or promote a new executable atom. A valid
administrative change produces versioned promotion and verification evidence.

## S07 — knowledge admission, correction, and retrieval

Define how raw observations, human decisions, agent claims, extracted facts, and
inferences enter usable knowledge. Preserve provenance, trust class, validity,
scope, and supporting references through summarization and retrieval.

Contradictory evidence coexists until a scoped reconciliation decision resolves
the specific claim. Summaries preserve material uncertainty and link to their
sources. Corrections supersede claims and invalidate dependent summaries where
needed; they do not erase original evidence without an explicit retention rule.

Retrieval must filter scope before disclosure and account for current goal and
policy versions. Untrusted instructions remain content through repeated summaries.
Context handoffs include outstanding decisions and unknowns rather than invented
completion. Track downstream decisions affected by superseded knowledge.

Acceptance: old direction does not silently re-enter an active plan; a corrected
fact updates dependent views; malicious instructions summarized repeatedly never
become authority; cross-project knowledge cannot leak through summaries.

## S08 — fleet capacity and human attention

Specify a hierarchy of system, project, sprint, and action budgets. Include model
usage, provider quotas, server resources, tool concurrency, and human review load.
Reserve capacity for safety, sensing, reconciliation, and recovery.

Define admission, priority, fairness, backpressure, concurrency limits, and behavior
when estimates are exceeded. Delegation transfers or reserves budget; creating a
child agent does not create new spending authority. Protect against starvation
and uncontrolled retries. Credential expiry and quota exhaustion are dependencies.

Human decisions have urgency, consequence, owner, timeout, and authorized fallback.
Group related requests; do not silently approve them because queues are long.
Measure decision backlog age and interruptions alongside compute cost.

Acceptance: a research burst cannot exhaust recovery capacity; adding an agent
does not exceed the parent mandate; one project cannot starve the other; missing
human response produces its specified fallback or blocked state.

## S09 — external commitments and compensation

For each action class define preparation, authorization, point of commitment,
receipt, verification, cancellation window, compensation, and accountable owner.
Distinguish reversible edits from messages, publication, spending, and deletion.

When outcome is uncertain, inspect provider evidence before retry. Compensation
is a new authorized action linked to the original, not a rewrite of its history.
Some commitments have no sufficient compensation and require human escalation.
Approval must state whether it covers artifact acceptance, publication, production
deployment, expenditure, or an external communication.

Acceptance: restoring graph state cannot imply that a sent message was unsent;
duplicate receipt ingestion cannot duplicate a purchase; failed compensation remains
visible with an owner. A rejected draft never advances to publication.

## S10 — compatibility and migration as controlled execution

Maintain supported combinations of schema, event envelope, runner, protocol/atom,
policy, agent configuration, model prompt, API, and client generation. State which
components pin versions for an attempt and which recheck current authority.
Revocations override an older pinned grant according to its enforcement contract.

Every batch declares compatible readers/writers, old-writer drain or fencing,
in-flight task handling, reversible changes, recovery, and effect reconciliation.
Shadow runs and backfills operate without permission to invoke external actions.
Historical events carry replay context and cannot create new live commands simply
because they pass through a current classifier.

Acceptance: old and new writers cannot race on authoritative state; a backfill
does not revive outreach; interrupted migration resumes idempotently; rollback
retains new receipts and explains any external effects it cannot undo.

## Phase assignments and owners

Owners below are component responsibilities; assign people before implementation.

| Requirement | Contract owner | Design gate | First implementation proof | Broader qualification |
|---|---|---|---|---|
| S01 | Goals and verification | Phase 2 | Phase 5 pilot outcome | Phases 7,9 |
| S02 | Graph control and Delta | Phase 2 | Phase 5 pause/claim/replan | Phases 7,8 |
| S03 | Portfolio and operations | Phase 2 | Phase 3 lifecycle fixtures | Phase 7 archival |
| S04 | Sensing and projections | Phase 2 | Phase 4 partial/stale source | Phase 9 outages |
| S05 | Runtime and recovery | Phase 2 | Phase 5 disconnect/receipt | Phase 9 restore |
| S06 | Policy and execution boundary | Phase 2 | Phases 3,5 privilege denial | Phase 6 remote exposure |
| S07 | Knowledge and retrieval | Phase 2 | Phase 4 provenance/correction | Phases 6,8 |
| S08 | Delta scheduler | Phase 2 | Phase 5 bounded admission | Phases 7,9 |
| S09 | External adapters and review | Phase 2 | Phase 5 ambiguous effect | Phases 7,9 |
| S10 | Platform release and graph migration | Phase 2 | Phase 3 migration fixtures | Every later cutover |

## C01 — combined-failure system acceptance scenario

Run first in disposable graph and fake external-provider fixtures, then in a
controlled staging environment. Never inject faults into production merely to
complete the baseline. Use event-controlled failures and capture exact versions.

### Preconditions

- Project goal G1 and bounded sprint W1 have an accepted version and known budget.
- Agent A has a scoped grant for staging artifact work; agent B lacks that grant.
- A claimed attempt has a lease/fencing epoch and a known external idempotency key.
- Receipts, projections, policies, and provider history can be independently checked.
- An unrelated project and a retained service establish isolation controls.

### Fault sequence

1. Start the attempt and deliver a duplicate input event. Only one authorized
   attempt owns the exclusive work; duplicate consumption is attributable.
2. Deliver an older runtime observation after a newer one and a partial source
   scan. Current projection must not regress or infer deletion from missing coverage.
3. Commit one simulated external effect, then interrupt receipt delivery. Its
   outcome is initially uncertain; the executor must not blindly repeat it.
4. Submit a scoped pause and new goal G2, then revoke A's capability while it is
   connected. Record when revocation is observed at the enforcement boundary.
5. Interrupt graph connectivity and restart the worker. Its old lease cannot
   authorize a new attempt. A revoked grant cannot become valid after restart.
6. Fire heartbeat, healing, and planning triggers. They cannot release the human
   hold, mint authority, or reinterpret G1 as the current goal.
7. Recover connectivity, reconcile provider history and buffered receipts, and
   replay input events. Link the committed effect once and preserve all attempts.
8. Reconcile W1 against G2; publish a proposed revised plan. Resume only with valid
   scope, current authority, released hold, and sufficient budget.
9. Inspect through a project-member client and an administrator client. Both get
   coherent explanations; project member cannot see unrelated project evidence.

### Additional orderings

Repeat with revocation occurring during disconnection: assert the declared offline
exposure bound, not impossible instantaneous revocation. Also test goal change
after an effect commits, receipt-buffer exhaustion, and provider unavailability
during reconciliation. Each produces either verified progress or owned uncertainty.

### Pass conditions

- No unauthorized new effects, duplicate known effects, or hidden budget expansion.
- Work remains paused until properly released; other authorized projects remain
  operable and the retained service is not archived by collateral state changes.
- Stale/partial sensing does not overwrite newer or intentional state.
- Already committed effects survive goal change and graph recovery as historical
  facts; acceptance against G2 is evaluated separately.
- Recovery is bounded by the selected objectives or escalates with a named owner.
- UI and MCP explain requested controls, applied controls, outage, unknown outcome,
  reconciliation, and the next permitted action from the same evidence.
- TestRun records target, generations, expected/actual results, event order, and
  independently inspected provider and graph evidence.

Phase 2 defines expected outcomes and numeric bounds. Phase 5 proves the core
scenario; Phase 6 adds remote-scope assertions; Phases 7–9 broaden concurrency and
duration. Passing this exercise supplements rather than replaces isolated tests.
