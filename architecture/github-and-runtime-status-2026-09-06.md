# GitHub and runtime reconciliation — 2026-09-06

This is a read-only baseline captured during the SeedForth consolidation.
Re-run `python3 operations/reconcile.py --server root@185.192.96.100
--graph root@185.192.96.100` for current runtime facts.

## Repository state

| Repository | Local checkout | GitHub default branch | Relationship |
|---|---|---|---|
| `kagrawal29/seedforth` | `fe37d58` | `aa8cb8f` | local platform branch is 147 commits ahead; not yet pushed |
| `kagrawal29/delta` | `53d4d96` | `53d4d96` | local main matches GitHub main; local runtime files are dirty |
| `kagrawal29/mycelium` | `e43f15f` on `fix/scope-split-and-deploy-flow-policy` | `a928955` on main | local work is not the GitHub default branch and has 14 dirty files |
| `kagrawal29/tetrahedron` | `262aa14` | `079ac5b` | retained as reference-only; local checkout is not synchronized |

The SeedForth GitHub repository is currently public; the Delta, Mycelium, and
Tetrahedron repositories are private. Branch protection checks did not return
an enabled protection policy for SeedForth or Delta at capture time.

## New-server state

- Server: `185.192.96.100` (`delta2` in the registry)
- Delta service: active and enabled from `/opt/delta`
- Neo4j: `mycelium-neo4j` running and reachable on Bolt `:7687`
- WAHA: running on localhost `:3000`
- Product checkouts: Flowing Indian and Seedforthing are present, but contain
  generated/runtime changes and are not deployment-clean
- Immutable consolidated releases are staged at
  `/opt/seedforth/releases/a8adca5`; the published release is clean, but
  `/opt/seedforth/current` still points to the previously validated
  `ff350d9` release because existing services have not been switched
- Linux/amd64 Mycelium CLI artifact staged under the release and reports
  version `a8adca5` from `/opt/seedforth/shared/bin/mycelium`
- The new Mycelium heartbeat service has now passed a manual invocation and
  its timer is enabled. The live graph atoms repaired during that validation
  are convergence null-key handling, relationship-safe TTL deletion, and the
  single-statement Charlie Focus atom.

## Live graph snapshot

At capture: approximately 30,420 nodes, 25,565 relationships, 32 enabled
protocols, 12 active graph agents, 3 pending decisions, and the latest
protocol run at `2026-09-06T10:00:05.479Z`. Counts are dynamic and are evidence
of liveness, not a version identifier.

## Required convergence order

1. Push or deliberately retain the reviewed platform commits with a release
   tag/manifest.
2. Create a server-side release checkout at `/opt/seedforth` without stopping
   the legacy runtime.
3. Run component and integration gates against the release checkout.
4. Record the platform SHA, component SHAs, and graph bootstrap version.
5. Wire the runtime secret contract and install Go-built artifacts; the server
   currently has no Go toolchain.
6. Switch services using a reversible systemd/environment change.
7. Reconcile again and retire `/opt/delta` only after a stable observation
   window.
