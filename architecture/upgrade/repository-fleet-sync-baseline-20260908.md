# Repository fleet sync baseline

Date: 2026-09-08

The SeedForth root repository is an orchestration/registry repository. Its
`.gitignore` explicitly excludes independent project directories, so it is not a
backup mirror of all project source.

Each project must instead have its own canonical GitHub repository and a recorded
relationship to local checkouts, worktrees, and server releases.

Read-only local inventory found:

- Flowing Indian: dirty feature checkout, one local commit ahead of its tracked
  remote branch; server checkout is dirty and on a different `main` revision.
- Delta: dirty local checkout.
- Tetrahedron: dirty local checkout.
- Pulse and its nested tools: dirty feature checkouts with branch boundaries.
- Seedforthing: local branch is substantially divergent from its tracked remote.
- SolveOS: dirty and one local commit ahead.
- Several Delta project folders and Sceneforth OS have no configured origin.
- Most other remotes report clean, equal local/upstream revisions, but this is
  not a replacement for server-release verification.

Required system behavior:

1. Maintain a versioned repository registry with owner, canonical repository,
   default branch, local paths, server paths, and project status.
2. Run read-only reconciliation on a regular cadence.
3. Record GitHub SHA, local/worktree SHA, server/deployed SHA, dirty state,
   branch, freshness, and conflicts in Mycelium.
4. Never reset, pull, force-push, delete, or overwrite a dirty/divergent checkout
   automatically.
5. Block autonomous execution when the worker's source revision or server
   deployment relationship is unknown.
