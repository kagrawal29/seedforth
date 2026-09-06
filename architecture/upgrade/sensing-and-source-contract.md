# Sensing, source reality, and mutation lineage

Status: proposed. Observations below refer to the partial baseline, not a complete
stream census. Covers A06–A07, A12–A16, S04, S07, S10.

## Stream contract

Every source registers authority, owner, project/platform scope, adapter source
revision, schema, trigger, expected cadence, freshness limit, coverage, cursor,
last attempt/success/consumption, lag, retention, permissions, consumers, mutations,
verification, retry, and escalation. Every writer registers its actual privileges
and intended writable labels/properties/relationships separately.

Stages: observe → validate → normalize → resolve identity → reconcile/classify →
append transition → update projection → notify consumers. Every input ends as
applied, duplicate, held-for-conflict, rejected, or failed with a reason. Rejected
and failed input is not silently dropped or marked metabolized successfully.

Raw restricted payloads may live in an external artifact store. Mycelium retains
source identity, hashes, lineage, and normalized durable facts. Logs and attachments
do not need full duplication into graph nodes. Redaction precedes extraction or
model exposure; access to source artifacts is checked independently.

## Initial source/writer map

| Source | Known current mechanism | Current limitation | Proposed destination/verification |
|---|---|---|---|
| Supervisor/fleet | AgentProcess and active SubAgent records observed | Consumer freshness and scope joins pending | RuntimeObservation → process projection; recent independent probe |
| Release/configuration | Current symlink and Git revision inspected | Not all effective config linked | Versioned source/runtime observation with drift finding |
| Heartbeat | 1-minute timer → deployed graph-runner → live atom chains | Per-atom evidence absent; error status weak | Versioned ProtocolRun/atom receipts and postconditions |
| Dream/division work | Live ExternalAtoms reference legacy worker commands | All 30 recorded pilot runs failed | Structured executable reference and typed arguments under grant |
| Lifecycle | Live lifecycle atoms; deployed provisioner writes hibernation | Runtime and business lifecycle conflated | Separate lifecycle decision and process observation |
| Progress | ProgressEvent, commit/artifact classification, legacy worker | Failure has positive weight; missing entity on some events | Typed attempt outcome → criterion-specific verified progress |
| Git | Pilot repositories/worktrees and commits inspected | Log commits resemble output; deployment not verified | Commit/artifact observation → review evidence, never automatic goal success |
| Human channels | Existing Delta/Charlie entrypoints | Complete identity/approval lineage pending | Message observation → proposal/request → verified decision |
| Providers | Existing capabilities and integrations described | Current subscriptions/scopes/results unverified | Provider-specific outcome/metric observations and receipts |
| Graphify | Experiment reported in audit | Exact artifact location/version not recovered yet | SourceSnapshot → bounded facts → discrepancy observations |
| Test/healing | Historical TestCase/ProtocolRun machinery | No TestRun records in baseline | Target-specific TestRun and repair recheck |
| Direct/admin/bootstrap | Graph tools and privileged access exist | Full writer census incomplete | Protected promotion/admin events with migration correlation |

Phase 0 must inventory every timer, cron user, service, webhook, watcher, manual
tool, and database credential capable of writing. An absent named Protocol does
not establish an absent scheduler. Inspect actual process entrypoints and callers.

## Freshness defaults proposed for pilot review

Fleet collection every 60 seconds, stale after three missed intervals. Protocol
freshness uses its declared cadence plus maximum expected run duration, not one
global 24-hour threshold. Provider thresholds follow their actual publication and
rate-limit constraints. Source snapshots become out-of-date when a new relevant
revision is observed, even before their time-to-live expires.

Record attempted versus successful collection. Quota exhaustion is an outage with
an owner. Event timestamps do not substitute for adapter heartbeat. Backoff has
jitter, bounded attempts, and an incident after the stream's allowed outage window.
Critical thresholds remain review targets until measured against deployment.

## Graphify integration

Recover the original experiment outputs and pin extractor provenance before
reproducing it. The audit's public Graphify experiment and local artifact-graphify.py
are different mechanisms; do not assume interchangeable behavior or schemas.

Adapter input is an immutable source snapshot: repository ID, revision, selected
paths, content hash (including dirty content if intentionally included), extractor
version/configuration, start/end, permissions, coverage, and failures. Run extraction
without access to production secrets or write-capable runtime credentials.

Output distinguishes deterministic source facts, inferred relationships, ambiguous
matches, excluded content, and extraction failures. Stable source keys include
repository/revision/path/symbol; changed symbols are new observations, not silent
rewrites of deployed runtime relationships.

Deterministic joins first compare protocol IDs, executable paths, deployment SHA,
service entrypoints, and known dependencies. An LLM may explain discrepancies and
propose tests. A verified comparison or approved promotion can establish a stronger
relationship; semantic resemblance alone cannot assert implementation or authority.

Start with Delta/Mycelium execution and one active product. Validate a known call,
a removed implementation, a renamed symbol, partial extraction, and secret exclusion.
Report precision/coverage on known fixtures, runtime, and cost. If the experiment
cannot be reproduced, keep adapter selection unresolved while retaining this sensor
contract; do not call the integration complete based on a new unrelated extractor.

## Replay, deletion, and uncertainty

Deduplicate by source identity plus stable event ID; hash fallback includes source
scope and occurrence identity. Do not deduplicate distinct real-world events merely
because payloads match. Use source cursor ordering where supported and event-time
rules otherwise. Cursor advances only after durable processing disposition.

Snapshot deletions require complete coverage or authoritative tombstones. Partial
lists cannot remove objects. Replays run in observation-only mode; reducers cannot
emit executable commands unless explicitly promoted as a new authorized decision.
Historical imports must never resend messages or revive retired work.

Knowledge admission preserves provenance, trust, validity, and contradictions.
Retire dependent summaries when their underlying accepted claims are superseded.
Fresh sensing does not authorize a change of goal or permission.

Acceptance: every pilot state can name source, time, transformation and consumer;
failed reads remain different from zero data; partial source coverage is visible;
lost/late events reconcile safely; no adapter can write outside its contracted scope.
