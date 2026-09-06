# Graph identity, state, and evidence contract

Status: proposed v2 semantics, not a deployed schema. Covers A01–A04, A06–A07,
A10–A14, S01–S07, S10. Existing constraints and data require migration preflight.

## Canonical identity

Keep existing stable node_id values where possible. Select one canonical Project
per verified real project; attach historical identities through explicit aliases
and migration decisions. Never merge by name alone. A scoped alias resolver returns
one canonical identity or a visible conflict. The Cajon eco record needs verification.

Every active core node has scope_id and scope_kind (platform or project); adapters
support old project properties during migration. Store canonical IDs rather than
human names in new references. Historical names remain labels, not authorization.
Platform observations referring to a product carry both observer and subject scope.

Preserve Being being-seedforth, ForestPromise seedforth-forest-promise, and Purpose
purpose-seedforth as existing root anchors. Link them to platform/repository and
reviewed governance records without creating another competing root.

## Work hierarchy and relations

Proposed canonical hierarchy: Project HAS_WORKSTREAM Workstream HAS_MILESTONE
Milestone HAS_WORK_ITEM WorkItem. Milestone ADVANCES EntityGoal. EntityGoal remains
the existing goal vocabulary. WorkItems may additionally record direct goal links.
Shared milestones require a declared owner; dependencies use explicit bridge edges.

WorkItem ASSIGNED_TO SubAgent is the canonical assignment direction, matching the
observed pilot edges. ExecutionSession EXECUTES WorkItem and PERFORMED_BY SubAgent.
AgentProcess BACKS SubAgent and RUNS_ON Server. CodeChange points to Repository
and exact base/head revisions; raw patch content stays in Git/artifact storage.
Do not create fake active parents during migration: unresolved historical work
is held for classification before it becomes eligible for execution.

## Lifecycle and version rules

| Object | Proposed states and semantics |
|---|---|
| WorkItem | proposed → ready → claimed → in_progress → review → done; blocked/cancelled are explicit branches |
| ExecutionSession | queued → running → succeeded/failed/aborted/expired; pause tracked as a control state |
| Control state | none / pause_requested / paused / resume_requested / abort_requested / applied_or_failed |
| Signal | received → accepted/denied → claimed → acknowledged → applied/failed/expired/cancelled |
| DecisionRequest | pending → approved/rejected/deferred/expired; response creates a separate Decision |
| ActionProposal | proposed → accepted/rejected/expired; accepted proposal links to work, mandate, and decisions |
| Project | portfolio lifecycle separate from work permission, service obligation, runtime, and evidence health |

Map legacy todo→ready only when eligibility requirements pass, otherwise proposed.
Map in_review→review. Historical done remains a historical claim with verification
status; do not retroactively invent proof. paused/failed do not overload WorkItem
state when the failure belongs to one attempt. Rejection can create a new attempt
on the same task after revision; previous evidence persists.

Every authoritative aggregate carries state_version. Transition requests specify
expected_version. A graph transaction locks/serializes the aggregate using a
tested Neo4j-compatible mechanism, rechecks authority and preconditions, increments
version, and appends StateTransition atomically. Implementation must prove atomic
claim behavior under concurrent transactions; a read-then-write query is insufficient.

## Observations, signals, and projections

Observation records something a source reports. Signal requests a controlled
change. A transport envelope can carry either but routes by validated kind.
An observation cannot become a command through generic replay or interpretation.
DecisionRequest is a gate only where policy requires one; not every read or signal
creates a human approval request.

Core envelope: schema_version, event_id, scope_id, kind, source, source_revision,
occurred_at, observed_at, ingested_at, correlation_id, causation_id, actor_id,
payload_ref/hash, trust_class. Optional source_sequence is mandatory when supplied
by a source with ordering guarantees. Never compare unrelated source sequences.

Critical event records are append-only through normal execution APIs. Corrections
link to superseded evidence. Current projections record reducer generation,
last applied source cursor, as_of, evidence status, and supporting event IDs.
Authority decides conflicts; timestamps alone do not override owner intent.

Time fields distinguish event time and ingestion. Validity intervals apply to
time-sensitive facts. Snapshot claims require observation coverage. Delayed input
can update history without regressing present state. Unknown is not a zero score.

## Execution and policy evidence

Add semantic records for Invocation, Receipt, StateTransition, Observation,
PermissionDecision, and TestRun where no existing label safely expresses them.
Select final labels in authored schema review. An invocation links attempt,
capability, actor, originator/mandate, policy generation, target, input hash,
idempotency key, outcome status, and receipts. Sensitive input is referenced/redacted.

ProtocolRun records exact protocol generation and every attempted atom generation,
start/end/status/error code, not just aggregate ok counts. QueryTrace distinguishes
read/discovery from execution and links run/atom where applicable. A failed atom
halts dependent steps unless an explicitly declared recovery edge permits continuation.

Permission records are immutable evaluations, not grants by themselves. A grant
records issuing authority, allowed operations, resource/destination scope, budget,
expiry, and revocation epoch. Active policy generations have protected promotion.
High-risk evidence and policy writes use separate principals from task agents.

## Schema and migration invariants

Preflight missing IDs, duplicates, alias conflicts, scope gaps, and required edge
directions before adding constraints. Uniqueness alone does not guarantee fields
exist. Use validation protocols and boundary enforcement for required-field and
relationship constraints not supplied by the selected database configuration.

Each schema bootstrap is versioned, reviewed, idempotent for authored topology,
and verified against a disposable copy before live promotion. Record migration
receipts separately from topology. Compatibility readers expose one projection;
old writers are drained/fenced before authority changes. See migration plan.

Acceptance: one canonical identity per active product; no scope escape; concurrent
claim has one winner; replay changes no external effects; no stale event overrides
a hold; every new done task has required acceptance evidence; each state explains
origin, time, transformation, authority, and verification.
