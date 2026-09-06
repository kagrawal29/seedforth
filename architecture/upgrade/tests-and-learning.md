# Behavior verification, useful autonomy, and learning

Status: verification contract under implementation. Exact executed coverage and
remaining gates are recorded in execution-ledger.md; this document is not itself
evidence that every scenario passed.
Covers A01–A17, S01–S10, C01; product experience coverage U01–U16.

## Test architecture

Owner direction: every human-facing interface built or changed in this upgrade
must be exercised end to end using Playwright CLI. The implementing agent may
imitate the human operator under the owner's delegated testing authority. Mark
such reviews as simulated/delegated, never as personal owner acceptance. Target
full operational readiness by the owner's next-day return, without weakening the
requirements or claiming an unelapsed unattended observation period.

Test the actual browser interactions, not only DOM existence or API responses:
desktop/mobile, scoped login/logout/reconnect, inspection, controls, exact evidence,
error/stale/loading states, concurrent responses, revocation, and failed operations.
Synthetic-response browser regression and browser-to-real-gateway/graph staging
acceptance are distinct evidence levels. Public remote authentication, conversation,
team administration, review and any new interface need their own runnable journeys.
Retain CLI version, source revision, scenario results and non-sensitive screenshots.
Never use owner production credentials in recorded traces, snapshots, or CLI args.

Layer 1 tests contracts against minimal disposable fixtures: identity, scope,
state transitions, permissions, ordering, and replay. Layer 2 tests adapters with
fake/sandbox providers and real serialization. Layer 3 tests complete graph-agent
workflows in staging. Layer 4 uses approved live probes and unattended observation.
Read-only baseline inspection never runs a test that writes evidence to live state.

Test the runner using deliberate assertion failure, query error, timeout, wrong
database, stale result, and incomplete fixtures. It must distinguish pass, fail,
error, timeout, skipped, and unknown. Only an actual fresh pass counts as verified.

TestRun is append-only through normal APIs and includes test/suite/version, target
identity, source/schema/policy generation, fixture or snapshot identity, runner,
start/end, assertion hash, expected/actual, result, and evidence. A latest-summary
property is derived. Failure to persist evidence prevents a claim of verified pass.

## Required scenario families

| Test family | Required assertions | Coverage |
|---|---|---|
| T01 identity | Alias resolution, duplicates preflight, missing scope, bridge isolation | A01,A11,S03 |
| T02 sensing | Duplicate/late/malformed/partial input, freshness, outage, cursor recovery | A12–A14,S04 |
| T03 execution | One claimant, worker fencing, restart, timeout, uncertain external effect | A03–A04,S05,S09 |
| T04 permission | Scope denial, malicious content, policy edit denial, revoked grant, approval replay | A05,S06–S07 |
| T05 evidence | Exact atom generation, error lineage, no false positive progress, criterion check | A06–A07,A10,S01 |
| T06 human loop | Board/MCP parity, accepted versus applied control, rejection/rework, reconnect | A17,U01–U16 |
| T07 lifecycle | Sleep differs from archive; retained services; goal change and holds | A02,S02–S03 |
| T08 capacity | Budget conservation, quotas, fairness, bounded retries/delegation | S08 |
| T09 migration | Repeat bootstrap, replay without effects, incompatible writer rejection, rollback | S10 |
| T10 healing | Violation→diagnosis→repair→independent recheck→resolve/escalate | A08 |
| T11 learning | Dream provenance/use, no authority promotion, real execution attribution | A07,A09 |
| T12 retention | Preserve required evidence, redaction, archive retrieval/restore | A15 |
| T13 Graphify | Known extraction, incomplete scan, revision drift, deterministic join, secret exclusion | A16 |
| C01 compound | Goal change, pause, revocation, partial observation, outage, restart, ambiguous effect | S01–S10 |

Each changed graph behavior needs a negative test that fails if it is absent,
disconnected, scoped incorrectly, or unable to establish its promised postcondition.
Tests must not simply read the behavior's self-written healthy flag.

## Pilot outcome evaluation

The upgrade includes two representative workflows for the actual active products.
Synthetic fixture goals unblock implementation; real acceptance thresholds are
approved before live trials. Record the task selected, its connection to direction,
authority, attempt, artifact, verification, review, useful outcome, and next step.

Report accepted outcomes per period, failure/blocked rate, intervention count,
outcome-evidence completeness, budget use, and age of unresolved decisions. Pair
metrics with actual artifacts and human review. Do not collapse them into a single
autonomy score. A successful no-work or safe-stop outcome is correct operation,
but it is not useful project progress.

Acceptance ladder: deterministic fixtures → sandbox end-to-end → one approved
bounded live workflow → repeated outcomes → overnight → multi-day → 30-day real
operation. A simulated clock tests transitions but does not prove long-term uptime.

## Invariants and healing

Classify each existing invariant constitutional, operational, advisory, or retired.
Record claim, population/scope, read-only check, positive/negative fixtures,
freshness, severity, permitted repair, forbidden changes, postcondition, evidence,
and failure/escalation. Meta-tests check the full declared enabled population.

Repair is an authorized task with attempt receipt, not a special permission bypass.
One incident owns repeated failures; retry budget and cooldown stop storms.
Verify changed topology and recompute the invariant independently. Failed repair
or stale recheck cannot resolve the incident. External compensation is separately
authorized, and health reporting distinguishes attempted from resolved.

## Dreaming, reinforcement, and memory

Dream hypotheses carry origin, scope, generation, confidence, expiry, and later
query/decision/action/validation references. Separate being retrieved from helping
produce a verified result. Measure usefulness for a sample before broader promotion.
Inferred edges cannot grant access or redefine governing facts.

QueryTrace records semantic discovery separately from actual atom execution.
Reinforcement derives from deduplicated evidence and identifies the exact generation.
Repeated UI polling cannot masquerade as autonomous learning. Retire stale summaries
and invalidate dependent plans when accepted facts change.

## Retention and observability

Proposed defaults for review: retain critical decisions, invocation references,
acceptance evidence, and migrations for the project's required audit horizon;
retain verbose activity and raw payloads for shorter configurable periods. No
arbitrary universal deletion schedule is introduced without obligation assessment.

Publish verified behaviors versus declared behaviors, stale streams, unknown scope,
failed tests, orphaned accepted work, unauthorized attempts, unresolved effects,
repair resolution rate, and useful dream outcomes. Instrumentation must have cost
limits and failure alerts of its own; telemetry volume is not a success measure.

Hard release gates: no demonstrated scope bypass, silent replay effect, forged
approval, false success on error, unrecoverable migration, or unresolved duplicate
effect. These cannot be hidden behind an overall passing percentage.
