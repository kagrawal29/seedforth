# Autonomous upgrade execution ledger

Authorization: on 2026-09-06 the owner instructed end-to-end autonomous execution,
including implementation, deployment, and verification. The previous planning-only
boundary is superseded for this upgrade. Business-side effects still require
specific mandates; no budgets, recipients, or commercial targets are invented.

Source branch: codex/seedforth-system-upgrade. Preserve unrelated local work.
Current known production release: 1770e7cdc085e36840ed5b2d5b116811348a5ae0.
Separate control component: 6fe3ee4b65e855901d9d5011690a07241c7ed88b,
deployed via /opt/seedforth/control-current. Active end-to-end goal registered
at the owner's explicit request. No token budget was requested.

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
  Restore container stopped again. Separate hardened loopback services deployed
  and verified. Both pilots report fresh process observations, unauthorized scope
  returns 403, the board serves HTTP 200 with CSP, and port 8787 binds only loopback.
  Automatic second sensor cadence succeeded. Source polling is not useful project
  execution. Bootstrap access expires seven days after provisioning and is not OAuth.
- Full runtime cutover, public remote interface, and autonomy trials remain
  incomplete. Do not describe this ledger as completion of the upgrade.
- Goal tracking is now active at the owner's request. The authored graph backlog
  contains W00–W21 with phase milestones, goal links, dependencies, and acceptance.
  Plan admission leaves all packages proposed until qualifying execution/review.
- Release 6fe3ee4 adds legacy-work triage, evidence inspection, platform scope,
  and real JUnit qualification admission. 35 tests passed from the immutable
  release on the disposable graph. Migration hash
  006b3bdbedb5fa29aa5cdb2cb10c59924b8c1ceb1d3c901f4bb1650dbe352185
  passed twice on the restored production graph, then was deployed live.
  Gateway smoke checks verified 22 platform work packages, the actual 35-test
  qualification, six unverified legacy Flowing Indian work items, and fresh sensing.
  Owner bootstrap scope now includes the platform, without changing token/expiry.
  Qualification artifact SHA256:
  a764860a246716c3fa36eaef428eaad0f939bebd8a5d1b2432ee0ee079c5510d.
  It is linked to W21 as release evidence, not credited as product progress.
  The old Graphify experiment remains unrecovered: a different desktop graphify-out
  was inspected by counts only (107/116 through 418/667), not the audit's 973/1980
  code slice. No legacy Maverick graph or CLI was used. Original historical
  handoff docs contain plaintext credentials: keep them out of release material
  and include dependent-service rotation/redaction in security remediation.

## Immediate continuation

Continue the active end-to-end goal, not another planning-only pass. Next priority:
protected capability broker and useful governed executor (W12/W13), including
isolated workers, budgets, durable invocation/outcome reconciliation, and strict
promotion controls before replacing the unsafe legacy division path. Continue
Graphify/source census and remote TLS/OAuth/MCP alongside that boundary. The
loopback board is an early interface, not the complete UX or remote-access promise.
No autonomous product outcome, archival, public MCP, scheduler retirement, or
30-day soak has been demonstrated. Preserve this distinction in progress reports.

## Execution rules

Implement graph-native domain behavior in authored Cypher; external adapters and
enforcement machinery remain versioned code. Test in disposable Neo4j on delta2
bound only to loopback because local Docker is unavailable. Never use production
as a fixture. Record exact test results and release/migration receipts here.

Before each live migration: inventory affected writers, snapshot and verify restore,
test idempotency and denied operations, and retain rollback. Keep new external
actions disabled until their authority and postconditions are implemented.
