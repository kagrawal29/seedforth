# SeedForth Architecture Canon

This directory contains the current architecture contract for SeedForth. The governing migration plan is [SEEDFORTH-PLATFORM-PLAN.md](../SEEDFORTH-PLATFORM-PLAN.md).

Documents in this directory are classified as:

- **Canonical:** intended system contract.
- **Operational:** current runtime/deployment description.
- **Historical:** retained for context, not active design.
- **Proposed:** planned behavior not yet deployed.

Current status: the platform architecture is deployed on `delta2`; the baseline
inventory remains observational evidence captured on 2026-09-06 and is
superseded by the reconciliation ledger when values differ.

## Reading order

1. [system-overview.md](system-overview.md)
2. [repository-topology.md](repository-topology.md)
3. [runtime-topology.md](runtime-topology.md)
4. [state-and-sync.md](state-and-sync.md)
5. [baseline-2026-09-06.md](baseline-2026-09-06.md)
6. [product-repository-sync-runbook.md](product-repository-sync-runbook.md)

No document in this directory contains credentials. Runtime secrets belong in the server secret store and documented operational runbooks, never in Git.
