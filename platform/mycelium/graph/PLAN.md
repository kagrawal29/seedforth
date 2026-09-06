# Mycelium Evolution — Cypher-Native Mutation Gate

This is the active plan for evolving mycelium from "graph with frozen write
path" to "graph that validates its own mutations and witnesses external graph
integrations". The plan lives in the repo because the graph's protocols live
in the repo; a new session should be able to read this file, query the graph,
and pick up exactly where the previous session left off.

## Current state (what's working)

- **Local Neo4j** with APOC at `bolt://localhost:7689` (container
  `mycelium-neo4j-local`). Single source of development truth.
- **Prod + staging Neo4j** on pulse-server at `:7687` / `:7688`. Seeded from
  `graph-state.cypher` on `main` / `develop`. APOC bump for server compose
  committed but not yet applied on the containers.
- **Phase B Merkle**: per-node `leaf_hash` + singleton `Being.root_hash`.
  Idempotent, drift-detecting, round-trip verified byte-identical.
  See `graph/protocols/merkle-properties.cypher`.
- **Skip keys as graph nodes**: `MATCH (sk:SkipKey)` returns the config.
  Adding a new skip key is a single MERGE. merkle-properties reads them
  dynamically. See `graph/protocols/skip-keys-init.cypher`.
- **Heartbeat**: `graph/protocols/heartbeat.cypher` + `graph/runner/heartbeat-loop.sh`.
  Protocol registered as `Protocol {node_id: "protocol-heartbeat"}`.
  Liveness properties in SkipKey, so breathing does not churn `root_hash`.
- **Graph-state export**: `graph/protocols/export-graph-state.cypher` + runner.
  Emits deterministic, label-scoped MERGE statements. Replaces the legacy
  FalkorDB Python script. Committed graph-state.cypher is its output.
- **Chain scaffolding in the graph** (unused so far): 22 Invariants with
  `check_cypher` properties, 158 TestCases with `assertion_cypher`, 36
  Protocols (36 new ones being added this session), 10 legacy Species with
  WitnessSignatures, a Being node as the singleton identity anchor.

## Decisions locked for this evolution

| # | Decision | Choice |
|---|---|---|
| 1 | Execution order | Revised: Phase 0.5 → 1 → 0 → 2 → 6 → 3 → 7 → 8 → 4 → 9 → 5 |
| 2 | Witness signatures | ed25519, quorum = 2 (one small Python sidecar for verify) |
| 3 | Legacy species | Relabel to `:LegacySpecies`, never extend |
| 4 | Plan doc | This file |
| 5 | External graph model | Hybrid: imports start read-only, adoption promotes nodes to core |
| 6 | Namespace | Compound `<source>:<original>` node_id + `:Imported:<Source>` label |
| 7 | Bundle delivery | Git PR |
| 8 | Schema translation | Accept any schema, tag with provenance |

## Phase map

```
0.5  SkipKey nodes + dynamic merkle                       [ DONE this session ]
     └ heartbeat protocol + loop                          [ DONE this session ]
1    run-invariants + run-tests protocols                 [ IN PROGRESS ]
     └ triage the 14 currently-failing TestCases
1.5  invariant scope refactor (core / imports / all)
0    fresh genesis under Phase B algorithm                [ blocked on Phase 1 ]
     └ relabel existing Species to :LegacySpecies
2    species-mint / species-sign / species-canonize
2.5  ed25519 signing sidecar (graph/runner/verify-signature.py)
6    continuous heartbeat via systemd for prod/staging    [ partially done: local runs ]
3    validate-merge write gate
7    Source model + import-external protocol
8    adoption protocol
4    GitHub Actions for internal PR validation
9    GitHub Actions for import PR validation
5    Multi-witness + per-source chains                    [ deferred ]
```

## Phase 0.5 — Skip keys + dynamic Merkle  [DONE]

Source: `graph/protocols/skip-keys-init.cypher` + update to
`graph/protocols/merkle-properties.cypher`.

Seven SkipKey nodes registered, two categories:

- `merkle-output`: leaf_hash, root_hash, root_hash_computed_at, leaf_count
- `liveness`: last_heartbeat, last_heartbeat_at, heartbeat_count

Verified: 15 heartbeats + merkle re-run produced byte-identical root_hash.
Currently stable at `222a59ffb53625326d407280f6995273ecb744e727b77c6ddebd81b237521f9d`
(with the 3 newly-registered Protocol nodes, 7 SkipKey nodes, and updated Being
heartbeat properties).

## Phase 1.6 — true-green baseline  [DONE]

All active runners are green:
- `run-invariants.sh` → 17/17 healthy, 6 deferred
- `run-tests.sh` → 134/134 passing, 24 deferred

Deferral categories (filtered via `enabled = false` + `deferred_reason`):

| Reason | Tests | Invariants | Recovery |
|---|---|---|---|
| `blocked-phase-0` | — | 4 | Requires fresh genesis + witness lifecycle |
| `blocked-write-path` | — | 1 | Once a live write protocol creates CouplingEvents |
| `data-cleanup` | 3 | 1 | Backfill forest aliases, synthetic fixtures, proposed_at |
| `frozen-write-path` | 8 | — | Restores when any write protocol resumes |
| `structural-assertion` | 4 | — | Requires edge-density audit |
| `missing-fixture` | 3 | — | Restore fixtures or delete tests |
| `tdd-coverage-gap` | 3 | — | Write the missing TestCases |
| `test-design-outdated` | 2 | — | NLQ pattern evolved; revisit after Phase 1.8 |

Each deferred test/invariant has a `deferred_note` property explaining the rationale.

Key 1.6 changes:
- 18 invariants renamed `cypher_check` → `check_cypher` (schema reconcile)
- invariant-12 chr() → literal forest alias list
- 8 TestCases migrated `size((n)--())` → `COUNT { (n)--() }`
- 14 TestCases rewritten with clean boolean assertions (was: self-mutating legacy harness queries)
- Both runners updated to prefer local file over Protocol node (edit loop friendly)
- Both runners respect `enabled=false` filter

New SkipKey additions: `enabled`, `deferred_reason`, `deferred_note` (lifecycle), plus `embedding`, `embedding_for_leaf_hash`, `embedding_model` (derived-output, for Phase 1.7).

## Phase 1 — Read-only runners  [DONE in 1.6]

Two protocols being built in parallel:

- `graph/protocols/run-invariants.cypher` — loop Invariant nodes, execute
  `check_cypher` via `apoc.cypher.run`, update `health` + `last_check`.
- `graph/protocols/run-tests.cypher` — loop TestCase nodes, execute
  `assertion_cypher`, compare to `expected`, update `last_result` + `last_run`.

Also triage of the 14 currently-failing TestCases: for each, determine
disposition (fix / retire / stale-schema / bad-cypher / genuine-regression).

## Phase 0 — Fresh genesis  [blocked]

Once Phase 1 results are in and the baseline is known-clean:

```
graph/protocols/genesis-phase-b.cypher
  - relabel existing Species → :LegacySpecies, flag pre_phase_b: true
  - MERGE species-genesis-phase-b with parent_dna = NULL, genesis = true,
    algorithm = "phase-b-v1", manifest_root = current Being.root_hash
  - link Being via :CURRENT_SPECIES edge
```

## Phases 2-9

See the detailed artifacts list in the conversation history for this session.
Will be migrated into this file as each phase lands.

## Running protocols against the local graph

All protocols are files in `graph/protocols/`. Execute against local Neo4j:

```bash
docker exec -i mycelium-neo4j-local cypher-shell \
  -u neo4j -p localtest12 --encryption false \
  < graph/protocols/<name>.cypher
```

Runners in `graph/runner/` wrap this pattern with argument handling,
post-processing, and exit codes suitable for CI and systemd.

## Source of truth

The graph is primary. Files are the serialized form for git. When a
protocol is modified:

1. Edit the `.cypher` file
2. Re-run it against the local graph (idempotent; the new version supersedes)
3. Update the corresponding `Protocol` node's `cypher` property (or re-register
   via a registration script)
4. Verify the change did what you expected by inspecting the graph
5. Commit the file + any resulting changes to graph-state.cypher

The `Protocol` nodes in Neo4j and the `.cypher` files in git should agree.
Divergence is a bug; the graph's `Protocol.cypher` wins for what's actually
running, the file wins for what's committed as canonical.
