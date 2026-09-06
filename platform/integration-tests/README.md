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

The current release has the component gates but not all cross-component gates;
the server cutover remains disabled until these checks are implemented and
run against disposable infrastructure.
