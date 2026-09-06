# Repository Reconciliation — 2026-09-06

## Authority

`registry/repositories.json` is the inventory. GitHub canonical branches are
the upstream source for versioned code. Local checkouts are working copies;
server product directories are runtime state and must not be overwritten
without a project-specific capture and approval. The consolidated platform
release is the server authority for Delta and Mycelium.

The root checkout also contains numerous untracked experimental/project
directories not listed in the registry. They were preserved and are outside
this reconciliation until separately classified.

## Local checkout snapshot

| Repository | Local branch / SHA | GitHub branch / SHA | Dirty | Interpretation |
|---|---|---|---:|---|
| Mycelium | `fix/scope-split-and-deploy-flow-policy` / `e43f15f` | `main` / `a928955` | 14 | Working source is not canonical; consolidated platform copy is deployed |
| Delta | `main` / `53d4d96` | `main` / `53d4d96` | 3 | Canonical standalone source matches remote; platform copy is deployed |
| Flowing Indian | feature branch / `c84e0fa` | `main` / unavailable from checkout | 10 | Local feature work; do not overwrite |
| Seedforthing | `master` / `9123434` | `master` / `0102ad8` | 0 | Local checkout behind automated remote; boundary rule added on current remote tip |
| SolveOS | `master` / `b4af595` | `master` / `36d8738` | 1 | Local checkout differs from remote |
| Ember | `main` / `1fc3dde` | `main` / `1fc3dde` | 0 | Synchronized |
| Audioworld | `main` / `c7796f6` | `main` / `460902a` | 0 | Local checkout differs from remote |
| Website | `main` / `1924519` | `main` / `1924519` | 0 | Synchronized |
| Tetrahedron | `main` / `262aa14` | `main` / `079ac5b` | 11 | Reference-only; preserve, do not merge into platform |

Hashes are abbreviated evidence from the read-only reconciler, not proposed
merge decisions. Re-run `python3 operations/reconcile.py` before acting.

## Server snapshot (`delta2`, 185.192.96.100)

| Path | Branch / SHA | Dirty | Policy |
|---|---|---:|---|
| `/opt/seedforth/current` | detached / `bed326a` | 0 | Active immutable platform release |
| `/opt/delta` | `main` / `53d4d96` | 10 | Disabled legacy rollback checkout; retain intact |
| `/home/proj-flowing-indian/flowing-indian` | `main` / `54ced2f` | 9 | Active product runtime; capture before cleanup |
| `/home/proj-seedforthing/seedforthing` | `master` / `5e8e5de` | 436 | Active product runtime; behind automated remote; do not reset or pull blindly |

### Security exception

The Seedforthing runtime contains a tracked file at
`delta-config/.vercel-token-charlietheagent`. Its contents were not printed or
copied. The file mode was hardened in place from `777` to `600`, preserving the
live path and owner. Because the file is tracked in the product repository
(and may therefore exist in repository history), the product owner must rotate
the token and scrub the product repository history before that checkout can be
called deployment-clean.

## Next safe actions

1. Capture diffs and runtime artifacts from each dirty product checkout.
2. Ask each project whether local/server changes are intended, publishable, or
   generated state before choosing merge, commit, archive, or discard.
3. Create explicit migration records for Mycelium and Delta standalone remotes;
   do not delete them while the platform subtree remains history-sensitive.
4. Keep Tetrahedron reference-only and retain its GitHub repository.
