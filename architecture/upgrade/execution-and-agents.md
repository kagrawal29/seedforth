# Execution, agents, and useful autonomy

Status: proposed. Covers A03–A09, A17, U03–U08, U10–U12, S01–S02, S05–S09.

## Role and identity model

Charlie manages discussion, alignment, summaries, and decision proposals. Delta
selects eligible work, delegates, coordinates, and recovers under accepted mandates.
Project agents execute bounded tasks. These are responsibilities with explicit
principals, not independent authorities over competing copies of project state.

A SubAgent has durable identity, owner, capabilities, project assignments, and
model selection policy. AgentProcess has observed process state and resource use.
LLM session has context lifetime. ExecutionSession is a task attempt that can outlive
a process or model session. A serving endpoint alone is not evidence of autonomy.

## Eligible work and scheduler

Eligibility requires active work permission, accepted goal/milestone, ready task,
owner, known acceptance criteria, satisfied dependencies, valid grants, fresh
required inputs, available budget, and no applicable hold. Scheduler queries these
conditions through versioned graph behavior. It returns no-work with reason when
none qualify; it does not generate busywork to keep an agent occupied.

Proposed initial concurrency: one executing attempt per product and one independent
platform maintenance slot. Expansion requires measured capacity and isolation.
Reserve recovery/sensing resources; delegate budget reservations down the work tree.
Rate limits and human-decision capacity are dependencies, not reasons to bypass gates.

## Attempt protocol

1. Claim eligible work atomically; record lease, fencing epoch, expected task and
   mandate versions, actor, and plan. A competing claimant receives a conflict.
2. Create an isolated worktree/artifact workspace at a recorded base revision.
3. Build context from scoped, current graph evidence and referenced artifacts.
4. Evaluate each intended effect through the capability boundary; reserve budget.
5. Persist Invocation before dispatch; execute via an approved ExternalAtom adapter.
6. Capture receipt or explicit uncertain outcome, activity, resource consumption,
   and relevant artifacts. Update claim lease only while execution remains valid.
7. Run independent criterion-specific verification. Execution success alone does
   not establish useful progress or acceptance.
8. Enter review or accept under an explicit standing policy; publish ProgressEvent
   only for substantiated contribution. Record blocked/failed outcomes separately.
9. Reconcile goal version and choose next permitted work or stop with reason.

Default pilot lease proposal: 90 seconds with renewal every 30 seconds. Expiry
fences future authoritative writes from that attempt. Reconcile external outcomes
before retry; an expired lease does not undo an already committed provider action.
These timings require capacity tests and are not deployed values.

## Structured external execution

Replace script-plus-arguments strings with reviewed executable ID, release-bound
path, typed argument schema, allowed working directory, permitted destinations,
timeout, credential reference, and receipt contract. Never repair the current bug
by switching to unrestricted shell execution.

Timeout hierarchy: per-tool deadline ≤ attempt deadline ≤ mandate expiry. The
outer process timeout must allow receipt capture/cleanup after child cancellation.
Select action-specific limits; the current 120/300-second mismatch is unacceptable.
Workers return explicit no-work, denied, blocked, failed, uncertain, or succeeded.
Runner exit codes reflect failure while graph records preserve detailed outcomes.

## Controls and collaboration

Start/retry/resume requests require current eligibility. Pause sets a scoped hold
and requests cooperative checkpoint; effectful adapters also check holds before
dispatch. Abort stops the attempt and reports in-flight or committed effects.
Reassignment fences the previous writer; no two active exclusive owners.

Human steering changes accepted goal or plan versions, then reconciles pending
steps. Delta cannot continue a superseded plan merely because its context was
loaded earlier. Agent-to-agent tasks retain originating authority, budgets, and
causation. Limit delegation depth and reject cycles.

Agent onboarding: proposed role → owner-approved scope/budget → isolated identity
and tools → test capability/denial → activate → observe health. Retirement drains
attempts, transfers owned work, revokes grants, stops process, and retains evidence.
Do not grant a new agent administrator access by default.

## Outages and uncertain effects

When graph authority is unavailable, admit no new mutating work. Previously
authorized in-flight actions follow their explicit action-class policy; critical
effects require online checks. Durable restricted receipt buffering is external I/O,
not an alternative work planner. Stop if evidence cannot be preserved.

A provider timeout after request submission is uncertain until reconciled. Query
the provider using its idempotency key or receipt identifier where available. No
blind retry of spending, messaging, publication, or deletion. Compensation is a
new authorized action linked to the old commitment.

## Useful autonomy as upgrade acceptance

Two representative product workflows exercise the common platform. Choose actual
business acceptance parameters at review; use synthetic fixtures for implementation
tests. This selection does not narrow the upgrade to one mission or postpone the
broader audit obligations.

Demonstrate work chosen from accepted direction, executed within authority,
verified, reviewed where required, and followed by a justified next action. Include
blocked and no-work cases. Count autonomous accepted outcomes and human interventions
alongside failures, costs, and time; do not use commit counts as the success metric.

Each pilot proves C01 combined failures, then disconnected overnight and multi-day
execution. A real 30-day trial is a later qualification; simulated time does not
prove actual month-long reliability.
