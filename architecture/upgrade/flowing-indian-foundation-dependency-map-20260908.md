# Flowing Indian governed-delivery dependency map

Date: 2026-09-08
Program: #1 and #17

## Target outcome

Flowing Indian work can be requested from Delta Discord or Charlie WhatsApp,
planned with coherent context, paused for human-owned decisions, executed by a
bounded agent from a verified repository revision, and delivered with GitHub,
CI, review, deployment, and Mycelium evidence.

## Dependency layers

### Layer 0 — authority and identity

- #2 graph-resident agent identity and operating context
- #7 Flowing Indian GitHub access and three-way repository sync
- #11 repository fleet registry and reconciliation

Required before autonomous implementation. Discovery may inspect while the
repository relationship is being reconciled, but must not mutate an unknown or
divergent checkout.

### Layer 1 — context and intake

- #3 GitHub ingestion, repository graph, and semantic indexing
- #4 phone-first intake, alignment, and delivery protocol
- #22 explicit human-input gates

Required for coherent planning through either channel. Read-only discovery can
start with partial indexing if the partial/stale state is visible.

### Layer 2 — deterministic control

- #23 deterministic delivery state machine
- #24 risk-based approval authority
- #25 execution readiness and test-first delivery contract
- #26 GitHub readiness and approval metadata at agent admission

Required before implementation is admitted autonomously. These define legal
states, allowed actors, readiness, authority, and refusal behavior.

### Layer 3 — engineering delivery

- #6 PR, CI, evidence, and human review contract
- isolated worktree and verified revision execution
- repository-specific tests, deployment checks, and release evidence

Required before claiming a product result is delivered.

## Flowing Indian product dependency graph

```text
#5 Workstream alignment
  ├── #13 Order discovery audit
  │     └── #14 Durable order state and reconciliation
  │           ├── #15 Buyer/team notifications
  │           └── #16 Order history and operations
  ├── #18 Course/content/assets audit
  │     └── #19 Authenticated access and learner progress
  └── #20 Catalog/product truth audit
        └── #21 Product pages and bundle conversion
```

Cross-stream constraints:

- #14 supplies the order/payment contract needed by #19 and #21.
- #18 supplies the course/content truth needed by #19.
- #20 supplies product/SKU/content truth needed by #21.
- #7 and #26 gate all implementation work across the three streams.
- #15 and #16 remain separate from #14 so notification and operations failures
  cannot make payment persistence ambiguous.

## Parallel work allowed

- platform discovery and service verification
- GitHub/Mycelium indexing and repository reconciliation
- #13, #18, and #20 read-only product audits
- drafting specifications, decision packets, and test plans
- testing channel routing without creating implementation work

## Explicit no-go conditions

- repository branch, SHA, dirty state, or deployment relationship is unknown
- issue lacks outcome, scope, acceptance criteria, or owner/agent
- human-owned product context is missing
- required specification or test plan is absent
- approval authority is undefined for the requested action
- graph and GitHub state disagree at admission time
- production or customer-facing effects lack explicit approval

## Readiness milestone

The first real user request should begin as discovery only. The first autonomous
implementation begins only after Layers 0–3 are verified for the selected
repository and the relevant product issue reaches `Approved for execution`.
