# SeedForth Repository Topology

**Status:** Canonical target architecture  
**Last reviewed:** 2026-09-06

## Target structure

```text
SeedForth workspace
├── seedforth/                      one platform repository
│   ├── architecture/
│   ├── mycelium/
│   ├── delta/
│   ├── deployment/
│   ├── operations/
│   ├── registry/
│   └── integration-tests/
├── flowing-indian/                 independent product repository
├── seedforthing/                   independent product repository
├── solveOS/                        independent product repository
├── ember/                          independent product repository
├── audioworld/                     independent product repository
└── tetrahedron/                    separate historical/reference repository
```

## Repository roles

| Repository | Role | Target state |
|---|---|---|
| `seedforth` | Mycelium, Delta, deployment, operations, contracts | Canonical platform source |
| Product repositories | Application/product source | Remain independent |
| `seedforth` workspace | Local registry and coordination | Temporary migration workspace or lightweight registry |
| `tetrahedron` | Former orchestration/infrastructure system | Reference-only |

## Important distinction

The platform repository is not the live graph and is not the server filesystem.

```text
Platform Git repository
  → reviewed deployment
  → server checkout
  → running Delta/services
  → runtime observations
  → Mycelium graph
```

The live Neo4j graph is not committed into Git. It is backed up, exported, versioned by schema/bootstrap metadata, and reconciled against authored definitions.

## Migration constraints

- Preserve product repository ownership and independent release history.
- Preserve Mycelium and Delta history where practical.
- Do not use Git submodules as the primary integration mechanism.
- Do not move runtime logs, inboxes, outboxes, credentials, or agent home directories into Git.
- Do not delete the old repositories until the platform deployment and rollback gates pass.
