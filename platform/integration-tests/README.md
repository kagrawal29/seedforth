# Platform integration gates

The integration suite verifies boundaries rather than re-running every
product test. A release is eligible for cutover only when these checks pass:

1. `control-envelope.schema.json` accepts valid Delta/Mycelium envelopes and
   rejects missing project scope or unknown message kinds.
2. Mycelium’s control-model Cypher parses and is idempotent on a disposable
   Neo4j database.
3. Delta can emit a `progress` envelope and Mycelium can record it against one
   `WorkItem`/`ExecutionSession` without duplicate state on replay.
4. A server reconciliation identifies a deliberately introduced SHA/process/
   graph mismatch as `drifted` or `conflicting`.
5. The release manifest records all component SHAs and the graph bootstrap
   version before service activation.

The repository includes a dependency-light boundary suite at
`test_platform_boundaries.py`; run it with `pytest platform/integration-tests`.
The real Neo4j bootstrap/replay gate can be run against a disposable container
with `bash platform/integration-tests/run-disposable.sh`. It exits with status
2 when Docker is unavailable and never uses the production graph endpoint.
The latest evidence is recorded in
[`verification-2026-09-06.md`](verification-2026-09-06.md).
The current production release passed the schema/bootstrap, active Delta,
graph-health, fleet-reconciliation, and rollback checks and is deployed on
`delta2`. The disposable replay and deliberate-mismatch harnesses remain
automation backlog for subsequent releases; they are not silently treated as
passed by the current release manifest.
