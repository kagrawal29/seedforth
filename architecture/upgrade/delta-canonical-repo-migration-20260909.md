# Delta canonical repository migration

Date: 2026-09-09
Status: Integration required; live deployment frozen

## Decision direction

`Seedforth/delta` is the target canonical repository because Delta is a
SeedForth platform component and the organization is intended to own project
repositories. `kagrawal29/delta` remains a source history to preserve during
migration, not a second active authority.

## Observed state

- `kagrawal29/delta` (`origin/main`): `53d4d96`.
- `Seedforth/delta` (`seedforth/main`): `d2961bc`.
- `/opt/delta`: `aef62a1` plus extensive uncommitted runtime and Mycelium work.
- Local SeedForth checkout has the interactive-session fix at `6a420e6`.
- The two GitHub lines diverge across runtime, templates, graph tooling,
  lifecycle, and deployment files. This is not a fast-forward migration.

## Migration contract

1. Freeze live Delta code changes while the migration is in progress.
2. Preserve the server working tree as a recovery artifact before changing it.
3. Create an integration branch rooted in `Seedforth/delta`.
4. Bring the newer OpenCode/Mycelium line into that branch deliberately,
   resolving runtime and template conflicts by behavior and tests.
5. Preserve the old personal-repo line as an archive tag or branch; do not
   delete or force-rewrite it.
6. Run the complete Delta test and deployment checks from the integration
   branch, then open a reviewable PR into `Seedforth/delta`.
7. After merge, repoint local and server remotes to `Seedforth/delta` and
   deploy only the merged commit.
8. Add a reconciliation check that blocks deployment when the server has
   uncommitted tracked changes, unknown files, or a different remote/commit.

## Runtime-state boundary

Repository code, templates, deployment scripts, and graph protocols are
versioned. Runtime state such as registries, locks, logs, inboxes, generated
fleet snapshots, credentials, and caches is not committed. The deployment
contract must explicitly identify and back up those paths.

## Approval policy

Human review is risk-based, not required at every merge. Routine, bounded
implementation PRs may be merged by the delivery system when CI passes, the
issue has execution-ready metadata, the change stays within its mandate, and
no human-owned gate is active.

Human approval is required for product meaning or content, pricing and
commercial behavior, payment/auth/data-model decisions, security or privacy,
irreversible production operations, repository/source-of-truth migrations,
and any issue explicitly marked `Human input needed` or `Awaiting human
approval`. Agents may still prepare the change, evidence, and recommendation
before that gate.

## Current gate

The interactive-session fix is locally tested but not deployed. Deployment is
blocked until the integration branch has been reviewed and the server's
uncommitted changes have been classified as source changes or runtime state.
