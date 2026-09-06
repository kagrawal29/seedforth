# Mycelium Platform Import

This directory is the initial sanitized working-tree import of Mycelium into the SeedForth platform repository.

## Source

- Source checkout: `tetrahedron/projects/mycelium`
- Source commit at import: `e43f15f1186e6bbc117d0daadbf1e5126123b5ec`
- Source branch: `fix/scope-split-and-deploy-flow-policy`
- Import type: sanitized working-tree snapshot

## Excluded

- Git metadata and nested repository state.
- `.claude/`, `.memsearch/`, `.pytest_cache/`, `__pycache__/`, and `dist-e2e/`.
- `team-credentials.env`.
- embedded credential TOML files.
- Local heartbeat and sync state.
- legacy Maverick CLI, Pulse, and bolt-proxy deployment trees.

The independent Mycelium repository remains the history/reference source until a dedicated history migration and secret-removal review are complete.

## Required before cutover

1. Reconcile imported files against the canonical Mycelium branch.
2. Remove or classify legacy Maverick/Pulse deployment assets.
3. Review all credential/configuration files for secret safety.
4. Add platform-level build and integration tests.
5. Record the platform commit used by the new server.
