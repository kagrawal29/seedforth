# Archive: v1 pre-migration scripts

These scripts were the external orchestration layer for mycelium's heartbeat and immune cycle. As of 2026-04-17, they are deprecated — their logic now lives inside Neo4j as `Protocol` nodes, run via `apoc.periodic.repeat`.

## What replaced them

- `heartbeat-loop.sh` → `apoc.periodic.repeat('mycelium-heartbeat', ...)` scheduling `protocol-heartbeat-scheduled` which calls `protocol-heartbeat-core`. Run via `mycelium start`.
- `immune-cycle.sh` / `immune-cycle.py` → `protocol-immune-cycle` with closed heal loop (detect → heal via apoc.cypher.run → recheck → propose → score). Invoked from heartbeat every 10 beats.

## Why archived, not deleted

- Reference for debugging or rollback
- Historical context for how the system worked before graph-native autonomy
- The bash/python versions contain useful logic (fd3 stdin fix, APOC dynamic evaluation) that informed the cypher rewrite

## To restore

1. `git mv archive/v1-pre-migration/graph-runner/*.sh graph/runner/`
2. `mycelium stop` (cancel the APOC schedule)
3. `bash graph/runner/heartbeat-loop.sh &` (old behaviour)

Not recommended — the cypher-native version fixes the open heal loop bug and removes the external-process failure mode.
