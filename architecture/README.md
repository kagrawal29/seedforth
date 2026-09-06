# SeedForth Architecture Canon

This directory contains the current architecture contract for SeedForth. The governing migration plan is [SEEDFORTH-PLATFORM-PLAN.md](../SEEDFORTH-PLATFORM-PLAN.md).

Documents in this directory are classified as:

- **Canonical:** intended system contract.
- **Operational:** current runtime/deployment description.
- **Historical:** retained for context, not active design.
- **Proposed:** planned behavior not yet deployed.

Current status: the target architecture is proposed; the baseline inventory is observational and was collected on 2026-09-06.

## Reading order

1. [system-overview.md](system-overview.md)
2. [repository-topology.md](repository-topology.md)
3. [runtime-topology.md](runtime-topology.md)
4. [state-and-sync.md](state-and-sync.md)
5. [baseline-2026-09-06.md](baseline-2026-09-06.md)

No document in this directory contains credentials. Runtime secrets belong in the server secret store and documented operational runbooks, never in Git.
