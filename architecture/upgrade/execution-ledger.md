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

Current deployment update: control release 7b433aa is live (see promotion evidence
below). Broker Cypher and worker boundary source are deployed, but the production
broker/isolated-worker daemon and useful model/code capabilities still need to be
implemented and provisioned. Do not confuse source promotion with active execution.

## Broker implementation qualification

- Added graph-native invocation admission, dispatch, and settlement. Admission
  reserves bounded action units once per intent. Mandate ID/version, scope, lease,
  capability generation, cost, deadline, and holds are enforced. Claims now bind
  an explicit mandate and current assignee rather than silently accepting no mandate.
- Separate broker authority admits results after worker revocation, including
  unknown outcomes that retain reservations. Failed executions are charged their
  reserved bound conservatively. Cancellation before dispatch releases it.
- Trusted dispatch uses immutable adapter bindings, never graph-supplied imports
  or shell commands. The concrete Git adapter only inspects pinned commit/tree IDs.
- Durable private receipt journal supports recovery without redispatch. Real Git
  fixture tests cover connection loss before and after the graph commits settlement.
- Full current suite: 44 passed on disposable Neo4j in 5.89s. Local unit suite:
  25 passed. Production read-only preflight: Mandate/Budget/InvocationResult have
  zero records, Capability has 21 records with zero duplicate non-null node IDs.
- These broker changes are not yet promoted to production or exposed to workers.
  Runtime remains on control release 6fe3ee4. Before promotion, test against restored
  production data and finish concurrency/revocation/deadline qualification. Next
  integrate the isolated worker/executor and actual project workflows. This is
  execution-foundation progress, not a completed autonomous product outcome.

## Execution rules

Implement graph-native domain behavior in authored Cypher; external adapters and
enforcement machinery remain versioned code. Test in disposable Neo4j on delta2
bound only to loopback because local Docker is unavailable. Never use production
as a fixture. Record exact test results and release/migration receipts here.

Before each live migration: inventory affected writers, snapshot and verify restore,
test idempotency and denied operations, and retain rollback. Keep new external
actions disabled until their authority and postconditions are implemented.

## Isolated worker path qualification

- Added a private Unix worker interface, expiring scoped identity binding,
  recoverable attempt reads, and atomic per-scope claim concurrency (default one).
  Worker operation allowlist excludes owner controls, policy, grants, and review.
- Added complete-invocation-work: worker success derives artifact identity from
  an actual successful broker invocation and enters review without progress credit.
- Qualified the actual path in disposable Neo4j through a non-root Docker worker:
  no network, read-only filesystem, dropped capabilities, no-new-privileges,
  resource caps, and only a broker socket plus fixture input/credential mounts.
  Scope/identity forgery and policy/review/settlement calls are rejected.
- Official test image pinned as
  python@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254.
- Full suite including the actual Docker worker: 57 passed in 12.74s. Local
  transport/broker tests: 14 passed. No product outcome or production worker
  activation is claimed. Current production control release remains 6fe3ee4.
- Next: promote the qualified schema after restored-data checks, provision the
  protected production worker/broker service, add useful bounded model/code adapters
  with monetary budgets and independent verification, and qualify actual product
  work. Keep remote MCP, Graphify, archival, and wider reliability scope active.

## Human-interface browser qualification

- Owner requires Playwright CLI for every human interface and delegates imitating
  the human operator in testing. Full-plan readiness by the next-day return is the
  target; no acceptance gate or honest soak requirement is removed.
- Added pinned Playwright CLI 0.1.19 journeys for the shipped UI. Synthetic-response
  regression passed login/storage, stale source visibility, HTML escaping, legacy
  non-actionability, versioned hold/conflict, outage recovery, mobile/desktop,
  concurrent inspectors, in-flight logout and revocation scenarios.
- Fixed response ordering so stale inspector/refresh results cannot replace the
  current selection; logout invalidates in-flight work and clears scoped content.
  Access denial remains visible without restoring an invalid session.
- Real browser -> HTTP gateway -> authored Cypher -> disposable Neo4j passed:
  22 work packages, persisted hold across logout/reload, restoration of initial
  hold disposition, and cross-scope denial. Independent graph read confirmed W00
  hold=false, state_version=2, two accepted dispatch_hold_changed signals.
- Desktop and 390px mobile screenshots captured locally; mobile visually inspected.
  Local boundary/worker/broker/runner/sensor suite: 35 passed in 5.13s.
- These tests simulate the owner in staging, not personal owner sign-off or
  useful product progress. No production UI deployment in this step. Runtime
  control release remains 6fe3ee4; additive broker promotion and actual governed
  project execution remain next, alongside remote MCP, Graphify and archival.

## Broker pre-promotion checks

- Added eight real-Cypher negative scenarios for revoked grants, disabled identity
  or scope, insufficient lease or mandate time for the full capability duration,
  changed mandate version, removed capability permission, and policy generation
  changes. Admission and dispatch both deny; the separate broker refunds an
  admitted-but-never-dispatched reservation even after revocation.
- Added six-way concurrent admission against a two-unit budget and concurrent
  dispatch of one invocation. Exactly two reservations and one dispatch succeed.
- Full disposable suite including the pinned isolated Docker worker: 66 passed
  in 13.34s. Restored-data checks and immutable-release qualification follow;
  this entry does not claim production promotion or useful product execution.

## Live control promotion — 2026-09-06 15:39 UTC

- Immutable release 7b433aa77b3a8758d85c06e66ea3a5c48294132f passed all 66 tests
  in 18.65s, including the pinned actual Docker worker. JUnit SHA256:
  ad1395da1ad9ccd5e376fa118bec8db88e7e2026ff4781cbed48fccb90c0add5.
- Migration applied twice on the earlier restored snapshot and twice on a fresh
  restored backup, preserving all 47 projects and exposing the 22 plan packages.
  Migration hash: c2639ed98c231a12c5b2052f4817691f8a2213936fa0eade26c3fe71d5cdcf4f.
- Fresh consistent backup (brief authorized offline maintenance):
  /opt/seedforth/shared/backups/upgrade-20260906.YpoVAtt0/neo4j.dump,
  SHA256 73f48dd8d9bb3ea2795eb9eb4eaa4147d42d83eb72d637b8db001739a08d5873.
  New isolated restore container/volume seedforth-restore-7b433aa retained, stopped
  after successful verification. Production restarted and HTTP/graph checks passed.
- Applied production migration and switched only control-current from 6fe3ee4 to
  7b433aa. Main platform remains 1770e7c. Control, sensing timer and Delta active.
  A deployment receipt records the prior target; full backup remains available.
- Live gateway verified 22 platform items, six unverified legacy Flowing items,
  both runtime sources fresh, all scopes held, and the linked 66-test qualification.
  Served app.js exactly matches the Playwright-qualified release. No production
  Invocation exists; production worker execution has not been enabled.
- Next focus is the actual protected production executor with useful bounded
  model/code capabilities and independent project acceptance, plus the remote
  MCP, Graphify, portfolio/lifecycle and reliability work already in the full plan.
