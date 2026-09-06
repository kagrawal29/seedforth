# SeedForth platform deployment

This directory describes the target deployment of the platform components on
the new SeedForth server. It is intentionally declarative: credentials stay
in the server secret environment, while code and service definitions are
versioned here.

## Release layout

```text
/opt/seedforth/
  current -> releases/<platform-sha>/
  releases/<platform-sha>/platform/{mycelium,delta}/
  shared/env/                 # root-owned, mode 0640, group-readable by delta
  shared/backups/
```

The existing `/opt/delta` runtime remains the rollback target until the new
release has passed its observation window. Do not delete it during rollout.

## Required release manifest

Each release must record:

- SeedForth platform commit;
- imported Mycelium and Delta source commits;
- graph bootstrap/protocol version;
- server checkout timestamp;
- test results and operator;
- rollback target.

The manifest is written only after the release checkout is complete and tests
pass. A service must never run from a mutable Git working tree.

The first completed manifest is
[`release-manifest-0402f84.json`](release-manifest-0402f84.json). Subsequent
releases should carry the same evidence fields with their own immutable
platform commit.

## Cutover sequence

1. Fetch the reviewed SeedForth commit into a new immutable release directory.
2. Validate the manifest, runtime environment, file ownership, and secret
   permissions.
3. Run Mycelium Go tests, Delta focused tests, import checks, and read-only
   graph health checks.
4. Start the new Mycelium heartbeat in parallel with the legacy runtime and
   verify one complete protocol cadence.
5. Start the new Delta service in a non-conflicting validation mode, then
   switch the Discord/WhatsApp consumers during a short maintenance window.
6. Reconcile server, supervisor, Git, and graph state.
7. Keep `/opt/delta` intact until the release is stable; rollback is a systemd
   unit/environment switch back to the recorded legacy target.

No step in this runbook mutates the graph implicitly. Graph writes happen via
reviewed bootstrap/protocol commands and are verified with a post-deploy query.

For a reproducible Delta validation environment, install
`platform/delta/requirements-test.txt` in an isolated virtual environment;
do not rely on the system Python package set. The production service does not
need pytest installed.

## Secret contract

`seedforth.env` is external to Git and must provide the values required by
Delta plus:

```text
MYCELIUM_DEV_BOLT_URI
MYCELIUM_DEV_USER
MYCELIUM_DEV_PASSWORD
MYCELIUM_PROD_BOLT_URI
MYCELIUM_PROD_USER
MYCELIUM_PROD_PASSWORD
```

Use a root-owned file readable only by the service account group (currently
mode 0640, `root:delta`) or a secret manager. Do not put tokens in systemd
unit files, Git remotes, release artifacts, or CLI binaries.
