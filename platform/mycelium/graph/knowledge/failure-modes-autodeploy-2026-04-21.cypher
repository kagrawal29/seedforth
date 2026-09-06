// @node_id: knowledge-failure-modes-autodeploy-2026-04-21
// @label: Autodeploy failure modes discovered 2026-04-21
// @kind: knowledge
// @description: FailureMode + Learning nodes capturing the seven-layer autodeploy bug chain debugged on 2026-04-21. Reuses the :FailureMode schema from failure-modes.cypher. Surface via `mycelium ask "autodeploy fails"`.
// ============================================================================
// Session arc: mycelium-autodeploy-{dev,prod} had been red for ~17 hours.
// Each layer was masking the next. Recording so the next time the graph
// sees "HTTP Error 429" or "fork/exec resource temporarily unavailable"
// in a trace, it can surface the right fix within one hop.
// ============================================================================

// ---- FailureMode 1: fork-bomb recursion --------------------------------------
MERGE (f:FailureMode {node_id: 'failure-autodeploy-fork-bomb-recursion'})
SET f.label            = 'Autodeploy fork-bomb: mycelium binary recurses into its own dev shim',
    f.symptom_pattern  = 'fork/exec .*mycelium-dev.*resource temporarily unavailable|TasksMax',
    f.symptom_example  = 'mycelium-dev[PID]: mycelium: failed to invoke mycelium-dev: fork/exec /usr/local/bin/mycelium-dev: resource temporarily unavailable',
    f.root_cause       = 'Go binary shellOut → /usr/local/bin/mycelium-dev wrapper → exec ./mycelium (bash shim) → bash shim detects global mycelium binary on PATH → execs Go binary again → shellOut again. Repeats until systemd TasksMax cap (18690) exhausts fork().',
    f.fix_command      = 'Wrapper must exec ./mycelium-dev (the 15KB bash write-path script), not ./mycelium (the bash dispatcher). Go binary guard added in cmd/maverick/main.go (MAVERICK_SHELLOUT_DEPTH) as defense in depth.',
    f.fix_explanation  = 'Two-layer fix: binary refuses recursion (PR #43), and wrapper targets the correct bash entry. Either alone would surface a clear error; both together make the system safe.',
    f.affected_os      = 'linux-systemd',
    f.related_issue    = 'kagrawal29/mycelium#40',
    f.first_seen       = datetime('2026-04-21T07:25:00Z'),
    f.resolved_at      = datetime('2026-04-21T09:15:00Z'),
    f.updated_at       = datetime();

// ---- FailureMode 2: wrapper's NEO4J_PASS clobbered by target case ------------
MERGE (f:FailureMode {node_id: 'failure-autodeploy-neo4j-pass-clobber'})
SET f.label            = 'Bootstrap 401 → 429: mycelium-dev script overwrites caller NEO4J_PASS with team read-only pass',
    f.symptom_pattern  = 'HTTP Error 401: Unauthorized.*HTTP Error 429: Too Many Requests|0 Protocols bootstrapped',
    f.symptom_example  = 'ERROR: protocol-adopt-node: HTTP Error 401: Unauthorized\\nERROR: protocol-amortization-recount: HTTP Error 429: Too Many Requests\\n... 0 Protocols bootstrapped.',
    f.root_cause       = 'mycelium-dev bash script case "$target" unconditionally reassigns NEO4J_PASS=${MYCELIUM_{TARGET}_PASS:-localtest12}. Wrapper exports NEO4J_PASS with admin-write creds; script clobbers it with the read-only team pass from team-credentials.env. First MERGE returns 401; Neo4j auth rate limiter upgrades subsequent attempts to 429.',
    f.fix_command      = 'Change case block to precedence: NEO4J_PASS="${NEO4J_PASS:-${MYCELIUM_{TARGET}_PASS:-localtest12}}". Respect caller.',
    f.fix_explanation  = 'Caller (e.g. autodeploy wrapper) knows which password role it needs; script should not assume.',
    f.affected_os      = 'all',
    f.related_issue    = 'kagrawal29/mycelium#44',
    f.first_seen       = datetime('2026-04-20T15:44:00Z'),
    f.resolved_at      = datetime('2026-04-21T09:45:00Z'),
    f.updated_at       = datetime();

// ---- FailureMode 3: Neo4j auth rate-limiter masks real error ----------------
MERGE (f:FailureMode {node_id: 'failure-neo4j-auth-rate-limiter-masks-401'})
SET f.label            = 'Neo4j 2026+ auth lockout: repeated 401s morph into 429 "Too Many Requests"',
    f.symptom_pattern  = 'First HTTP request 401, subsequent identical requests 429',
    f.symptom_example  = 'curl #1 → 401 Unauthorized; curl #2..N within 5s → 429 Too Many Requests (same credentials, same endpoint)',
    f.root_cause       = 'Neo4j brute-force auth guard locks failing credentials for ~5s. Scripts that fire many MERGE requests in quick succession with a wrong password see only the first as "wrong" — the rest as "rate-limited" — which sends debuggers chasing a non-existent rate-limit config.',
    f.fix_command      = 'When seeing 429 from Neo4j HTTP, FIRST probe with one isolated curl + 5s pause + one more curl. If first is 401 and second is 200-or-auth-valid-code → creds are wrong. Do NOT hunt for rate-limit configs; there are none by default.',
    f.fix_explanation  = 'Saved 45 minutes of chasing ghost rate-limit knobs. Diagnostic heuristic: 429 with Neo4j ≈ auth lockout in 90% of cases.',
    f.affected_os      = 'all',
    f.first_seen       = datetime('2026-04-21T09:10:00Z'),
    f.updated_at       = datetime();

// ---- FailureMode 4: set-initial-password is no-op on initialized DB ----------
MERGE (f:FailureMode {node_id: 'failure-neo4j-set-initial-password-noop'})
SET f.label            = 'neo4j-admin dbms set-initial-password silently no-ops after first start',
    f.symptom_pattern  = 'Password rotation appears to succeed, but login still fails',
    f.symptom_example  = 'neo4j-admin dbms set-initial-password NEW → "Changed password for user" → login with NEW → 401',
    f.root_cause       = 'set-initial-password only takes effect before the database is first started. Warning: "this change will only take effect if performed before the database is started for the first time" is literal, not boilerplate.',
    f.fix_command      = 'Rotate via: (1) stop neo4j, (2) add dbms.security.auth_enabled=false to conf, (3) start neo4j, (4) curl ALTER USER neo4j SET PASSWORD \"NEW\" SET PASSWORD CHANGE NOT REQUIRED against /db/system/tx/commit, (5) stop, (6) remove the auth_enabled=false line, (7) start.',
    f.fix_explanation  = 'Auth-disable window is ~10 seconds of exposure. Acceptable on localhost-bound Neo4j; keep bolt-proxy firewall-closed during the window on public hosts.',
    f.affected_os      = 'all',
    f.first_seen       = datetime('2026-04-21T09:30:00Z'),
    f.resolved_at      = datetime('2026-04-21T09:42:00Z'),
    f.updated_at       = datetime();

// ---- FailureMode 5: prod Neo4j HTTP listener unbound despite enabled=true ----
MERGE (f:FailureMode {node_id: 'failure-neo4j-http-listener-unbound'})
SET f.label            = 'server.http.enabled=true without server.http.listen_address → nothing binds',
    f.symptom_pattern  = 'curl http://localhost:7474 → Connection refused (or 000) while neo4j-server is active',
    f.symptom_example  = 'systemctl status neo4j → active; ss -tlnp | grep 7474 → empty',
    f.root_cause       = 'Neo4j 2026.03.1 does not default server.http.listen_address to 0.0.0.0:7474 or 127.0.0.1:7474 when only server.http.enabled=true is set. Must explicitly set listen_address.',
    f.fix_command      = 'echo server.http.listen_address=:7474 | sudo tee -a /etc/neo4j/neo4j.conf && sudo systemctl restart neo4j',
    f.fix_explanation  = 'Known behavior change from earlier Neo4j versions. Document in pulse-setup template.',
    f.affected_os      = 'linux-neo4j-2026+',
    f.first_seen       = datetime('2026-04-21T09:17:00Z'),
    f.resolved_at      = datetime('2026-04-21T09:47:00Z'),
    f.updated_at       = datetime();

// ---- FailureMode 6: legacy neo4j.service IS prod, don't mask it --------------
MERGE (f:FailureMode {node_id: 'failure-neo4j-unprefixed-is-prod'})
SET f.label            = 'Unprefixed neo4j.service on pulse is PROD, not legacy',
    f.symptom_pattern  = 'neo4j.service in failed state alongside neo4j-dev.service + neo4j-staging.service',
    f.symptom_example  = 'systemctl list-units | grep neo4j → neo4j.service failed; neo4j-dev active; neo4j-staging active',
    f.root_cause       = 'Pulse provisioning named prod as the unprefixed canonical "neo4j.service" (bolt :7687, http :7474). Appearance as "legacy" while prefixed variants exist is a naming inconsistency tracked in plan-v1.1-maverick Track E.',
    f.fix_command      = 'DO NOT mask. Restart instead: sudo systemctl reset-failed neo4j && sudo systemctl start neo4j',
    f.fix_explanation  = 'plan-v1.1-maverick.md:298 documents the intent to rename neo4j.service → neo4j-prod.service. Don\\u0027t kill prod thinking it is a stale legacy unit.',
    f.affected_os      = 'pulse-server',
    f.related_issue    = 'kagrawal29/mycelium#41',
    f.first_seen       = datetime('2026-04-21T08:00:00Z'),
    f.resolved_at      = datetime('2026-04-21T08:20:00Z'),
    f.updated_at       = datetime();

// ---- FailureMode 7: no-swap + 3-JVM prod = OOM kill on spike -----------------
MERGE (f:FailureMode {node_id: 'failure-pulse-oom-no-swap'})
SET f.label            = 'Three native Neo4j JVMs on 15GB pulse-server without swap → OOM kill on spike',
    f.symptom_pattern  = 'neo4j.service Failed with result oom-kill, systemd Consumed N seconds CPU time',
    f.symptom_example  = 'neo4j.service: A process of this unit has been killed by the OOM killer. Failed with result oom-kill.',
    f.root_cause       = '3×(1G heap + 512M pagecache + JVM overhead) ≈ 6G warm + OS + qdrant + docker services. A heavy op (ingest, dream over large neighborhood) spikes a JVM several GB past heap; kernel picks a victim. No swap means kill-on-spike not slow-on-spike.',
    f.fix_command      = '(1) Add 8G swap: fallocate -l 8G /swapfile; mkswap /swapfile; swapon /swapfile. (2) Add Restart=on-failure + RestartSec=10s to each neo4j-*.service. (3) Tune staging heap down to 512M.',
    f.fix_explanation  = 'Parked as project_pulse_oom_risk — not yet applied. Highest-severity latent risk.',
    f.affected_os      = 'pulse-server',
    f.first_seen       = datetime('2026-04-20T15:44:00Z'),
    f.updated_at       = datetime();

// ---- Learning: what worked (so future sessions don't rediscover) -------------
MERGE (l:Learning {node_id: 'learning-autodeploy-debug-2026-04-21'})
SET l.label            = 'How to debug a silent autodeploy crashloop',
    l.session          = '2026-04-21',
    l.debug_heuristic  = [
      'Start at the service log tail, not the script. journalctl -u <service> -n 50 shows the actual failure symptom before you read code.',
      'When the symptom is "resource temporarily unavailable" or EAGAIN from fork, suspect recursion / fork-bomb first. Check CPU time consumed per failed attempt — 40+s burn with no progress is the signature.',
      'When the symptom is HTTP 429 from Neo4j, suspect auth lockout (failed creds) before looking for rate-limit configs. Neo4j has no default rate limiter — the lockout is the rate limiter.',
      'When a wrapper calls an exec target, strace is overkill — just cat the wrapper. 90% of env/arg bugs are visible in 5 lines.',
      'Masking any systemd service on prod needs a provenance check first. Assume "legacy" = "prod with a bad name" until proven otherwise.'
    ],
    l.resolved_issues   = ['kagrawal29/mycelium#40', 'kagrawal29/mycelium#41', 'kagrawal29/mycelium#42', 'kagrawal29/mycelium#44'],
    l.prs_shipped       = ['kagrawal29/mycelium#43'],
    l.cascade_length    = 7,
    l.time_to_green     = 'P2H',
    l.updated_at        = datetime();

// ---- Edges ----------------------------------------------------------------
MATCH (fb:FailureMode {node_id: 'failure-autodeploy-fork-bomb-recursion'})
MATCH (pc:FailureMode {node_id: 'failure-autodeploy-neo4j-pass-clobber'})
MATCH (rl:FailureMode {node_id: 'failure-neo4j-auth-rate-limiter-masks-401'})
MATCH (sp:FailureMode {node_id: 'failure-neo4j-set-initial-password-noop'})
MATCH (hl:FailureMode {node_id: 'failure-neo4j-http-listener-unbound'})
MATCH (nl:FailureMode {node_id: 'failure-neo4j-unprefixed-is-prod'})
MATCH (oo:FailureMode {node_id: 'failure-pulse-oom-no-swap'})
MATCH (l :Learning    {node_id: 'learning-autodeploy-debug-2026-04-21'})
// Learning synthesizes all seven:
MERGE (l)-[:SYNTHESIZES]->(fb)
MERGE (l)-[:SYNTHESIZES]->(pc)
MERGE (l)-[:SYNTHESIZES]->(rl)
MERGE (l)-[:SYNTHESIZES]->(sp)
MERGE (l)-[:SYNTHESIZES]->(hl)
MERGE (l)-[:SYNTHESIZES]->(nl)
MERGE (l)-[:SYNTHESIZES]->(oo)
// Causal chain (fork-bomb masked clobber, clobber masked by rate-limiter, etc):
MERGE (fb)-[:MASKED]->(pc)
MERGE (pc)-[:MASKED]->(hl)
MERGE (rl)-[:MASKED]->(pc)
MERGE (sp)-[:AFFECTS_DIAGNOSIS_OF]->(pc)
MERGE (nl)-[:CAUSAL_ROOT_OF]->(oo);

RETURN
  'autodeploy-2026-04-21 findings recorded: 7 FailureModes + 1 Learning + causal edges' AS status;
