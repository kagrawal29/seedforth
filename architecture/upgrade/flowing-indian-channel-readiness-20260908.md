# Flowing Indian channel-to-delivery readiness

Date: 2026-09-08
Sprint objective: use Flowing Indian work through Delta in Discord and Charlie
in WhatsApp, with the system governing planning, execution, review, and delivery.

## Confirmed server registration

- Delta registry contains Flowing Indian as an active product project.
- Discord project channel is registered: `1539714100832112660`.
- GitHub repository is registered: `kartiksahu/flowing-indian-website`.
- Flowing Indian project agent is configured on the server with runtime `opencode`.
- WhatsApp routing contains multiple Flowing Indian chats, including a chat
  with a recorded agent session.
- Delta Discord service is active.
- WhatsApp webhook service is active.
- SeedForth control gateway and protected worker services are active.

## Runtime readiness observed

The governed-loop units are `oneshot` services triggered by active systemd
timers, so they are normally inactive between runs. The latest observed runs
completed successfully:

- Flowing Indian autonomous executor: ran and returned `idle` because no graph
  WorkItem was ready.
- conversation processor: active timer run, no queued direction delivered.
- Delta event and acknowledgement ingest: successful, no pending events.
- Flowing Indian graphify producer: successful, revision `2d07670`, 3 documents.
- graphify sensor: successful, 51 Flowing Indian facts collected.
- runtime and service sensors: successful.
- Mycelium heartbeat: successful.

The runtime foundation is therefore operating on schedule, but the complete
channel-to-GitHub-to-graph-to-execution path is not yet proven with a real user
request. A message reaching the project agent is not sufficient evidence that an
issue was planned, gated, executed from a verified revision, reviewed, and
delivered.

## Sprint acceptance marker

From either the Flowing Indian Discord channel or Charlie WhatsApp:

1. User states a desired outcome.
2. System identifies the project, agent identities, GitHub repository, and
   current context.
3. Agent performs bounded discovery and produces a structured proposal.
4. Missing human-owned context becomes a focused decision request.
5. Accepted work is represented by GitHub issues and Project metadata.
6. Only execution-ready work can enter a bounded Delta attempt.
7. Branch, PR, CI, review, and deployment evidence are recorded.
8. User receives progress, blockers, approval requests, and final report in the
   originating channel.

## Required verification

- channel routing and identity scope
- GitHub issue/project metadata ingestion
- Mycelium context and provenance
- human-input and approval gates
- repository revision reconciliation
- bounded work claim and execution
- PR/CI/review evidence
- WhatsApp and Discord progress/final delivery
- recovery after interruption or duplicate message
