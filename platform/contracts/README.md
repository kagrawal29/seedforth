# SeedForth platform contracts

These contracts define the boundary between Delta, Mycelium, and independent
product repositories. They are deliberately small: transport payloads carry
observations and requests, while durable state is represented in Mycelium.

## Canonical control model

```text
Project
└── Workstream             bounded outcome / area of work
    └── WorkItem            one actionable unit
        └── ExecutionSession  one bounded attempt with evidence

SubAgent ──ASSIGNED_TO──> WorkItem
AgentProcess ──BACKS──> SubAgent
AgentProcess ──RUNS_ON──> Server

Signal ──REQUESTS──> DecisionRequest ──RESOLVED_BY──> Decision
ExecutionSession ──PRODUCES──> ActivityLog / ProgressEvent / CodeChange
CodeChange ──TOUCHES──> Repository
```

The distinction matters:

- a `SubAgent` is an identity and capability set;
- an `AgentProcess` is a currently running supervised process;
- an `ExecutionSession` is a bounded attempt, regardless of process restarts;
- a `WorkItem` is durable intent and remains when an attempt fails;
- a `Signal` is an observation or request, not a command to mutate state.

## State transitions

`WorkItem.status` is one of `proposed`, `ready`, `claimed`, `in_progress`,
`blocked`, `review`, `done`, or `cancelled`.

`ExecutionSession.status` is one of `queued`, `running`, `succeeded`,
`failed`, `aborted`, or `expired`.

`AgentProcess.status` is one of `starting`, `ready`, `degraded`, `stopped`,
or `unknown`.

Every transition records `observed_at`, `source`, and an actor/process id.
Delta may report process observations and deliver requests. Mycelium owns the
durable transition and decision record. Git owns the code and diff itself.

## Envelope rules

Transport messages must include:

```json
{
  "schema": "seedforth.control.v1",
  "message_id": "msg-<unique>",
  "kind": "signal|decision_request|progress|execution_result",
  "project": "<project-id>",
  "source": "delta|mycelium|agent|provider",
  "occurred_at": "<RFC3339 timestamp>",
  "correlation_id": "<work-item-or-session-id>",
  "payload": {}
}
```

Consumers must be idempotent on `message_id`, reject missing project scope,
and preserve the original payload as evidence before deriving state.
