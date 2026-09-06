# Delta legacy boundary

**Status:** Operational boundary

The supported SeedForth runtime uses:

- `tools/neo4j_helper.py` for authenticated Neo4j HTTP access;
- `tools/graph-runner.py` for graph-resident protocol execution;
- `seedforth-mycelium-heartbeat.service` for heartbeat scheduling;
- `seedforth-delta.service` for the Delta process.

The following imported files are retained for provenance or manual migration
only and are not supported service entrypoints:

- `deploy/heartbeat/run-heartbeat.sh`
- `deploy/heartbeat/run-dream-cycle.sh`
- `deploy/heartbeat/run-deep-cycle.sh`
- `deploy/heartbeat/run-long-cycle.sh`
- `tools/fix-invariants.py`
- `tools/run-invariants.py`
- `tools/nl-query.py`
- `tools/graph-ui/server.py`'s Docker fallback
- `deploy/provision-contabo.sh`

These legacy paths may contain historical `cypher-shell` examples. They must
not be scheduled, copied into a production unit, or used with real credentials.
Any future reactivation must first replace command-line password handling with
the shared HTTP helper and add a release-gate test.

This boundary is separate from the active graph program. Graph behavior belongs
in Mycelium protocols; only external I/O belongs in scripts.
