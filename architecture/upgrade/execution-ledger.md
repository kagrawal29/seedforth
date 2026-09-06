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
below). Worker component 3d8feef is live and the first bounded Cajon code pilot has
completed through production invocation, fresh browser verification, delegated
review and source application. This is a deterministic executor of an agent-authored
proposal, not generalized model-driven autonomy. Next address the explicit checkout
follow-up, Flowing Indian's pilot, model/cost controls, remote MCP, Graphify and
the remaining full-plan phases. Do not confuse one accepted code artifact with
completion of the system upgrade or proof of long-term autonomous operation.

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

## Protected service entry point qualification

- Added Linux socket-activated broker entry point, restricted external repository
  bindings, systemd sandbox units and durable receipt reconciliation before new
  dispatch. The broker's socket survives process replacement without unlinking
  another process's endpoint. The inherited descriptor cannot leak to adapters.
- Exact worker identity remains credential-bound, and execution/budget/mandate
  behavior remains in the authored graph operations. Startup cannot promote code,
  grant access, create mandates or activate work. Recovery conflicts fail closed.
- Full disposable Linux suite: 71 passed in 11.64s, including actual Docker worker,
  inherited descriptor validation, two service instances over the same socket,
  and recovery-before-dispatch checks. Systemd unit syntax validation passed.
  Linux-only activation tests are explicitly skipped on macOS; their delta2
  execution, not a local skip, is the qualifying evidence.
- Service is source-only pending explicit provisioning. Current live control
  remains 7b433aa. The first adapter still only inspects Git provenance. Next add
  useful isolated code/model capabilities and scoped launcher provisioning with
  monetary budgets and independent product acceptance; full-plan scope remains.

## Product-grounded source and acceptance baseline

- Rechecked live scopes: Flowing Indian and Cajon remain held. Actual agent working
  directories are /home/proj-flowing-indian/flowing-indian and
  /home/proj-cajon-sensei/cajon-sensei, not /opt/delta/projects paths. A running
  opencode process still does not establish useful execution or a deployed app.
- Local Flowing Indian has preexisting tracked/untracked edits, preserved untouched.
  Existing webhook tests read local secrets and call Clerk; do not run them as
  isolated tests or send synthetic payment webhooks to production by accident.
- Added explicit-path, exact-commit Git blob snapshots for worker/source-sensing
  inputs. No working-tree reads, symlinks, submodules, history enumeration, mutable
  revision names, arbitrary paths or repository execution. Coverage and untrusted
  source status are explicit. Size/deadline bounds and secret-pattern tripwires
  are defense-in-depth, not exhaustive secret classification.
- Local tests: 12 passed. Full disposable Linux suite: 83 passed in 12.28s.
  Actual local snapshots succeeded for Cajon app/index.html at
  498b17acbd832b37744b9138abf3e4d52bc81f57 and Flowing API order/verify at
  c84e0fa4453f02a60ac992f403cfa8f79900004c. These are local-checkout provenance,
  not an assertion that remote runtime or production serves those revisions.
- Playwright CLI reproduced a real Cajon defect: after 200ms simulated time at
  80bpm the app credits one complete loop (expected zero, full cycle 3000ms).
  New cajon-loop.playwright.js fails on the current app as expected. No app fix
  has been made. Playback-only milestone unlocks also lack clean-playing evidence
  and need a separate honest UX decision rather than silently claiming mastery.
- Admitted authored pilot finding twice in staging, then to live Mycelium:
  wi-cajon-partial-loop-credit is proposed/held, with an independent failed
  baseline TestRun and acceptance criteria. Verified through scoped read-work and
  read-evidence. Admission source hash:
  d9904103615656e0e367b69e9ade017054165f78ff346b5e01328c85e2c0a206.
- Snapshot adapter and worker service remain source-only. Next connect scoped
  artifact delivery and bounded model/code proposal execution, then use this
  real failing case to qualify the complete product loop. Do not count the
  baseline finding or source snapshots as a fixed product or accepted outcome.

## Worker artifacts and governed code proposals

- Added own-invocation artifact reads through the private worker interface. Graph
  checks enabled identity, unexpired read/execute grant, scope, ownership and
  successful result. Broker validates exact capability-bound filename and hash,
  rejects symlinks/nonregular files and oversized responses, and returns untrusted
  content without host paths. Revocation denies subsequent reads.
- Added bounded old/new code proposals against exact Git source. Unique match,
  promoted path coverage, revision, request/output size and deadline are enforced.
  Candidate artifact records base and proposed hashes, with applied=false and
  verification_status=not_run. No repository mutation, execution or self-acceptance.
- Service registry now includes code snapshot and proposal capabilities, still
  inactive until explicit production provisioning/promotion. Bounds accommodate
  the real newer Cajon file: 256KiB/file, 512KiB total, 1.2MB serialized artifact.
- Full disposable Linux suite: 95 passed in 14.05s. Actual isolated Docker worker
  read its own artifact. Real graph code-proposal fixture produced/read candidate
  code and entered review while leaving repository unchanged and ProgressEvent
  count zero. Source-only progress, not a useful accepted production outcome.
- Remote census found newer product revisions: Cajon
  2a518d957bb1fbd39b02a8dcbc3e1f2890630b93 and Flowing
  54ced2fe429b90576d59f005e9d6ebf9d8d69a6a. Cajon app/index.html hash
  56b092507f73ff644f742f63f3bd43802f3638df85895000c37282644a1b83b0
  differs from the local tested app and still contains the suspect credit condition.
  Remote working trees contain operational edits/history; preserve them.
- Added the remote source baseline to live Mycelium after twice-applied staging
  admission. The held Cajon task keeps its original failed local baseline and
  separately records the newer candidate revision as not_browser_tested. Do not
  present a local-copy fix as a verified change to the current remote product.
- Next: qualify the current remote app, produce the candidate through the governed
  worker path, independently test its exact artifact with Playwright CLI, review
  and apply it safely. Model-driven work, monetary budgets, public MCP, Graphify,
  archival, full UX and unattended qualification remain part of the active goal.

## Current Cajon candidate browser qualification

- Rechecked remote HEAD 2a518d957bb1fbd39b02a8dcbc3e1f2890630b93 and copied only
  app/index.html for isolated browser qualification. Its hash matches the recorded
  remote baseline. Updated browser entry to choose Basic Rock in the current UX.
  The first-beat regression fails on this current build too (expected 0, actual 1).
- Playwright additionally exposed a real pause-rendering ReferenceError:
  resonanceMult is read before its block-scoped declaration in drawDojoCanvas.
- The agent-authored explicit edit proposal was executed through the real broker
  on disposable Mycelium using the current remote Git source, not a hand-edited
  product checkout. It fixes cycle-boundary accounting, initial beat/count-in,
  partial cycles on tempo changes, and resonance declaration ordering.
  Fixture scope fixture-5b07211a3ce448fe9181c9a6bc65fcd0,
  invocation ac75c27effee49d6b05318bbb782c277. This was a trusted staging harness,
  not an isolated production worker or generalized model-driven autonomy.
- Candidate app SHA256:
  dad62bbc229af2cb827326608660bb23ef64381caa7a48909cddc000ffc53a85.
  All 12 actual Playwright CLI acceptance scenarios passed: initial beat, full
  cycle, pause, restart, keyboard tempo change, count-in, and error-free rendering
  through desktop/mobile resize. Mobile screenshot visually inspected; broader
  responsive/accessibility and musical-accuracy claims are not made.
- Qualification metadata is versioned in evidence/cajon-candidate-20260906.json.
  Exact candidate, metadata and test source retained root-private at
  /opt/seedforth/shared/backups/cajon-candidate-dad62bbc229a. Content hashes and the
  successful staging Invocation artifact hash were checked before archival.
- Added staged-candidate TestRun evidence to the actual Cajon task in live graph.
  Work remains proposed/held and candidate explicitly not applied. Product checkout
  and runtime unchanged. Full platform suite remains 95 passed (12.70s latest).
- Next land this verified candidate through the production governed attempt,
  separate exact-artifact verification/review and safe source/deployment promotion.
  Then expand useful work to Flowing Indian and continue the full upgrade scope.

## Production protected broker provisioned

- Worker component ae992b14d9e398de2a0f36a1a789ffc7e9ca2d99 is installed at
  /opt/seedforth/worker-current. Main Delta remains 1770e7c and control remains
  7b433aa. Both worker socket/service and existing Delta/control services are active.
- Uses an unprivileged static broker account, private StateDirectory, source-read
  group and root-private worker socket directory. Socket mode 0660 grants only
  seedforth-workers. The broker's pinned shallow source copy is root-owned and
  group-readable, not writable by workers or the broker. No legacy project mount
  or Docker/Neo4j credential is exposed to workers.
- Qualified authority twice on disposable and restored graph, preserving 47
  projects and all scope holds. Immutable-release suite: 95 passed in 14.79s.
  Qualification JUnit admitted to the live platform plan as release evidence.
- Provisioning initially stopped at Git's cross-owner local transport check before
  creating credentials/grants. Exact upload-pack source trust (not global wildcard
  trust) allowed the private clone; provisioning then resumed from inspected state.
  Installer source now includes that exact-path fix for future reconstruction.
- Pilot worker principal has Cajon-only read/execute grants, two bounded artifact
  invocation units, and no monetary authorization. Credential and mandate expire
  2026-09-06T17:08:00.013208+00:00. Secrets are root-private external files; never
  copy them into tool output or the repository. Work scope is still disabled/held.
- Live private API read-work succeeded; other-scope read and review were denied;
  claiming the held task was denied. Service restart retained the same listening
  socket inode and recovered API access. Graph independently confirms zero pilot
  attempts, zero spent/reserved units. No product work has executed in production.
- Next run the reviewed candidate via the isolated production worker under this
  bounded mandate, verify its exact artifact independently, review and safely
  promote the source/deployment. If authority expires first, inspect graph/receipt
  state and explicitly renew the bounded pilot; never silently bypass expiry.

## First bounded production code pilot completed

- Worker release 3d8feef7c4a6a37c4c723d9b5d9735dcf68f9579 qualified with 99 tests
  in 14.34s, including the actual graph-authored executor inside the restricted
  Docker worker. Worker release updated separately; control/Delta unchanged.
- Job contains only scope/work/attempt/invocation identities. Actual instruction
  is admitted to Mycelium, read by the claimant, and enforced by broker capability,
  mandate, lease and budget checks. Existing/uncertain attempts are not restarted.
- Production attempt attempt-cajon-pilot-v1 executed invocation-cajon-pilot-v1 and
  generated Receipt a269f0ed-2eea-46b0-be86-6e911c3706bd, entering review. One
  artifact action unit spent, zero reserved and no monetary spending. Worker has
  no network, repository mount, Docker socket or graph/provider credentials.
- Its exact candidate file matches the staged verified hash. Fresh Playwright CLI
  run against the actual production artifact passed all 12 scenarios. Linked
  TestRun qualification-cajon-production-pilot-v1 verifies the exact Receipt hash.
- Delegated source-promotion Decision guards the before Git blob and after file
  hash. GitHub master had advanced from the server copy but its app blob was
  identical to the tested base. One-file PR #1 merged as
  9f694ee4d544927b7df109d6f2f5c739ec78ab0d in Seedforth/cajon-sensei.
- Server fast-forward did not complete. It has pre-existing operational edits;
  those were preserved. Only app/index.html was atomically replaced after two
  before-image checks, preserving ownership/mode and retaining root-private backup.
  After hash verified dad62bbc229af2cb827326608660bb23ef64381caa7a48909cddc000ffc53a85.
  Git HEAD was deliberately not rewritten; public hosting is not yet verified.
- Review transitioned wi-cajon-partial-loop-credit to done/version 5 and recorded
  one verified accepted_artifact ProgressEvent. Review is explicitly owner-delegated
  operator action, not personal owner acceptance. The scope is held again.
- Created held follow-up wi-cajon-checkout-reconcile to preserve operational edits
  while restoring a coherent source checkout/release and checking hosting state.
  Evidence summary: evidence/cajon-production-pilot-20260906.json.
- This establishes a real bounded code-fix loop. It does not establish generalized
  model planning, continuous useful autonomy, other product outcomes, secure public
  MCP, full human UX, Graphify, safe portfolio archival or unattended soak success.

## Selected source-file sensing deployed

- Control component 5bda38cd2a95693e84ac22a1f9a70af875a803e6 is live as of
  2026-09-06T16:38:58Z. Main Delta remains 1770e7c; worker remains 3d8feef.
  Immutable-release suite passed 107 tests in 14.60s, including the real isolated
  Docker executor and graph reducers. JUnit SHA-256
  eaf32534a6ff780f6ee013ce6e841b240de0b07d53c73404897b7490fa5020e0
  is admitted as a ReleaseQualification linked to W21; no product progress credit.
- New graph-authored record-code-observation reducer and three registered streams
  retain event time, ingestion time, exact committed/working hashes, repository and
  adapter revisions, coverage and latest successful evidence. Late events, duplicate
  IDs, conflicts, revocation, stale/degraded reads and absent paths are tested.
- Sensor parent retains graph credentials, while file/Git probes run as project
  users without inherited environment, extra groups or descriptors. Probes refuse
  symlinks, unsupported files, oversized content and unstable reads. Effective and
  ambient capabilities are checked to be zero in the child. No source contents or
  environment values are stored in observations. This does not fence legacy writers.
- Initial service deployment reported collection_failed (no invented fresh state).
  Hardened transient-service diagnosis established that the parent lacked effective
  CAP_SETUID. Explicit ambient identity-switch capabilities fixed the parent; child
  privilege checks and an actual hardened service probe passed. Failed observations
  remain in history; successful observations now supersede them in the projection.
- Actual gateway readback confirms Cajon app/index.html is diverged_from_commit:
  HEAD 2a518d957bb1fbd39b02a8dcbc3e1f2890630b93 and applied file hash
  dad62bbc229af2cb827326608660bb23ef64381caa7a48909cddc000ffc53a85.
  Flowing server HEAD is 54ced2fe429b90576d59f005e9d6ebf9d8d69a6a; both
  app/api/order/route.ts and app/api/verify/route.ts are missing there, although
  present in the previously inspected local source. Public Vercel state is not
  established by these server-file observations; no hosting failure is inferred.
- Timer runs every five minutes; freshness limit is fifteen minutes. Only these
  selected paths are covered, not full repository cleanliness or public hosting.
  Automatic repair, source incidents/escalation, retention policy and Graphify
  extraction remain incomplete. No portfolio or work permission changes occur.
- Updated board explicitly displays code drift, freshness and partial coverage.
  Playwright CLI 0.1.19 passed both synthetic-response regression (including mobile,
  escaping and race/denial cases) and real HTTP/Cypher disposable-graph journey with
  graph-reduced drift displayed. One early navigation failed because the fixture
  gateway was not ready; after readiness the full journey passed. No production
  credentials entered browser CLI traces. Test browser, gateway and tunnel stopped.
- Migration applied twice to restored production data; all 47 projects and scope
  holds preserved. Restored container stopped again, volume retained. Production
  checks confirm all 47 projects, all holds, completed Cajon work and existing
  Delta/control/broker/runtime-sensor services are intact.
- Continue the complete upgrade: reconcile source/hosting provenance, inventory and
  fence legacy writers/schedulers, close source failures through scoped incidents,
  qualify Graphify, deliver scoped remote MCP and the richer human experience,
  then broader bounded useful work, safe archival and unattended recovery tests.
  Do not keep expanding metadata-only fixtures as a substitute for these outcomes.

## Legacy scheduler census and exact fence

- Live inspection found six root cron jobs, including a duplicate heartbeat and
  the deep/long scripts explicitly forbidden by the platform legacy boundary.
  `/opt/delta` is not the canonical release symlink. Long-cycle source retains
  password command-line handling. All eight old opencode agents also have broad
  provider credential keys in their environments; values were never printed.
- Qualified release f81e8498dd1162917a9b086c1368b1ff359e9d6f: 111 tests passed
  in 16.34s. Graph Decision authorizes four exact hashes; external I/O adapter
  preserves the complete configuration, refuses changed state and comments only
  duplicate root heartbeat plus ungoverned root dream/deep/long execution.
- Applied and independently read back; graph observation verifies four fenced
  LegacySchedule records. Root-private before/after backup retained. Both source
  ingestion jobs, supported heartbeat, Delta, WhatsApp, control and broker remain.
  No services, projects, users, scripts, logs or customer data were deleted.
- Detailed evidence and backup hashes: writer-census-20260906.md. Release TestRun
  qualification:f81e8498dd1162917a9b086c1368b1ff359e9d6f:f5de57f5df56cb22e939e15cd42c96d92684accca1552e9c7c8b9f7accdedd8e
  informs W21. Runtime release pointers unchanged (control5bda38c, worker3d8feef,
  main1770e7c); only the reviewed cron configuration and additive graph records changed.
- Held cadences still require governed replacements. Application schedule/nudge
  loops and legacy credential distribution remain unfenced. Wildcard Neo4j/VNC/
  webhook listener bindings require exposure checks and hardening. This is concrete
  risk reduction, not complete writer isolation or useful autonomous readiness.

## Internal graph/browser ingress guard deployed

- External IPv4 probes confirmed public reachability of Neo4j 7474/7687 and
  noVNC6083 before the change. All now explicitly refuse connections; SSH22 still
  connects and SSH-tunneled Neo4j HTTP returns200. Local graph/port access, all47
  projects, scope holds and existing service liveness are preserved.
- Security component afcc87be9b899b66b874d6410899401aaa429dc1 is deployed via
  security-current. Approved graph NetworkPolicy has a root-private offline kernel
  projection. IPv4/IPv6 INPUT and DOCKER-USER rules target only eth0 and three ports.
  Docker now requires the guard before startup. No Docker/service restart or shared
  firewall flush occurred. Root-private before-rule snapshots are retained.
- Immutable-release suite:116passed in18.65s, including real dual-stack namespace
  forwarding/denial/private-access tests. Hardened isolated systemd test also passed.
  JUnit8f85bd70062354fe9a7750eb944cd265da11211bfdd35ee7c36f1b09e85ec33f
  admitted as ReleaseQualification informing W21. Reapplication leaves exactly8
  guard rules across both families. Temporary namespaces/listeners cleaned up.
- Detailed evidence, recovery cautions and SSH access: network-guard-20260906.md.
  External IPv6 probe, full reboot/Docker restart/UFW reload drills and loopback
  Docker port bindings remain open. This does not isolate legacy local writers.
- Retained noVNC HTTP fails locally and through SSH; configured web root is absent.
  Prior application working state was not established, and noVNC was not modified.
  Do not confuse TCP/service liveness with a usable browser interface.
- Continue toward scoped remote MCP and full human UX, while completing legacy
  dispatch/credential migration, governed cadence replacement, Graphify, second
  useful product pilot, archival and unattended qualification. The entire goal
  remains incomplete; this security milestone is not a substitute for that scope.

## MCP boundary and durable conversation intake

- Control release2aed97e3ced22735f8281d24d6c866daeba044c1 is live, deployed
  2026-09-06T17:12:01Z. Main1770e7c, worker3d8feef and securityafcc87b unchanged.
  Shared Boundary now accepts bounded scoped graph reads and private durable
  conversation admission/readback. Owner has conversation-only grants for the
  three existing scopes, with no new execution/spend/model authority.
- Official MCP SDK2.1.1 adapter uses the same boundary after independent token
  verification. Four tools and a schema resource provide scoped metadata, current
  work, direction intake and conversation recovery. Qualified dependencies are
  pinned separately from the running Delta environment. SDK is installed only in
  test environments so far; no public or persistent production MCP server exists.
- Conversation keys are originator/scope-bound. Graph reducers serialize message
  sequence and idempotence, reject changed intent on replay, exclude other people,
  and store direction as uninterpreted content. Intake returns queued/not_started
  and explicitly states the governed Delta processor is not yet qualified. It does
  not fabricate an answer, WorkItem, Invocation, spend or progress.
- Actual official SDK client over TCP HTTP passed discovery/401 metadata, Origin
  rejection, graph/work reads, cross-scope denial, durable reconnect, graph-grant
  revocation and credential removal. Separate graph tests passed concurrent
  admission, request collision, cross-person privacy and hostile text containment.
  Initial SDK test exposed unstructured return typing; explicit typed structured
  output fixed it. No tests use real provider or owner credentials.
- Immutable release:123passed in26.45s. Qualification JUnit hash
  57b383b37bc541b66233dec8023792f185f9ff8edfe7e19c03a68b0396aa06e2
  is recorded in live Mycelium against W21. Playwright CLI control-board regression
  also passed after the shared-boundary change. Browser and fixture server stopped.
- Migration applied twice to the restored production graph with zero prior nodes
  carrying the new conversation labels. All47 projects and scope holds preserved.
  Live migration and authenticated HTTP readback returned30 bounded metadata rows
  per existing scope. No synthetic conversation was left queued in production.
  Restore container stopped again; data volume retained.
- The digest-file MCP verifier is a private qualification/enrollment adapter, not
  an OAuth authorization server. Public login/consent, PKCE/client registration,
  refresh/narrowed scopes, TLS, abuse limits, actual desktop/mobile agent trials
  and the originator-bound Delta processor are still required. Do not publish this
  adapter with a fictitious issuer or shared administrator credential as a shortcut.
- Continue by completing actual remote identity/access and the governed conversation
  processor, then integrating the richer board/Charlie experience with useful
  autonomous work. Legacy credential/writer isolation, Graphify, Flowing pilot,
  portfolio archival, recovery and unattended qualification remain in the full goal.

## Public TLS with closed application ingress

- Public https://185.192.96.100 now has a trusted Let's Encrypt IP certificate.
  Certificate expiry2026-09-13T08:21:27Z, SHA256
  100602d53854e1c4687981e6136cec6e378b12b8d8d01b5cb8f504ae391717d5.
  Application routes deliberately return503. HTTP serves only ACME challenges,
  foreign Host headers return421, and internal graph/browser ports remain refused.
  This is not a working public MCP or human control interface yet.
- Isolated Certbot5.4 installation with exact dependency lock avoids the broken
  system Certbot2.9/OpenSSL environment. Staging and production issuance passed.
  Certificates/account keys remain root-private under shared/acme-* and are not
  stored in the graph/repo. The existing system certbot.timer is unrelated and
  cannot be relied on to renew this custom certificate directory.
- Source release2fb1a5fc023a4edb4ca9aa0014ffd59259ac5843 supplies ingress and renewal
  service. No Delta/control/worker/security component source pointer changed.
  Nginx reloaded, not restarted. Only labeled443 firewall allowance added.
  seedforth-tls-renew.timer enabled, checks every six hours with systemd jitter.
- Qualification exposed and fixed two failures: Certbot's extra random sleep
  could exceed the service timeout, and nginx validation needed narrowly writable
  /run/nginx.pid. More importantly, Certbot returnedzero despite a failed deploy
  hook. Validation and reload now use mandatory ExecStartPost steps so systemd
  observes failure. First sleeping dry run was cancelled, second issued staging
  successfully but failed its hook, third passed full sandboxed webroot issuance
  and reload in11.085s. No production renewal has yet elapsed or been forced.
- External read-only suite14passed in5.24s, JUnit SHA256
  4cb15978c9143bbd63543e19cc703b5fd5ce100834a248fdae825054ff2444f1.
  Playwright CLI Chromium verified TLS without ignoring certificate errors, the
  closed response, no cookie and390px layout. Browser closed. This only tests
  transport/closed ingress, not a completed application UX. Existing services
  and sensor timers remain active. Reboot/publicIPv6/recurring expiry sensing are
  not qualified. Public authenticated access still requires real OAuth and consent.
- Next: build durable scoped identity/login/consent and real authorization-server
  behavior, qualify all human paths with Playwright, then enable narrow ingress
  routes. Continue the governed Delta processor and full remaining upgrade scope.

## Durable OAuth provider and actual transport qualification

- Source c38bb809fde4f207246f20b5f748e168ba677928 implements the OAuth provider,
  protocol routes and graph-native current identity-scope read. The credential
  store is private SQLite external I/O, containing digests of opaque codes/tokens,
  not a competing task/permission graph. Issuer/resource binding persists across
  restart. Grant authority remains Mycelium and is rechecked at token use.
- Single-use authorization codes, transactional refresh rotation, absolute family
  expiry, replay-triggered family revocation, explicit resource checks, S256 PKCE,
  callback validation, client-bound revocation, narrowed project selection and
  bounded registration/body sizes are implemented. Public PKCE clients only are
  advertised; no unsupported confidential-client or metadata-fetch claims.
- Tests exposed and corrected SDK resource enforcement omissions, public-client
  revocation validation, inaccurate supported-auth-method metadata, canonical root
  issuer formatting and frozen-error rollback handling. External calls are moved
  off the event loop. Graph outage fails closed; revocation can still reduce access.
- Ten provider/HTTP tests and one actual TCP HTTP OAuth→official MCP SDK→disposable
  graph journey passed. The latter issued credentials, read scoped work, queued
  direction without inventing execution, refreshed/reconnected, rejected the old
  token and foreign scope, then denied requests after actual graph-grant revocation.
  Internal synthetic human consent was explicitly used; no public bypass exists.
- Immutable release qualification:134passed in24.02s, no skipped tests, one SDK
  deprecation warning. JUnit hash28f5746cd337e01f48d564ba48c7dcb440f3d643c8adaefa7c4949c06cde0b19
  admitted in live Mycelium as a ReleaseQualification informingW21. Temporary
  transport server and namespace fixtures cleaned up. Live read confirmed only
  existing owner/sensor read identities and retained service/timer health.
- This release is tested source, not a production OAuth deployment. Current live
  control2aed97e, worker3d8feef, securityafcc87b and main1770e7c unchanged. Public
  application ingress remains503. No human interface was added by this provider
  slice, so its tests do not count as Playwright login/consent acceptance.
- Immediate next work: real enrollment/login/session/consent/recovery surface and
  abuse boundaries, tested with Playwright, then scoped public routing and client
  trials. Continue originator-bound Delta processing, legacy credential isolation,
  Graphify/full sensing, richer board/Charlie, Flowing useful autonomy, archival,
  recovery and unattended qualification. Entire goal remains incomplete.
