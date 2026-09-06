# SeedForth Platform

This directory is the future home of the unified SeedForth platform source.

```text
platform/
├── mycelium/             graph definitions, schemas, CLI, tests
├── delta/                channels, routing, agents, provisioning
├── deployment/           server services and deployment manifests
├── operations/           reconciliation, backups, recovery
├── contracts/            interfaces between platform components
└── integration-tests/    cross-component verification
```

The platform repository is the existing `kagrawal29/seedforth` repository. Product source remains in its own repositories and is referenced through `registry/repositories.json`.

## Migration rule

The current `delta/` and `tetrahedron/projects/mycelium/` directories are source checkouts with independent Git histories. They must be imported into this directory only after:

1. their working trees are snapshotted;
2. their local and GitHub branches are recorded;
3. secrets and runtime files are excluded;
4. history preservation is verified;
5. platform integration tests pass.

No runtime server path changes until the imported platform checkout is reproducible and the rollback path is tested.
