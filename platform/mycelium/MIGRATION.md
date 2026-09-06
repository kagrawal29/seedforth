# Mycelium Platform Import

This directory is the sanitized working-tree import of Mycelium into the
SeedForth platform repository. It is the deployed platform source; the
standalone Mycelium repository remains a provenance/reference checkout.

## Source

- Source checkout: `tetrahedron/projects/mycelium`
- Source commit at import: `e43f15f1186e6bbc117d0daadbf1e5126123b5ec`
- Source branch: `fix/scope-split-and-deploy-flow-policy`
- Import type: sanitized working-tree snapshot (no nested Git history)

## Excluded

- Git metadata and nested repository state.
- `.claude/`, `.memsearch/`, `.pytest_cache/`, `__pycache__/`, and `dist-e2e/`.
- `team-credentials.env`.
- embedded credential TOML files.
- Local heartbeat and sync state.
- legacy Maverick CLI, Pulse, and bolt-proxy deployment trees.

The independent Mycelium repository remains the history/reference source. It is
not an active SeedForth runtime dependency and must not be used as the source
for server deployments.

## Completed cutover gates

1. Local, GitHub, and server provenance was recorded.
2. Legacy Maverick/Pulse material was excluded or bounded as reference-only.
3. Runtime credentials were removed from the deployed active path.
4. Platform tests and graph bootstrap validation pass.
5. The server runs an immutable SeedForth release.

## Follow-up boundary work

- Remaining standalone-source drift is tracked in the repository reconciliation
  ledger; do not reset dirty checkouts.
- Historical/local-development credential defaults in non-deployed scripts are
  retained only as migration evidence and must be removed when those scripts
  are either ported to the platform runner or moved under `archive/`.
