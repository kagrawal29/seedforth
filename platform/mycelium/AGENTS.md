# Mycelium platform context

This is the Mycelium runtime inside the SeedForth platform repository. The
canonical repository and architecture are documented at the SeedForth root:

- [`SEEDFORTH-PLATFORM-PLAN.md`](../../SEEDFORTH-PLATFORM-PLAN.md)
- [`architecture/system-overview.md`](../../architecture/system-overview.md)
- [`architecture/state-and-sync.md`](../../architecture/state-and-sync.md)
- [`MIGRATION.md`](MIGRATION.md)

Mycelium is the graph-native control plane. Neo4j on the SeedForth server is
the live runtime state; Cypher under `graph/` is the versioned behavior and
knowledge source. Files and scripts are I/O adapters, not a second source of
truth.

## Runtime authority

The current live graph is the `mycelium-neo4j` container on the new SeedForth
server (`185.192.96.100`, Bolt `bolt://185.192.96.100:7687`). Credentials are
provided at runtime through environment variables or an external secret
store. They must never be committed or embedded in release binaries.

Use the root reconciliation command for read-only checks:

```bash
python3 ../../operations/reconcile.py --server root@185.192.96.100 --graph root@185.192.96.100
```

The graph is operationally authoritative, but source-controlled Cypher and
the platform repository are the change authority. Graph mutations go through
reviewed, idempotent protocols and an explicit deployment step.

## CLI boundary

The active Go CLI lives in `cmd/mycelium`. It provides read-only native
commands and dispatches write/orchestration commands to the contributor
toolchain. It uses `MYCELIUM_*` environment variables. `MAVERICK_*` variables
are accepted only as temporary compatibility aliases.

```bash
cd cmd/mycelium
go test ./...
```

## Safety rules

- Never commit credentials, local graph state, generated heartbeat state, or runtime logs.
- Use `MERGE`, explicit scopes, and idempotent protocols for graph changes.
- Do not use Pulse, FalkorDB, Maverick, or Tetrahedron deployment paths as active SeedForth infrastructure; historical files are retained only for migration/reference work.
- Before changing graph behavior, inspect the relevant protocol, schema, tests, and the root architecture documents.
