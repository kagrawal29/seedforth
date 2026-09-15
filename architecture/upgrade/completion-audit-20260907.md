# SeedForth/Mycelium upgrade completion audit

Date: 2026-09-07  
Authority: owner-delegated autonomous upgrade execution  
Authoritative runtime record: [execution ledger](execution-ledger.md)

This is an evidence map, not a claim that the program is complete. `Verified`
means current evidence directly covers the requirement. `Partial` means a
meaningful slice is landed but the stated requirement is broader. `Open` means
the required evidence or implementation is still missing.

| Requirement | Current disposition | Evidence / remaining boundary |
|---|---|---|
| Mycelium is the graph-native source of truth for governed state | Verified for the upgraded control path | Authored Cypher operations, versioned transitions, grants, holds, work, attempts, receipts, review, and evidence are live. Legacy writers remain a migration boundary. |
| State reflects external reality through source sensing | Verified for deployed sources; partial for complete fleet | Runtime, code, Delta events, service health, and Graphify sensors are live. Source lineage and failure/last-success distinction are projected. |
| Graphify is integrated as bounded sensing | Verified | Platform and both active products have provenance-bound snapshots, bounded facts, coverage, failures, and live cadence. Raw model summaries cannot become authority. |
| Useful bounded autonomy exists | Verified for qualification candidates | Flowing and Cajon each have accepted, independently checked, unapplied candidate outcomes. No product deployment, spend, or external business effect is implied. |
| Independent evidence prevents self-approval | Verified | Worker completion enters review; independent artifact/browser checks and separate graph review are required. Secret-bearing Flowing artifact was rejected. |
| Delta and Charlie remain distinct and aligned | Partial | Delta internal delivery, untrusted-content handling, acknowledgements, and graph projection are qualified. Full Charlie channel/business deployment and broader identity matrix remain outside the current proof. |
| Secure scoped remote MCP is usable remotely | Verified for qualified public journey; partial for team rollout | Public TLS/OAuth/PKCE/MCP journey passed with temporary Cajon principal and foreign-scope denial. Durable teammate provisioning, client compatibility matrix, and broad rollout remain. |
| Human control board provides visibility and steering | Verified for shipped slice | Board is deployed, scoped, versioned, mobile-tested with Playwright CLI, and now displays service health. Richer timeline/diff/portfolio controls remain future scope. |
| Flowing Indian and Cajon Sensei are active | Verified | Live graph marks both active; work gates remain intentionally held after qualification. |
| Other product work is safely archived | Verified for current boundary | Live audit found 42 archived projects, only the two non-core products unarchived, and no obsolete product processes/schedules running. |
| Recovery, security, and continuity are tested | Partial | Neo4j and identity restore paths, credential rotation, secret rejection, isolation, revocation, and public ingress checks passed. A full whole-server disaster drill and complete provider-secret remediation remain. |
| Unattended operation is qualified honestly | Open | Recurring timers are live and post-recovery health is clean for roughly 20 minutes in the latest recorded interval. Day/week/month qualification has not elapsed; the maintenance-window incident remains retained and excluded. |

## Current gates

1. Keep recurring health, sensing, executor, Delta event/ack, and Graphify
   timers running; every qualification report must query both systemd and
   Mycelium.
2. Investigate/reproduce the earlier conversation-processor constraint failure
   before calling the delivery path long-soak clean.
3. Do not deploy the rejected Flowing credential-bearing candidate; remediate
   the provider secret through its project release path before any future
   checkout/notification work.
4. Complete longer unattended observation and a whole-server recovery drill
   before marking this audit complete.

The upgrade must not be marked complete merely because all services are alive,
the board renders, or a short soak passes.
