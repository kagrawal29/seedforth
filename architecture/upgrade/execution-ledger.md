# Autonomous upgrade execution ledger

Authorization: on 2026-09-06 the owner instructed end-to-end autonomous execution,
including implementation, deployment, and verification. The previous planning-only
boundary is superseded for this upgrade. Business-side effects still require
specific mandates; no budgets, recipients, or commercial targets are invented.

Source branch: codex/seedforth-system-upgrade. Preserve unrelated local work.
Current known production release: 1770e7cdc085e36840ed5b2d5b116811348a5ae0.

## Progress

- Prepared full review package and recorded authorization to proceed.
- Live baseline B01–B17 established target identity and significant execution gaps.
- Implementation starting with trustworthy runner evidence and graph contracts.
- Runner, graph, and gateway tests: 29 passed on the isolated delta2 test graph
  in 3.72 seconds. Earlier platform boundary suite: 9 passed. New suite includes
  live concurrent claims, denied scope, expired leases, late results, holds,
  independent review, altered operation source, and credential revocation.
- Production preflight found nine duplicate historical ProtocolRun IDs and two
  enabled heartbeat protocols without FIRST_ATOM chains. Preserve historical IDs;
  v2 evidence uses a separately constrained VersionedProtocolRun label.
- Root cron still invokes legacy heartbeat (30 minutes), dream (4 hours), deep,
  long, fleet ingest, and context ingest alongside the new 1-minute timer.
- Consistent production snapshot completed; live Neo4j restarted successfully.
  Snapshot: /opt/seedforth/shared/backups/upgrade-20260906.I8ocj1Ch/neo4j.dump,
  mode 0600, SHA256 0ce702f4f5196c6efd6d6ec1543790ebfe0726613d95a30df23e8d5a86165d3e.
  Isolated restore verified 47 projects and 26,403 historical ProtocolRuns.
- Disposable test container seedforth-upgrade-test-20260906 uses delta2 loopback
  port 27474; restored snapshot seedforth-upgrade-restore-20260906 uses 28474.
  Tests now execute on the remote scratch venv (no fragile local SSH test tunnel).
  Scratch directory: /tmp/seedforth-upgrade.Eb1GkXTC.
- Authored additive v2 migration succeeded twice against restored production data.
  Most recent source hash: 01268043a5e5457434033a16d6817ccb42249bba1aba6e8241c6cde91c934b72.
  This migration is now applied and verified in production from immutable commit
  6f232e9b599ba9e22322f0eda8524dc76c2acfb1 (also pushed to the upgrade branch).
  Both pilot scopes are active but held for new execution, 11 reviewed graph
  operations exist, all 47 project records remain, and Delta/heartbeat stay active.
  Main platform symlink remains on 1770e7c. No scheduler cutover has run yet.
- Initial loopback gateway and responsive board implemented. Per-principal scoped
  bootstrap credentials are not OAuth. Public remote MCP is not delivered yet.
- Browser fixture checks passed: desktop project/inspector, 390px mobile layout,
  no browser credential storage, and clearing work data on disconnect. This is
  fixture UX validation, not production browser-to-worker acceptance.
- Restored-data container stopped after migration verification to close the
  temporary loopback read surface. Its dedicated volume and backup are retained.
- Next component includes runtime SourceStreams and append-only Observations with
  idempotency, late-event preservation, failed-collection visibility, and stale
  projection. Process observation never changes owner-directed portfolio state.
- Sensing/gateway/runner suite: 32 passed in the disposable graph. Updated schema,
  sources, and owner bootstrap grants applied twice to the restored snapshot;
  source hash edc37dbc8d3ed87d7de4c814a71fb98f08d7d591d79f85b61aa1a1bcf622b54f.
  Restore container stopped again. Separate hardened loopback services prepared;
  source polling is not autonomous project execution.
- Full runtime cutover, public remote interface, and autonomy trials remain
  incomplete. Do not describe this ledger as completion of the upgrade.

## Execution rules

Implement graph-native domain behavior in authored Cypher; external adapters and
enforcement machinery remain versioned code. Test in disposable Neo4j on delta2
bound only to loopback because local Docker is unavailable. Never use production
as a fixture. Record exact test results and release/migration receipts here.

Before each live migration: inventory affected writers, snapshot and verify restore,
test idempotency and denied operations, and retain rollback. Keep new external
actions disabled until their authority and postconditions are implemented.
