# SeedForth operating system upgrade: integrated specification and phased plan

Status: adopted v0.3, 2026-09-06. Autonomous implementation and deployment authorized.
This is the consolidated upgrade program derived from the full design discussion.
It specifies the work to design, verify, migrate, and deliver the system. Open
decisions and unverified runtime claims are explicit. Actual completion is tracked
in architecture/upgrade/execution-ledger.md, not inferred from this specification.

The [complete review package](upgrade/README.md) now contains supporting proposed
contracts, wireframes, delivery packages, and specific decisions D01–D15. These
make this plan reviewable; incomplete live inventory is separately documented and
remains a gate on affected migration work.

## 1. Outcome and scope

SeedForth should let humans lead an autonomous team remotely. Humans express dreams,
choose goals, change direction, review results, and decide material tradeoffs.
Agents perform bounded work continuously, coordinate, recover where authorized,
and show tangible evidence of progress. The system remains understandable at daily,
weekly, or month-long intervals of human attention.

The intended active products are Flowing Indian and Cajon Sensei. SeedForth is the
platform supporting them. Other products require deliberate archival dispositions.
Keep their history, decisions, repositories, and evidence recoverable. A product
leaving the active portfolio does not imply deleting its repository or shutting
down a hosted service relied on by customers.

Mycelium remains the executable graph program and durable system of record.
Delta orchestrates agents, execution, and recovery. Charlie handles alignment and
human communication. The board and remote MCP expose the same system state and
authority. Graphify contributes observations about source reality.

The upgrade includes the graph itself, all mechanisms that update it, authorization,
agent execution, testing, sensing, learning, runtime recovery, and human experience.
It must account for every finding from the audit, even when a finding is shown to
be historical or a lower-priority implementation is explicitly deferred.

## 2. Evidence and document authority

Read these together:

- [Historical live audit](../docs/mycelium-live-audit.md).
- [Engineering audit synthesis](../docs/mycelium-engineering-audit-report.md).
- [Foundation handoff](../tetrahedron/projects/mycelium/docs/session-handoff-foundation-2026-09-06.md).
- [Pre-foundation execution plan](../tetrahedron/projects/mycelium/docs/execution-plan.md).
- [Original operating specification](../tetrahedron/projects/mycelium/docs/spec-v1.md).
- [Platform plan](../SEEDFORTH-PLATFORM-PLAN.md).
- [Current platform contracts](../platform/contracts/README.md).
- [State and synchronization contract](state-and-sync.md).
- [System-wide contracts and combined-failure acceptance](upgrade/system-contracts.md).

The historical execution plan proposed VibeKanban and a bridge. The later handoff
rejected external task-state synchronization and chose a custom graph-backed UI.
Preserve the original experience goals; do not revive its superseded bridge plan.

The audit explicitly inspected 143.110.226.214. The foundation handoff describes
delta2, 185.192.96.100, as current authority. Audit counts, runtime states, and test
results must be revalidated against delta2. Do not access deprecated Maverick or
pulse graphs. A [partial live delta2 baseline](upgrade/baseline-and-findings.md)
was captured on 2026-09-06 at 13:49 UTC. Full writer and signal tracing remains pending.

Local contracts also disagree: Workstream/Milestone placement, WorkItem states,
assignment relationship direction, and Signal/DecisionRequest semantics vary.
Resolve them using deployed source, graph observations, and an explicit design
decision. Do not seed a new vocabulary on top of existing ones by accident.

The earlier planning drafts under root docs/ are local files in an ignored folder.
This architecture document is the versionable planning anchor. Supporting contracts
should live under architecture/upgrade/ as they are authored. Audit artifacts must
be retained and made available to reviewers through a deliberate documentation
decision; do not unignore all research documents or ingest historical credentials.

## 3. Accepted direction, proposed decisions, and open choices

### Accepted user direction

- Plan and specify before operational changes.
- Active products: Flowing Indian and Cajon Sensei.
- Graph must accurately map current state and support a complete agent work loop.
- Address all audit findings, including sensing, lineage, testing, and learning.
- Distinct Charlie alignment and Delta orchestration responsibilities.
- Remote operation, long sprints, deep work, team expansion, and extended absence.
- Calm, high-quality human interface with fine control and full inspectability.
- Admin and project access scopes; graph exploration plus speaking to Delta is
  preferred over a large catalog of narrow MCP business tools.
- Integrate source sensing informed by the Graphify experiment.
- Guardrails must hold when malicious content reaches agents.

### Proposed design defaults requiring specification review

- Durable events and observations underpin material current-state projections.
- Start with one Flowing Indian execution slice, then generalize to Cajon Sensei.
- Build a read-only interface early after the first trustworthy projections exist.
- Every external action carries explicit caller or standing-mandate authority.
- Capability enforcement is independent of language-model compliance.
- Use additive graph migrations and compatibility readers before retiring writers.
- Grow unattended operation through observed trials of increasing duration.

### User choices required before dependent behavior is enabled

- Measurable goals and success criteria for both active products.
- Team members, project visibility, and who may approve which actions.
- Spend limits, publication/deployment authority, and communication permissions.
- Which archived products still need hosting, maintenance, or customer obligations.
- Notification preferences, emergency contact, and unattended decision fallbacks.
- Preferred first remote clients and concrete deep-work workflow.

Resolve these with concrete proposals in the relevant phase. They do not block
source inspection, audit mapping, contract drafting, or interface prototypes.

## 4. Experience requirements

| ID | Journey | Required behavior | Human-visible evidence |
|---|---|---|---|
| U01 | Return for the day | Prioritize meaningful changes, decisions, and next work | Outcomes with dates, links, and uncertainty |
| U02 | Set direction with Charlie | Turn discussion into proposed goals and constraints; record acceptance | Direction version, author, rationale, affected work |
| U03 | Delegate to Delta | Convert intent into bounded work under explicit authority | Plan, owner, budget, checkpoints, execution ID |
| U04 | Start a long sprint | Continue after client disconnect or context expiry | Durable progress, attempts, checkpoints, final report |
| U05 | Work deeply | Inspect research, plans, diffs, tests, and outputs while steering | Source-linked artifacts and recorded plan changes |
| U06 | Inspect the team | Distinguish agent identity, process, model session, and work attempt | Current assignment, health, capability, activity, cost |
| U07 | Control work | Pause, resume, abort, retry, reprioritize, or reassign precisely | Requested/acknowledged/applied result and affected scope |
| U08 | Review a result | Approve or reject the exact presented output | Artifact version, tests, reviewer, feedback, resulting transition |
| U09 | Add a teammate | Authenticate remotely and grant project scope | Membership, access boundaries, revocation history |
| U10 | Add or retire an agent | Specify role, capability, budget, and lifecycle | Provisioning receipt, ownership, work handover |
| U11 | Return after a month | Understand progress, decisions, failures, and remaining work | Goals advanced, delivered artifacts, costs, unresolved blockers |
| U12 | Handle a failure | See cause, retries, owner, and recovery options | Incident timeline and independently checked recovery |
| U13 | Ask why | Explain a status, assignment, priority, or decision | Cause, source, time, authority, transformations, verification |
| U14 | Explore through MCP | Read scoped knowledge and converse with Delta | Consistent scope across traversal, delegation, logs, and artifacts |
| U15 | Change direction mid-sprint | Reconcile new intent with claimed work and effects in flight | Superseded plan, cancelled future actions, preserved completed outcomes |
| U16 | Operate from a phone | Review and decide without reading raw telemetry | Compact context, clear consequence, accessible controls |

The month-away promise is authorized progress where feasible, with explicit
blocked state when external dependencies prevent it. The system must not invent
busywork, manufacture progress, or exceed its mandate to keep appearing active.

## 5. Human interface specification brief

Design and review wireframes in Phase 1, before backend changes fix the UX shape.

### Default surfaces

1. Home: what changed since this person last looked, what needs their decision,
   what is moving, and material risk. Group low-level events into meaningful work.
2. Portfolio: active projects and their goals, evidence freshness, and exceptions.
   Archived projects remain accessible through history rather than active queues.
3. Project: dream, goals, plan, board, team, dependencies, and recent outcomes.
4. Attention: owned decisions, blocked work, conflicts, permission requests,
   repeated failures, and their consequences. Deduplicate recurring alerts.
5. Work inspector: purpose, plan, attempts, permissions, tool receipts, artifacts,
   tests, review, and next action. Terminal and raw logs are deeper layers.
6. Team: agents and humans, roles, scope, assignments, availability, and cost.
7. System view for admins: sensors, graph/runtime divergence, releases, protocols,
   invariants, source changes, capacity, and recovery.
8. Conversation: Charlie and Delta selectable independently with clear context
   and a shared decision history. Cross-channel continuation must preserve identity.

### Interaction rules

- Board labels are a human projection; document their mapping to internal states.
- Never display requested pause as applied pause or a commit as verified delivery.
- Show enough evidence to assess a decision without opening raw graph tools.
- Stale, conflicting, disconnected, empty, denied, and failed states need designs.
- Bind approval to the exact action, artifact version, scope, and policy context.
- Avoid credential-bearing URLs; session and deep-link access must be scoped.
- Updates survive reconnect through a durable cursor or equivalent recovery design.
- Accessibility, mobile layout, keyboard control, and error recovery are acceptance
  requirements. Numeric latency and notification targets are selected in Phase 1.

## 6. System boundaries and closed loop

```text
World: source, runtime, providers, humans, agents
  → sensors and bounded external I/O
  → observations with identity, time, source, and scope
  → graph normalization, reconciliation, and state transitions
  → current projections, goals, focus, and proposals
  → ownership, authorization, and bounded execution
  → external results and receipts
  → independent postconditions and goal progress
  → next action, learning, or escalation
```

Git remains authoritative for versioned source and reviewed graph definitions;
Supervisor supplies process observations; providers supply their account facts.
Mycelium represents those observations and governs durable intent, work, decisions,
permissions, behavior, evidence, and derived state. Source observations and model
inferences do not silently override human intent or external authoritative facts.

Graph transformations and domain decisions belong in authored Cypher/protocols
where applicable. Runtime code provides execution machinery, transport, external
I/O, and enforcement boundaries. Policy enforcement cannot depend solely on a
cooperative agent or on writable graph rules that the same agent can replace.

## 7. Graph and temporal model to settle

Define the smallest sufficient vocabulary using stable existing labels wherever
their meaning fits. The following are semantic responsibilities, not an instruction
to add every term as a new label.

| Domain | Required distinctions |
|---|---|
| Identity | Platform, product, canonical identity, historical alias, owner, scope |
| Infrastructure | Repository, checkout, release, server, service, process, configuration observation |
| Intent | Dream/mandate, goal, measure, workstream, milestone, bounded work, dependency |
| Agency | Agent identity, persona, model, capability, principal, delegated authority |
| Execution | Sprint, task attempt, invocation, receipt, effect, artifact, review |
| Sensing | Stream, observation, classification, rejection, transition, projection |
| Governance | Policy generation, approval, decision, proposal, conflict, incident |
| Behavior | Protocol/atom generation, trigger, run, test case/run, invariant |
| Learning | Discovery, execution attribution, hypothesis, use, validation, reinforcement |

For each critical fact specify origin, owner, scope, source generation, event time,
observation time, ingestion time, validity interval, confidence where meaningful,
verification, expiry, correction, and causal links. An append-only receipt may
need restricted payload retention; do not retain secrets or sensitive raw content
indefinitely merely to claim immutability.

Separate intended project lifecycle from runtime liveness and evidence health.
A supervised process does not authorize project reactivation. Missing observations
mean uncertainty according to a freshness contract, not proof of inactivity.

Resolve whether goals span workstreams, whether milestones belong within them,
and how shared dependencies cross project scopes. Record safe bridge rules.
Keep task attempts distinct from persistent processes and LLM sessions.
Specify optimistic version checks, atomic claims, leases, fencing of stale workers,
and protection against late results rewriting newer decisions.

## 8. Sensing, graph writers, and Graphify

Build two linked inventories: all sources that the system observes, and all
mechanisms permitted or technically able to mutate the graph. Include manual
queries, bootstrap, agent tools, scripts, schedules, graph-native protocols,
repair routines, and inherited credentials with broad privileges.

Every stream row must contain:

- Source authority, scope, owner, adapter path, source revision, and trigger.
- Declared cadence, actual schedule, last attempt, last successful observation,
  last consumed sequence, processing lag, and freshness threshold.
- Input schema, source ID, deduplication key, ordering and late-arrival behavior.
- Raw evidence location, redaction, retention, and access boundaries.
- Consumer protocol and exact atom generation; labels/properties/edges writable.
- Classification, rejected/unknown paths, resulting transitions and projections.
- Downstream consumers, feedback signal, verification, retry, and escalation.

Start with Git commits/artifacts, Graphify snapshots, supervisor and fleet,
service/resource probes, provider metrics and outcomes, conversations, human
decisions, task execution, tool receipts, protocol runs, invariant checks,
healing, dreaming, deployment/configuration, and administrator writes.

Test initial snapshots and incremental changes, deletion/tombstones, duplicate
delivery, delayed/out-of-order input, partial extraction, provider rate limits,
clock skew, outage, backfill, and reconciliation. Replays must not resend messages,
redeploy code, re-spend money, or re-emit already applied commands.

Graphify integration begins by reproducing the recorded experiment and inspecting
its artifacts/version. Research current official technical documentation before
selecting an implementation. Compare deterministic source extraction separately
from LLM-inferred relationships. Capture repository, Git revision, dirty content
hash if applicable, extractor version, coverage, failures, and capture time.

Join source facts with graph behavior and deployed runtime by stable identifiers.
Produce reviewable discrepancy findings for missing implementation, unobserved
behavior, ungoverned code paths, and generation mismatch. An inferred match cannot
grant access or become an authoritative implementation relationship automatically.
Begin with the platform and one active project; expand coverage after measured cost
and accuracy. The graph should know what the sensor did not inspect.

## 9. Scoped access, Delta delegation, and prompt injection

The preferred remote interface is scoped Mycelium exploration plus a durable
conversation with Delta. The MCP adapter and board use a shared application and
policy boundary. Design actual auth/transport details after checking current
official specifications and testing selected clients; universal client support
must not be assumed.

Separate authenticated human, client application, agent identity, persona,
project membership, and standing autonomous mandate. Effective permission is
bounded by the originating authority, delegated capabilities, resource scope,
current policy, and live revocations. Delta's system privileges do not enlarge
the authority of a teammate's conversational request.

Investigate safe graph query expressiveness: traversal depth, available labels,
read procedures, resource limits, aggregates, relationship leakage, and redaction.
Substring checks or a model-generated project filter are not an isolation boundary.
Test cross-project identifiers, inference through counts/errors, shared nodes,
cached results, exported artifacts, logs, and conversation history.

Threat-model malicious web pages, messages, repository instructions, documents,
tool outputs, graph knowledge, and compromised agents. Source content retains
its trust and provenance throughout summaries. Text cannot grant capabilities,
edit governing policy, disable auditing, or impersonate a human approval.

Specify enforceable controls for secret retrieval, command/tool execution,
network destinations, repository scope, production changes, spending, and message
sending. Bind approvals to exact action details and recheck before effect. Revoke
running jobs' future access and record effects already in flight. Add test cases
for malicious instructions, confused-deputy escalation, approval replay, credential
exfiltration, policy tampering, and cross-project memory contamination.

Independent operational access and pause controls must remain usable if the model
or graph is unhealthy. Define recovery identities and audit their exceptional use.
No architecture can promise perfect injection detection; acceptance is that tested
authority boundaries hold even when an agent follows hostile instructions.

## 10. Autonomous execution and collaboration

A sprint contract specifies goal, expected deliverables, acceptance criteria,
project, responsible agent, allowed capabilities, budget, concurrency, duration,
checkpoints, dependencies, escalation, and terminal conditions. It survives client
disconnect and process restart as durable graph state.

Specify proposal → assignment → claim → permission → invocation → effect → receipt
→ verification → progress → review/next action. Distinguish execution success,
artifact acceptance, production deployment, and business outcome. Goal progress
needs evidence appropriate to that goal, not a generic commit score.

Use idempotency keys when a provider supports them. For uncertain external outcomes,
reconcile before retrying. Do not claim universal exactly-once execution. Protect
concurrent work with worktree/branch isolation, assignment leases, review, and merge
rules; an expired worker cannot continue committing authoritative task transitions.

Agent-to-agent delegation must preserve owner, scope, budget, and causal history.
Prevent unbounded agent spawning, circular delegation, retry storms, and conflicting
edits. Model context expiration and handoff from durable decisions and checkpoints.
Persist enough explanation for another agent to resume without inventing history.

Workstream split, merge, and fallback operations require lineage, dependency checks,
budget conservation, and appropriate approval. Agents may propose improvements to
protocols but cannot promote their own unreviewed safety-policy changes.

Define unattended fallback work in advance. Blocked work can yield to another
authorized task; the system must not reinterpret an absent human's silence as
approval. Notifications should group related incidents and explain consequence.

## 11. Testing, healing, learning, and retention

Create a behavior map for every executable or state-transforming component:
owner, scope, trigger, inputs and freshness, preconditions, transition, effects,
postconditions, receipts, failure/retry/escalation, tests, and latest evidence.
Track declared, implemented, wired, enabled, observed, tested, and verified as
separate dimensions. Report unknown, stale, skipped, and degraded explicitly.

Test the test runner with known failing fixtures before trusting its verdicts.
TestRun evidence includes target environment, snapshot/as-of marker, source and
schema generation, assertion hash, timestamps, expected/actual result, error,
runner, and relevant evidence. Historical passing properties are summaries only.
Prevent tests from merely reading health flags set by the behavior under test.

Invariants need positive, negative, scope, freshness, timeout, repair, boundary,
and postcondition scenarios as applicable. Classify constitutional, operational,
advisory, and obsolete invariants. Coverage queries must inspect the full intended
population; a scoped meta-test must not be advertised as whole-system coverage.

Healing records violation, diagnosis, permission, attempt, changed state, recheck,
resolution or escalation. Deduplicate incidents and bound attempts. Verify rollback
or compensation without erasing evidence of the failed repair.

Dreaming records origin, confidence, expiry, and downstream use or validation.
Hebbian attribution distinguishes discovery, execution, co-firing, and actual
benefit. Do not reward dashboard polling as successful autonomous learning.
Promote behavior only through an explicit reviewed and tested path.

Retention considers operational, structural, evidentiary, human, and learning
value plus privacy and cost. Define which projections can be rebuilt over which
retention horizon. Preserve required historical references before expiring raw
telemetry. Validate archival restoration and prevent automated reactivation.

## 12. Phased delivery and dependency gates

Phases 0–2 are preparation: documentation, read-only investigation, and design
prototypes. Phases 3 onward are the proposed implementation program, entered only
after integrated design review. Dates and estimates follow the verified inventory;
the older hour estimates are not reused for this substantially larger upgrade.

### Phase 0 — establish current reality

Purpose: identify which audit problems exist now and what actually changes state.

Deliverables:

- Dated delta2 baseline with release, schema, graph identity, runtime, schedules,
  active projects, agents, integrations, and current verification evidence.
- Source-to-runtime inventory, graph-writer inventory, and signal lineage rows.
- Revalidated audit findings with source links and explicit unknowns.
- Portfolio inventory and proposed archival dispositions, including dependencies.
- Graphify experiment artifact inventory and reproducibility assessment.

Read deployed source and bounded graph observations; do not run live writers,
repair routines, bootstrap, or tests that create evidence during this inspection.
Compare both intended active projects with their actual graph and agent state.

Exit: each known critical writer/stream has an owner, trigger, scope, mutation set,
and consumer or a recorded gap; legacy findings are distinguished from delta2
facts. Unresolved baseline access or evidence gaps are visible, not filled by guess.

### Phase 1 — product experience and operating contracts

Depends on initial Phase 0 inventory; scenario design can proceed in parallel.

Deliverables:

- U01–U16 scenarios with concrete examples for both products.
- Goals, authority matrix, unattended mandate template, and decision policy.
- Board, attention, project, execution, team, and return-after-absence wireframes.
- Charlie/Delta responsibilities, handoff behavior, and shared conversation state.
- Product disposition proposals and client compatibility research requirements.

Exit: the user can walk through normal work, a blocker, a rejected result, a
long sprint, and return after absence; open business choices have owners and gates.
Numeric usability and response targets are proposed and reviewed here.

### Phase 2 — integrated technical specification and migration design

Depends on Phase 0 baseline and Phase 1 experience. This is the implementation gate.

Deliverables:

- Canonical schema/identity/lifecycle decisions and compatibility mappings.
- Signal, event, mutation, projection, replay, and freshness contracts.
- Scope/delegation/query design, threat model, and negative authorization tests.
- Execution, concurrency, checkpoints, external-effect, and recovery contracts.
- Behavior/TestRun contract, invariant classification, and audit traceability.
- Graphify sensor design and discrepancy promotion workflow.
- API/projection contracts shared by UI, channels, and MCP.
- Migration batches, writer cutover, restore/rollback plan, and test scenarios.

Exit: every audit family maps to planned work and acceptance evidence; disputed
state vocabulary is resolved; no safety-critical permission or recovery question
is silently left to implementation. Review the complete specification together.

This gate also requires S01–S10 from the system-wide contracts: goal evaluation,
control precedence, lifecycle dimensions, observation coverage, graph-outage
operation, authority root, knowledge admission, fleet resources, external
commitments, and migration compatibility. Define C01 combined-failure outcomes
and numeric bounds before implementation. These are initial execution requirements,
not work postponed until autonomous learning or final reliability qualification.

### Phase 3 — executable graph foundation and trusted evidence

Depends on approved Phase 2. Begin in disposable Neo4j fixtures.

Deliverables: tested evidence runner; identity and scope constraints; canonical
aliases; provenance and version records; graph bootstrap generation; behavior
inventory; additive foundation mapping for platform, repositories, releases,
services, decisions, and credential exceptions without secret values.

Bootstrap twice, check topology and stable authored identities, test migration
preflight against duplicates, and restore a snapshot into an isolated environment.
New execution evidence may append on rerun; authored topology must not duplicate.

Exit: failure fixtures fail, valid fixtures pass, current evidence identifies the
target generation, and foundation queries explain canonical identities and sources.
Only then apply approved minimal foundation batches and verify live observations.

### Phase 4 — sensing and truthful projections

Depends on Phase 3; build each stream end-to-end rather than all sensors first.

First streams: deployment/process/fleet, work execution evidence, Git/artifacts,
human decisions, and the Graphify source slice. Follow with necessary provider
outcomes and metrics for the chosen product goal.

Deliverables: registered adapters, lineage, source snapshots, mutation attribution,
freshness and conflict rules, sensor monitoring, deduplication/backfill, shadow
projection comparison, and a read-only board showing current evidence.

Exit: for each pilot projection, explain source, transformation, time, and what
would invalidate it. Disconnecting a source produces stale/unknown state visibly.
Graphify can reproduce a bounded discrepancy without claiming runtime certainty.

### Phase 5 — one governed execution loop and usable controls

Depends on Phase 3 and the relevant Phase 4 streams. Select a bounded Flowing
Indian outcome with the user; a staging artifact is a proposed first safe scope.

Deliverables: work and sprint records, permission enforcement, claim/lease,
isolated worktree, invocation/effect receipts, postconditions, progress, review,
Signals with retained acknowledgement/results, and board control/inspection.

Exercise success, rejection/rework, denial, pause/resume, abort, simultaneous
claim, expired worker, crash before/after effect, lost receipt, and changed intent.
Approval of a draft does not automatically authorize production release.

Exit: one complete goal-to-next-action path is visible and controllable by a human.
The same tests prove forbidden actions cannot occur and retries do not duplicate
known effects. Rollback returns to the prior writer safely with evidence retained.

Pass the core C01 combined-failure scenario: delayed observations, duplicate input,
uncertain effect, pause, goal change, revocation, graph outage, and worker restart.
The executor must preserve intent and evidence while enforcing the specified
offline authority limits. Include bounded scheduling and compensation semantics.

### Phase 6 — remote access and team collaboration

Depends on Phase 5 authority/execution behavior; client and UI prototyping starts
earlier. Do not make production remote mutation the first test of authorization.

Deliverables: authenticated scoped graph reads, Delta conversation, Charlie
coordination, durable asynchronous operation references, team membership and
revocation, reconnect/history, protected artifacts, and selected-client trials.

Exit: admin and project-member test identities see only permitted data; Delta
does not elevate project requests. Client disconnect leaves authorized work
running. Revocation prevents further effects. Prompt-injection boundary tests pass.
Demonstrate mobile review and one concrete remote deep-work session.

### Phase 7 — second project, portfolio transition, and unattended sprints

Depends on Phase 5 and the relevant Phase 6 access paths.

Deliverables: Cajon Sensei onboarding to the same contracts, verified project
isolation, agent provisioning/retirement, inter-agent delegation, checkpointed
sprints, resource budgets, policy-backed next-work selection, and return reports.

Apply reviewed archival dispositions after history mapping and dependency checks:
drain work, stop applicable schedules, disable autonomous reactivation, disposition
credentials, preserve hosted services as agreed, and verify restoration procedure.

Exit: both products advance a defined goal with evidence; archived products do
not consume autonomous attention. Start unattended trials at short duration, then
overnight and multi-day periods. Escalation and blocked behavior are demonstrated.

### Phase 8 — measured healing, learning, and self-modification

Depends on trusted sensing, permissions, execution, and tests from Phases 3–7.
Basic failure handling ships earlier; this phase expands autonomous adaptation.

Deliverables: invariant repair with independent recheck, bounded incidents,
dream usefulness evidence, correct atom attribution, workstream split/merge/fallback,
proposal-to-reviewed-protocol promotion, and retention based on measured value.

Exit: deliberate failures are repaired within permission or escalated; inferred
knowledge remains distinguishable; usefulness is measured; adaptive work conserves
budget and scope. Irreversible cleanup requires its own explicit disposition.

### Phase 9 — reliability qualification and operational handoff

Depends on all release-critical obligations above. Documentation and reliability
work occur throughout; this is their final qualification rather than first work.

Deliverables: restore drills, resource/cost monitoring, provider and model outage
handling, backpressure, credential expiry, audit retention, emergency access,
operator runbooks, full architecture reconciliation, and unattended soak results.

Run progressively longer real trials, targeting the desired 30-day absence.
Accelerated fixtures test clock-dependent transitions but do not substitute for
actual unattended operation. Report achieved duration honestly.

Exit: measurable progress and failures are explained; alert delivery, safe stop,
restore, and resume are demonstrated; remaining exceptions have owners and bounds.
Retire old execution paths only after compatibility and rollback obligations pass.

## 13. Parallel work and critical path

```text
P0 baseline ───────────┐
P1 UX + mandates ──────┴→ P2 integrated design review
                          → P3 graph/evidence foundation
                          → P4 first sensors + read-only board
                          → P5 one governed action + board controls
                          → P6 remote/team access
                          → P7 second project + unattended sprints
                          → P8 measured adaptation
                          → P9 reliability qualification
```

Parallelize UX design with read-only inventory; Graphify research with source
inventory; policy/threat modeling with graph contracts; UI prototypes with fixture
projection design; later independent sensor adapters with a frozen envelope.
Security, tests, documentation, and runtime recovery accompany every phase.

Do not require full ecosystem cleanup or all source extraction before the first
useful UI. Do not postpone access enforcement or evidence correctness until the
remote gateway exists. Keep one integrated review of contract changes so separate
workstreams cannot invent incompatible notions of completion, identity, or scope.

## 14. Audit disposition and phase coverage

Historical section numbers refer to the live audit. Every row requires delta2
applicability evidence before implementation claims. Initial revalidation is recorded
in the live baseline as B01–B10; remaining coverage is pending.

| ID | Audit finding | Main delivery phases | Proof required |
|---|---|---|---|
| A01 | Split project identities (§§2,11–13) | 0,2,3,7 | Canonical resolution preserves history and scope |
| A02 | Contradictory lifecycle and progress (§§7,11,17) | 2,4,7 | Intent, liveness, and freshness remain distinct |
| A03 | Missing execution causality (§§12–14) | 3,5 | Goal through receipt and next action is traversable |
| A04 | Unowned/unresolved proposals (§§12,18) | 5,7,8 | Owner, gate, result, and escalation exist |
| A05 | Capability without authority (§§8,18,21) | 2,5,6 | Denial/delegation/isolation tests prevent effects and leaks |
| A06 | Protocol generation and scheduler drift (§§41,49B) | 0,3,4 | Exact source/atom generation linked to current runs |
| A07 | Weak traces and Hebbian evidence (§3) | 3,5,8 | Actual execution and benefit attributable without double count |
| A08 | Healing without resolution (§§4,26,37) | 5,8 | Independent postcondition or explicit escalation |
| A09 | Unmeasured dream usefulness (§§4,26–27,49F) | 8 | Later use/validation measured; inference retains status |
| A10 | Stale/fragmented tests (§§29–34) | 2,3,9 | Tested runner and current target-specific evidence |
| A11 | Schema and meta-test gaps (§31) | 0,2,3 | Deployed constraints and complete scoped test population |
| A12 | Stream/metabolism gaps (§§22–25) | 0,2,4 | Every critical source has consumer, freshness, and feedback |
| A13 | Partial runtime/configuration map (§§16–17) | 0,3,4,9 | Release/process/configuration observations agree or conflict visibly |
| A14 | Mixed claim origins (§§35,43,50) | 2,3,4 | Provenance and uncertainty survive projections and summaries |
| A15 | Telemetry and orphan retention (§§5–6,27) | 2,7,8,9 | Archive/restore preserves required history and evidence |
| A16 | Disconnected source reality (§§45–49) | 0,2,4 | Versioned Graphify findings reproducible within measured coverage |
| A17 | Incomplete human loop (§§19,28,32) | 1,5,6,7 | Board/chat/MCP decisions and execution form one auditable workflow |

Expand each family into atomic findings during Phase 0. Disposition vocabulary:
confirmed-current, partially-applicable, resolved-with-evidence, legacy-only,
unknown; later implementation status is separate. Any deferral names impact,
compensating measure, owner, and review trigger. None disappears silently.

## 15. Migration and release discipline

For each batch: preflight → snapshot/restore check → fixture rehearsal → additive
bootstrap → shadow comparison → bounded writer cutover → verification → observation.
Record source revision, schema/bootstrap generation, operator, target environment,
affected identities, compatibility readers/writers, and evidence.

Avoid two independent writers controlling the same state. If an old writer must
coexist, define its permitted fields, event IDs, compatibility adapter, and conflict
behavior. During cutover fence or drain it before the new authority starts.
Rollback needs to account for events produced since migration; database restore
alone cannot reverse an external effect. Preserve receipts and reconcile effects.

Do not combine foundation mapping, project archival, public remote access, and
autonomy expansion in one release. Each has different verification and recovery.
Historical graph data and dirty repository work must survive migrations.

## 16. Required specification package and completion rules

Author these supporting documents during Phases 0–2 under architecture/upgrade/:

| Document | Contents |
|---|---|
| baseline-and-findings.md | Current evidence, atomic audit findings, writer inventory, uncertainty |
| experience-and-wireframes.md | U01–U16 flows, screens, errors, attention modes, measurable UX criteria |
| portfolio-and-mandates.md | Product goals, owners, archival dispositions, unattended authority |
| graph-and-state-contract.md | Identities, schema, transitions, aliases, time, evidence, compatibility |
| sensing-and-source-contract.md | Full stream registry, Graphify, transformations, freshness, replay |
| execution-and-agents.md | Work lifecycle, sprint, claims, delegation, concurrency, recovery |
| access-and-threat-model.md | Scopes, principals, graph reads, enforcement, injection and leakage tests |
| interfaces-and-mcp.md | Shared projections, conversations, auth research, compatibility, reconnect |
| tests-and-learning.md | Behavior map, TestRun, invariants, healing, dreaming, retention |
| migration-and-operations.md | Batches, rollout, rollback, restore, monitoring, support, soak trials |
| [system-contracts.md](upgrade/system-contracts.md) | S01–S10 cross-component obligations and C01 combined-failure scenario; drafted |

Every executable behavior specification includes: requirement IDs, owner, authority,
inputs/freshness, preconditions, graph transition, allowed I/O, postcondition,
evidence, error/unknown behavior, retry/timeout, tests, migration, and rollback.
Implementation WorkItems are authored in Git and later promoted to Mycelium through
the reviewed path. During planning, do not seed live work or change schedules.

Program acceptance requires U01–U16, A01–A17, S01–S10, and C01 to have current evidence or explicit
reviewed exceptions; both projects have real goals and complete execution paths;
scoped remote users can inspect and steer; archived work stays inactive; health,
progress, permission, and learning claims have provenance and verification.

## 17. Immediate next work

Proceed with Phase 0 read-only investigation and Phase 1 scenario specification in
parallel. First establish delta2 endpoint/release and inspect its writer/scheduler
chain; then trace a Flowing Indian signal through existing evidence. Draft the
daily home, attention queue, and execution inspector flows from that concrete path.
Use the findings to complete supporting contracts, then review Phase 2 as a whole.

Include S01–S10 in this investigation: identify actual outcome evaluators, competing
controllers, archive/service dependencies, observation coverage, outage behavior,
privileged writers, memory admission paths, capacity allocation, external commitment
points, and version compatibility. Record unverified behavior as unknown.
