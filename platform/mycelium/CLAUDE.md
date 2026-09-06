# Mycelium — SeedForth platform component

Work in this directory as part of the SeedForth platform repository, not as a
standalone team distribution. Read the root `CLAUDE.md` and
`SEEDFORTH-PLATFORM-PLAN.md` first.

Mycelium owns the graph-native control plane: protocols, graph knowledge,
graph tooling, and the Neo4j runtime. Delta owns Discord/project interaction
and execution supervision. Product repositories remain independent.

The live graph is Neo4j in `mycelium-neo4j` on `185.192.96.100`. The server
checkout and graph are inspected by `../../operations/reconcile.py`; do not
assume local files, GitHub, the server checkout, and graph state are synced.

Changes to graph behavior belong in versioned Cypher/protocols, with tests and
an explicit promotion record. Credentials are runtime-only. Historical
Maverick/Pulse/FalkorDB material may remain in this imported snapshot while it
is classified, but it is not an active dependency.

Before ending a work session, update the relevant migration/architecture
record and leave the working tree and test status clear.
