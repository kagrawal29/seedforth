# Delta/Mycelium — Remediation Plan
## Making the system honest before making it smart

*Based on the deep review (Aug 2 2026). The system is a well-built ingestion pipe
with a mostly-broken reasoning layer and an unimplemented decision layer. The
core problem: data integrity is broken, so every layer above it is untrustworthy.
This plan fixes the root causes first, then builds the missing intelligence on
solid ground.*

---

## The Verified Truth (why this is urgent)

| Finding | Impact | Evidence |
|---|---|---|
| **Classifier regex broken** (`=~` is full-string in Neo4j) | 605 auto-commits scored as real work. "producing=54.2" is noise | `'auto: x' =~ '^auto'` → False; 669/669 commits `is_real=true` |
| **9/16 heartbeat protocols fail** (decompose splits at `WITH`) | `:Report`=0, snapshots stale, hub sense-queries empty | Atoms end in `WITH`, invalid standalone |
| **Knowledge half empty** | connect/converge/decay/dream/route are no-ops | `:Knowledge`=0, `:Convergence`=0, `:Measurement`=0 |
| **Blockers/milestones dropped** | Strategic questions unanswerable | SEED.md "Pending" not ingested; 0 WorkItems, 0 due dates |
| **DirectionScore missing** | "thriving vs drifting" uncomputable | 0 nodes; no SERVES edges to compute it |
| **Steering unsafe/manual** | Registry race, duplicate watchers, not scheduled | Executor bypasses `hibernate()`, no lock, run manually |
| **Two message pipes** | Agents told one contract, runtime uses two | HTTP for messages, file-bridge for schedules |
| **Session loss on restart** | Agents forget conversation | `session_id` never persisted to registry |
| **No roles** | All project agents byte-identical | No subagents, no per-role models |

---

## Priority Tiers

```
P0 — Make the data HONEST (nothing above can be trusted until this)
P1 — Make the reasoning REAL (progress, lifecycle, direction on solid data)
P2 — Make the SuperAgent OPERATE (act on real proposals, persist, unify pipes)
P3 — Make it COMPLETE (knowledge graph, roles, Hebbian, observability)
```

---

## P0 — Data Integrity (the severed joints)

### P0.1 Fix the classifier regex [CRITICAL — 1 file]
**Root cause:** Neo4j `=~` has full-string `matches()` semantics. `'auto: x' =~ '^auto'` → False.
**Fix:** Use `STARTS WITH` / `CONTAINS` / `ENDS WITH`, which are prefix/substring (not full-match).
```cypher
// Corrected classification atom
WITH s,
  CASE
    WHEN toLower(s.message) STARTS WITH 'auto' THEN 0.0
    WHEN toLower(s.message) STARTS WITH 'sync' THEN 0.0
    WHEN toLower(s.message) STARTS WITH 'ci:' THEN 0.0
    WHEN toLower(s.message) STARTS WITH 'chore' THEN 0.0
    WHEN size(s.message) < 15 THEN 0.0
    WHEN toLower(s.message) CONTAINS 'feat:' OR toLower(s.message) CONTAINS 'fix:' OR
         toLower(s.message) CONTAINS 'build:' THEN 1.0
    ELSE 0.3
  END AS weight
```
**Also:** fix `graph-tool.py` and `progress-markers.py` (they have the same regex bug).
**Action:** update atom cypher, clear signals, re-scan, re-score. Verify: `auto` commits → weight 0, real commits → 1.0.

### P0.2 Repair the decomposed heartbeat atoms [CRITICAL]
**Root cause:** decompose-protocols.py splits at `WITH`/`MATCH` boundaries, producing atoms that END in `WITH` — invalid standalone statements. 9/16 protocols fail every run.
**Fix:** Never split a `WITH` clause. Split only at statement-complete boundaries (a `RETURN`, a full `MATCH...WHERE...RETURN`, or a clause that can stand alone). Simpler: split at blank-line boundaries in the source .cypher files (each source statement is a complete unit), not at clause boundaries.
**Also:** reconcile fat atoms vs step-children (remove the `-stepN` orphans; keep either fat OR fine, not both). Remove the 27 unreachable orphan atoms.
**Action:** rewrite decompose, clear `:Report`/`:Snapshot`, re-run heartbeat, verify 16/16 protocols OK + `:Report` nodes appear.

### P0.3 Fix scanner coverage + outcome signals [HIGH]
**Root cause:** ecosystem repos have `project_dir=None` → scanner falls back to non-existent paths → 0 signals → false `stalled`. Outbox files are deleted after Discord post → `OutboxSignal`=0. Deployment-200 check (weight 1.2) never implemented.
**Fix:**
- Scanner: resolve real repo paths for ecosystem projects (registry has them as git repos, or infer from `/opt`/`/root`).
- Outbox: persist scored signals BEFORE deletion (write `OutboxSignal` on delivery, not after).
- Add deployment check: for projects with `vercel.json`, `curl` the URL, emit `ProgressEvent` weight 1.2 on 200.
**Action:** update scanner, re-run, verify ecosystem projects stop being false-stalled and outbox signals appear.

### P0.4 Protocol-health invariant [HIGH]
**Root cause:** 15 invariants all "healthy" while 9 protocols fail silently. The immune system doesn't cover the execution layer.
**Fix:** Add `invariant-protocol-health` — checks every enabled Protocol has a `ProtocolRun` with `atoms_ok == atoms_total` in the last 24h. Failing → ActionProposal.
**Action:** add invariant + testcase. Verify it catches the broken protocols (before P0.2) then passes (after).

---

## P1 — Real Reasoning (on honest data)

### P1.1 Blocker/next-step/milestone model [HIGH — unlocks strategy]
**Gap:** SEED.md "Pending"/"Open Questions"/deadlines are dropped. No WorkItems, no due dates. SuperAgent can't answer "what's blocking X?" or "is it on time?"
**Build:**
- `(:Blocker {entity, type, description, since, resolved})` — from SEED.md "Pending" + agent reports
- `(:Milestone {entity, title, due, status, criteria})` — from SEED.md deadlines + goals
- `(:WorkItem {entity, goal_ref, title, deliverable, status, due})` — with `-[:SERVES]->(:EntityGoal)`
- Extend context-ingest LLM prompt to extract: pending/blockers, next-steps, deadlines, milestones
**Verify:** `MATCH (b:Blocker {entity:'heritage-diaries'})` returns Jitendra approval + Kissan deadline.

### P1.2 Goal lifecycle [HIGH]
**Gap:** all 41 goals `status='active'` forever. `goal_progress` uncomputable.
**Build:** Goal `active → in_progress → done` transitions. Tie to Milestone completion and WorkItem closure. An atom marks goals `done` when their success_criteria are met (measured or agent-confirmed).

### P1.3 DirectionScore [HIGH — the compass]
**Gap:** formula exists in docs, 0 nodes, uncomputable (no WorkItems/SERVES).
**Build once P1.1+P1.2 land:**
```cypher
direction = 0.4*goal_progress + 0.3*work_alignment + 0.3*activity_focus
```
Store `(:DirectionScore {entity, score, computed_at})`, trend nightly, flag `drift` when <40 and active.

### P1.4 Outcome signals (not just activity) [MEDIUM]
**Gap:** progress measures commits/files, not deals/revenue/leads.
**Build:** `(:Outcome {entity, metric, value, period})` — revenue, deals closed, response rate, followers. Sources: agent reports (parse outbox embeds with "Shipped"/numbers), manual SuperAgent judgment on borderline. Weight 1.2-2.0. This is what makes "thriving" mean something.

---

## P2 — SuperAgent Operates

### P2.1 Unify message pipe [CRITICAL for reliability]
**Gap:** HTTP for messages, file-bridge for schedules/reports/admin. Agents told one contract, runtime uses two. Session lost on restart.
**Decision:** HTTP is the primary pipe. Route schedules/reports/admin through `deliver_message` too (agent gets a prompt "Scheduled task: X" over HTTP, not a file). OR keep file-bridge for everything and drop HTTP. Pick one.
**Also:** persist `session_id` to registry on create; restore on boot. Add conversation logging to the HTTP path (write `_log_exchange` from `deliver_message`).
**Fix:** `peek`/`restart_hub` broken (call removed `capture_tmux_scrollback`), silence loop dead for opencode (set `last_inbox_time` in deliver_message).

### P2.2 Safe steering [HIGH]
**Gap:** executor writes registry directly, no lock, bypasses `hibernate()`, not scheduled.
**Fix:** steering calls `provisioner.hibernate()` (git_save + bridge shutdown + registry update), adds a registry lock, runs in the deep cycle cron (it IS in the deep cycle — verify it's actually scheduled). Add `invariant-steering-consistency` (no orphaned bridges).

### P2.3 Hub reads real graph [HIGH]
**Gap:** Hub's sense-queries return empty (`:Report`, `:Knowledge` all 0). ActionProposals never surfaced to Discord.
**Fix:** after P0.2 (reports work) and P0.3 (knowledge), the hub's existing CLAUDE.md queries work. Add a boot/cycle hook: on hub startup + every deep cycle, the steering executor posts a summary of proposals to the admin channel ("3 stalled, 1 needs ratification").

### P2.4 Persistent agents (DM routing) [MEDIUM]
**Gap:** `_route_dm_to_persistent`/`_auto_provision_personal_agent` are dead code. All DMs go to hub.
**Decision:** route DMs to hub always (current), OR restore persistent-agent routing. Pick based on product intent.

---

## P3 — Complete

### P3.1 Knowledge/Convergence ingestion
**Gap:** `:Knowledge`=0. Connect/converge/decay/dream/route (half the OS) are no-ops.
**Build:** agents write `:Knowledge {file_type:'decision|learning|pattern'}` via graph-tool (writes, not just reads). Context-ingest writes decisions as `:Knowledge`. Then connect/converge/decay/dream become real.

### P3.2 Role/subagent machinery
**Gap:** all agents identical. No subagents.
**Build:** provision subagent definitions in opencode.jsonc (explorer/general for each project); per-role model allocation (personal→deepseek-chat); `role` field on ProjectInfo; graph `:Subagent.role` updated on provision.

### P3.3 Hebbian strengthening
**Gap:** QueryTrace accumulates, never links to nodes, no strengthen/decay.
**Build:** graph-tool links traces to touched node_ids; a weekly atom strengthens fired paths / decays unused (adjust edge weights, not delete).

### P3.4 Observability
**Gap:** no spend/latency tracking.
**Build:** opencode stats via API per agent; DeepSeek spend via billing API; `:Metric` nodes in graph.

---

## Sequencing & Dependencies

```
P0.1 regex fix ───────────┐
P0.2 decompose repair ────┤→ data honest
P0.3 scanner coverage ────┤
P0.4 protocol invariant ──┘
        │
        ▼
P1.1 blockers/milestones ─┐
P1.2 goal lifecycle ──────┤→ reasoning real
P1.3 DirectionScore ──────┤
P1.4 outcome signals ─────┘
        │
        ▼
P2.1 unify pipe ──────────┐
P2.2 safe steering ───────┤→ SuperAgent operates
P2.3 hub reads graph ─────┤
P2.4 persistent agents ───┘
        │
        ▼
P3.1 knowledge ───────────┐
P3.2 roles ───────────────┤→ complete
P3.3 hebbian ─────────────┤
P3.4 observability ───────┘
```

## Effort Estimate

| Tier | Items | Effort |
|---|---|---|
| P0 | 4 | 1-2 days — small files, high leverage |
| P1 | 4 | 3-5 days — new models + ingestion |
| P2 | 4 | 2-3 days — runtime fixes |
| P3 | 4 | 3-5 days — new features |
| **Total** | 16 | **~2 weeks** |

## Success Criteria

1. `auto:` commits score 0; real commits score 1.0; FleetProgress is trustworthy
2. 16/16 heartbeat protocols OK; `:Report` populated; protocol-health invariant green
3. Ecosystem projects not false-stalled; outbox signals present; deployment-200 checks work
4. `MATCH (b:Blocker {entity:'heritage-diaries'})` returns Jitendra + Kissan
5. `DirectionScore` exists per active entity, trends nightly
6. One message pipe; sessions persist across restart; conversation logged
7. Steering runs scheduled, uses `hibernate()`, no registry races
8. Hub can answer: idea ✓, direction ✓, blockers ✓, next ✓, thriving (DirectionScore) ✓
