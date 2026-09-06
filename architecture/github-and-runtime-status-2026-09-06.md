# GitHub and runtime reconciliation — 2026-09-06

This is a read-only baseline captured during the SeedForth consolidation.
Re-run `python3 operations/reconcile.py --server root@185.192.96.100
--graph root@185.192.96.100` for current runtime facts.

## Repository state

| Repository | Local checkout | GitHub default branch | Relationship |
|---|---|---|---|
| `kagraw29/seedforth` | `30c6a0d` | `30c6a0d` | local platform main matches GitHub main; live runtime is pinned to tested `bed326a` |
| `kagrawal29/delta` | `53d4d96` | `53d4d96` | local main matches GitHub main; local runtime files are dirty |
| `kagrawal29/mycelium` | `e43f15f` on `fix/scope-split-and-deploy-flow-policy` | `a928955` on main | local work is not the GitHub default branch and has 14 dirty files |
| `kagrawal29/tetrahedron` | `262aa14` | `079ac5b` | retained as reference-only; local checkout is not synchronized |

The SeedForth GitHub repository is currently public; the Delta, Mycelium, and
Tetrahedron repositories are private. Branch protection checks did not return
an enabled protection policy for SeedForth or Delta at capture time.

## New-server state

- Server: `185.192.96.100` (`delta2` in the registry)
- Delta service: active and enabled from `/opt/seedforth/current/platform/delta`
- Neo4j: `mycelium-neo4j` running and reachable on Bolt `:7687`
- WAHA: running on localhost `:3000`
- Product checkouts: Flowing Indian and Seedforthing are present, but contain
  generated/runtime changes and are not deployment-clean
- `/opt/seedforth/current` points to immutable release `bed326a`; the
  consolidated Delta service is active and the legacy `/opt/delta` unit is
  disabled but retained for rollback
- Linux/amd64 Mycelium CLI artifact is installed at
  `/opt/seedforth/shared/bin/mycelium` and managed independently from the
  Python service release
- The new Mycelium heartbeat service has now passed a manual invocation and
  its timer is enabled. The live graph atoms repaired during that validation
  are convergence null-key handling, relationship-safe TTL deletion, and the
  single-statement Charlie Focus atom.

## Live graph snapshot

At refresh: approximately 31,136 nodes, 25,714 relationships, 32 enabled
protocols, 11 active graph agents, 3 pending decisions, and the latest
protocol run at `2026-09-06T11:36:32.845Z`. Counts are dynamic and are evidence
of liveness, not a version identifier.

## Completed convergence order

1. Reviewed platform commits are pushed to GitHub main.
2. The immutable release checkout exists at `/opt/seedforth` and is clean.
3. Component tests, graph bootstrap, and runtime smoke checks pass.
4. Runtime secret wiring and the Linux Mycelium artifact are installed.
5. Services were switched through reversible systemd and symlink changes.
6. Post-cutover reconciliation confirms active Delta, successful heartbeat,
   and preserved rollback checkout.

Remaining cleanup is repository/product drift, not platform cutover.
