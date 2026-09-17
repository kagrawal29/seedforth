# State and Synchronization Contract

**Status:** Canonical target architecture  
**Last reviewed:** 2026-09-06

## Authority matrix

| State | Authority | Direction |
|---|---|---|
| Source code | GitHub repository | GitHub → local/server checkout |
| Local edits | Local checkout | Developer → PR |
| Deployed code | Server checkout + recorded SHA | GitHub → server → process |
| Process liveness | Supervisor | Supervisor → FleetState → Mycelium |
| Runtime configuration | Delta registry | Registry → Mycelium observation |
| Agent identity/capabilities | Mycelium | Mycelium → grounding/config |
| Engineering workstreams and work items | GitHub Issues/Projects | GitHub → Mycelium projection → agents/UI |
| Platform protocols and graph-native work | Mycelium + authored Git | Git → Mycelium → runtime |
| Human decisions | Mycelium | channels/UI → Mycelium |
| Protocol definitions | Git-authored graph files | PR → bootstrap → verify |
| Protocol execution | Mycelium | ProtocolRun/evidence nodes |
| Commits and diffs | GitHub/Git | GitHub/Git → progress signals → Mycelium |
| Raw transport logs | Filesystem/provider | raw log → durable summary |
| External account state | External provider | provider → observed graph state |

## Reconciliation states

Every observed entity should resolve to one of:

```text
healthy | drifted | conflicting | stale | orphaned | unknown
```

Examples:

- supervisor running + graph stopped → `conflicting`;
- graph active + no runtime process → `stale` or `orphaned`;
- server SHA differs from declared deployment SHA → `drifted`;
- active workstream without recent progress → `stale`;
- registry project without graph identity → `orphaned`.

For every active product repository, the canonical engineering relationship must
also be recorded across three locations:

```text
GitHub canonical branch / PR
        ↕
local checkout or worktree
        ↕
server checkout or deployed release
```

The graph records observed SHAs, branch, worktree, deployment, freshness, and
conflicts; it does not make an unverified local or server checkout authoritative.
A worker may execute only against a pinned, identified revision and must report
the revision it actually changed.

## Reconciliation rules

1. Read all sources before writing any derived state.
2. Never silently overwrite an authoritative source.
3. Record the observation timestamp and source.
4. Create `StateConflict` or `ActionProposal` when sources disagree.
5. Permit automatic repair only for derived liveness and safe metadata.
6. Require human or policy approval for strategic status, ownership, deletion, or external side effects.
7. Record the deployed platform commit and graph bootstrap version in Neo4j.
8. Treat GitHub webhook ingestion as incremental observation and run periodic
   reconciliation against GitHub, local checkouts, and server releases. Missing,
   stale, divergent, or dirty state is visible and blocks unsafe execution.

## Promotion path

```text
Edit authored graph definition
  → local graph test
  → pull request
  → review gates
  → server bootstrap
  → verification query
  → protocol execution
  → runtime evidence
```

## Backup path

```text
Live Neo4j
  → scheduled export/snapshot
  → restore test
  → integrity report
  → retained backup
```

Backups are recovery artifacts, not a substitute for authored graph definitions.
