# Upgrade delivery backlog, migration, and operations

Status: active delivery plan under delegated implementation/deployment authority.
See execution-ledger.md for tested and deployed scope; unimplemented contracts remain targets.
Parent: [program phases](../seedforth-upgrade-plan.md).

## Delivery work packages

Each package becomes governed graph WorkItems. Component owners are responsibilities,
not assignments to already authorized autonomous agents.

| ID / phase | Package and owner | Dependencies | Exit evidence |
|---|---|---|---|
| W00 / P0 | Current baseline, platform operations | Approved read access | Target/release, B findings, unknowns, critical writer/stream census |
| W01 / P0 | Audit reconciliation, graph engineering | W00 | Atomic A findings, applicability and source/runtime evidence |
| W02 / P1 | UX flows and wireframes, product design | Initial W00 | U01–U16 reviewable, including failure and absence |
| W03 / P1 | Portfolio/mandates, owner + platform | W00 | Product lifecycle dimensions, proposed archival, grant worksheet |
| W04 / P2 | Canonical graph and behavior contracts | W01–W03 | D01–D15 and S01–S10 reviewed with compatibility decisions |
| W05 / P2 | Threat model/MCP qualification design | W02,W04 draft | Isolation tests, protocol/client strategy, authority root |
| W06 / P2 | Migration and verification design | W01,W04,W05 | Batches, tests, rollback, outstanding human choices |
| W07 / P3 | Trusted runner and fixture evidence | Integrated review | Known failures fail, target/source/generation recorded |
| W08 / P3 | Identity/scope/foundation migration | W07 | Duplicate preflight, alias map, twice-run bootstrap, restore |
| W09 / P4 | Runtime and work sensing | W08 | Freshness/cursor/coverage and lineage through projections |
| W10 / P4 | Graphify source sensor slice | W08, experiment recovery | Pinned artifact/version, bounded reproducible discrepancies |
| W11 / P4 | Read-only board, interface team | W02,W09 projections | Useful scoped state, evidence links, stale/error UX |
| W12 / P5 | Capability broker and protected policies | W05,W08 | Grant/denial/revocation and hostile-input tests |
| W13 / P5 | Executor/claims/receipts/review | W07,W09,W12 | Complete pilot path, no false progress or duplicate effect |
| W14 / P5 | Board control/timeline/diff | W11,W13 | Versioned controls, review binding, C01 core |
| W15 / P6 | MCP and teammate access | W12–W14 | Scoped graph/conversation, reconnect, client trials |
| W16 / P7 | Second product and agent lifecycle | W13,W15 | Both projects, isolation, provisioning, bounded delegation |
| W17 / P7 | Portfolio archival batches | W03,W08,W16 dependencies checked | Drained work, retained services, no automatic reactivation |
| W18 / P7 | Bounded unattended operation | W14–W16 | Verified outcomes, budgets, fallbacks, return reports |
| W19 / P8 | Healing and incident closure | W07,W12,W13 | Independent postcondition and bounded escalation |
| W20 / P8 | Learning, knowledge correction, self-modification | W09,W13,W19 | Provenance/usefulness; reviewed promotion; budget conservation |
| W21 / P9 | Reliability qualification | Release-critical packages | Restore/outage drills, soak duration, operational handoff |

No elapsed-time estimates are claimed before critical source and privilege scope
is known. Estimate package sizes after review, tracking confidence and dependencies.
Parallelize UX with audit, source sensing with runtime adapters, and interface work
with fixtures once contracts stabilize. Coordinate all vocabulary changes centrally.

## Migration batches

M0 capture source/configuration inventory, graph snapshot, and isolated restore.
M1 add evidence/identity/schema contracts and compatibility readers; no new autonomy.
M2 map verified canonical project/agent/runtime identities with preserved aliases.
M3 introduce streams and shadow projections, comparing divergence without effects.
M4 fence legacy writers for one work path; activate broker/executor in staging.
M5 bounded live pilot and read/control board under explicit grants.
M6 add remote users and second product after authority tests.
M7 apply individually reviewed portfolio archival dispositions.
M8 expand safe adaptation and retire obsolete machinery after observation.

Every batch declares target, source and graph generation, scope, preflight, allowed
mutations, backup, rollback, compatibility, verification, observation window, and
operator. Typed cross-project bridge rules remain enforced during migration.

Existing legacy worker launch is not repaired independently: migrate its credential,
argument schema, workspace isolation, timeout, claims, result semantics, and grants
together. Otherwise a reliability fix would activate unreviewed external effects.

## Writer cutover and replay

Enumerate writer principals and owned fields. Drain or fence the old owner before
the new reducer takes authority. Compatibility readers may coexist; two competing
authoritative writers may not. Pin versions for attempts while honoring current
revocation at dispatch. Old events must declare origin schema and replay context.

Shadow and backfill modes have no external-effect grants. Rollback preserves
post-cutover receipts and reconciles committed external outcomes before restoring
planning state. A database restore cannot unsend messages or undo expenditure.

## Operational modes and recovery

Healthy: admit eligible work. Degraded: show uncertainty and stop actions requiring
unavailable authority/evidence. Recovering: replay receipts, reconcile leases and
provider outcomes, validate projections, then resume explicit permitted work.
Emergency stop remains independent of model availability; graph outage handling
follows S05 with explicit offline exposure bounds.

Proposed initial service targets for review: connected request acknowledgement
p95 ≤2 seconds; event projection p95 ≤5 seconds; pause acknowledgement ≤10 seconds;
fleet stale after three missed collections. These are engineering targets pending
measurement, not production guarantees. Set RPO/RTO after inventorying durable
receipts, snapshot/WAL capabilities, and restore drills; do not invent zero loss.

Monitor ingestion lag, failed receipts, queue age, oldest decision, lease expiry,
effect uncertainty, cost/reservations, provider quota, disk/memory, credential expiry,
and external alert delivery. Use bounded logs and redact secrets before persistence.

## Required pre-build evidence work remaining

- Complete all user/system cron and application schedule inventory.
- Trace fleet ingest and progress reduction from deployed source and live atoms.
- Verify six nonpilot agent callers/outputs before their archival dispositions.
- Recover exact Graphify experiment artifacts/configuration.
- Inspect actual grants/database privileges and secret-store boundaries.
- Inspect current backups, restoration, platform deployment and network exposure.
- Identify any external customer obligations or services behind archive candidates.

These are targeted baseline tasks with deliverables, performed alongside implementation.
Unknowns do not prevent review of the proposed architecture, but gate affected
implementation and live promotion.

## Review and build entry

Review D01–D15, the UX journeys, scope and unattended defaults, archive dimensions,
and phase order. Resolve necessary business parameters only before issuing actual
mandates. Record amendments and decision owners in the package.

Build entry requires accepted contracts, authority-root design, representative
fixtures, affected writer inventory, recoverable migration batches, and an explicit
implementation instruction. Completion requires current acceptance evidence across
the requirement matrix, not merely authored nodes or passing historical test fields.
