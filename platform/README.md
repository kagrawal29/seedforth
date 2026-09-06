# SeedForth Platform

This directory is the unified SeedForth platform source.

```text
platform/
├── mycelium/             graph definitions, schemas, CLI, tests
├── delta/                channels, routing, agents, provisioning
├── deployment/           server services and deployment manifests
├── operations/           reconciliation, backups, recovery
├── contracts/            interfaces between platform components
└── integration-tests/    cross-component verification
```

The platform repository is the existing `kagraw29/seedforth` repository. Its
tested runtime release is pinned independently from GitHub `main` until a new
release passes the deployment gates. Product source remains in its own
repositories and is referenced through `registry/repositories.json`.

The initial Mycelium import is documented in [mycelium/MIGRATION.md](mycelium/MIGRATION.md). It is now the reviewed production platform source; its deployed release and remaining source-checkout drift are tracked in [the reconciliation ledger](../architecture/repository-reconciliation-2026-09-06.md).

## Migration rule

The historical `delta/` and `tetrahedron/projects/mycelium/` directories remain independent source/reference checkouts. The platform import was completed after:

1. their working trees are snapshotted;
2. their local and GitHub branches are recorded;
3. secrets and runtime files are excluded;
4. history preservation is verified;
5. platform integration tests pass.

The runtime now uses immutable releases under `/opt/seedforth/current`; `/opt/delta` remains intact as the rollback target. Future changes follow the same release-and-rollback gates.
