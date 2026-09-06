# Progress + Direction — The Compass Layer for the Agent Fleet

*Design for the layer that makes the SuperAgent steer instead of read. Built on top of
mycelium-os.md (heartbeat + compass), rhythm-and-immune.md (cadences), and the Sutradhaar
constitution (gates + energy model). The problem it solves: the fleet runs schedules on
autopilot with no definition of work, no lifecycle, and no direction.*

---

## 0. The Five Questions, Answered

| Question | Where it's answered |
|---|---|
| Which projects need work vs dormant/done? | Section A — lifecycle states + auto-transitions |
| What is "work"? What are markers of progress? | Section B — WorkItem anatomy + scored ProgressEvents |
| Why does work exist? Is it moving us right? | Section C — mandate → goals → direction score |
| How do we map direction? | Section C — EntityGoals + direction score formula |
| How does the SuperAgent orchestrate and navigate? | Section D — the Sense/Assess/Decide/Act/Learn loop |

---

## A. Project Lifecycle States

The registry today has `active` and `hibernated` — a process state, not a truth state. A
project can be `active` (process running) and simultaneously *done* (nothing real left to
do). Lifecycle is stored as `lifecycle_state` on the entity node, separate from the runtime
`status` used by Delta's resource manager. They interact: an entity in `complete` or
`stalled` should have its runtime throttled or hibernated.

### A1. The states

| State | Meaning | Entry condition | Exit condition |
|---|---|---|---|
| `seed` | Created, no real work yet. SEED.md may or may not exist | Project provisioned, no ProgressEvent with weight ≥ 0.5 | First real ProgressEvent → `active` |
| `active` | Has meaningful work, producing progress | First real ProgressEvent (weight ≥ 0.5) | No real progress for `stall_days` → `stalled`; all goals closed → `maintenance` or `complete` |
| `stalled` | Was active, stopped producing real progress | No ProgressEvent with weight ≥ 0.5 in `stall_days` (default 7; 5 for paid earners, 14 for missions) | New real ProgressEvent → `active`; SuperAgent decides it's blocked on external reality → `dormant`; blocked > 30 days → `dormant` |
| `maintenance` | Goals met, light recurring upkeep remains (daily reports, monitoring, content pacing) | All EntityGoals `complete` but recurring WorkItems open | Recurring work closed for 30 days → `complete`; new goal seeded → `active` |
| `complete` | Goals met, no open work | All EntityGoals `complete`, no open WorkItems | Reopened by owner or SuperAgent → `active`; irrelevant 30 days → `archived` |
| `dormant` | Paused intentionally (waiting on a person, season, funding) | SuperAgent decision with reason, or stalled > 30 days | Wake trigger: user message, scheduled task, SuperAgent → `active` |
| `archived` | No longer relevant; structure preserved, agent stopped | SuperAgent decision; or `complete`/`dormant` untouched for 90 days | Never (append-only; resurrection is a fresh seed) |

The `stalled` → `complete` case is the gopal-website disease. The schedule only knows "tasks"
and "statuses", so nothing changes when a project is actually finished. The lifecycle layer
answers with evidence: goals closed, work items done, no real progress → the honest state is
`complete` (or `maintenance`), not `active`.

### A2. LifecycleEvent — every transition is audited

Every transition writes a `:LifecycleEvent` node:

```cypher
CREATE (le:LifecycleEvent {
  node_id: 'le-' + randomUUID(),
  entity: 'proj-gopal-website',
  from: 'active', to: 'complete',
  reason: 'All 6/7 tasks done; task 7 has no deliverable; site live and returned 200.',
  triggered_by: 'superagent',
  created_at: datetime()
})
MATCH (p:Project {node_id: 'proj-gopal-website'})
MERGE (le)-[:TRANSITIONS]->(p)
SET p.lifecycle_state = 'complete'
```

`triggered_by` is `auto-rule`, `superagent`, or `human`. The graph keeps the full arc:
seed → active → stalled → dormant → active → complete → archived is a readable history the
SuperAgent can navigate ("what happened to this entity and why").

### A3. Auto-transition rules (runnable every 24h, deep cycle)

```cypher
// Find active entities with no real progress in the last N days -> stalled
MATCH (p:Project {lifecycle_state: 'active'})
OPTIONAL MATCH (e:ProgressEvent)
WHERE e.entity = p.node_id AND e.weight >= 0.5
      AND e.created_at > datetime() - duration({days: coalesce(p.stall_days, 7)})
WITH p, max(e.created_at) AS last_real
WHERE last_real IS NULL
   OR last_real < datetime() - duration({days: coalesce(p.stall_days, 7)})
RETURN p.name, last_real,
       duration.between(coalesce(last_real, p.created_at), datetime()) AS stalled_since
```

Auto-rule transitions write a LifecycleEvent with `triggered_by: 'auto-rule'` and create an
`ActionProposal {type: 'ConfirmLifecycle'}` for SuperAgent ratification before the runtime
state (hibernation) is touched. Auto-rules only change the graph lifecycle — never runtime
`status` directly.

---

## B. Work Definition and Progress Markers

### B1. WorkItem anatomy — a task prompt is not work

A `:WorkItem` is only real when all four fields exist:

| Field | Rule | gopal-website task 7 in reality |
|---|---|---|
| `goal_ref` | MUST `:SERVES` an EntityGoal. No SERVES edge = not work, it's drift | absent |
| `deliverable` | a concrete artifact: code merged, post published, N leads, report written | **absent** → not a WorkItem |
| `success_criteria` | measurable; a judge can verify | absent |
| `progress_markers` | intermediate signals that EVIDENCE it | absent |

A correct WorkItem would look like:

```cypher
CREATE (w:WorkItem {
  node_id: 'wi-gopal-task7',
  entity: 'proj-gopal-website',
  goal_ref: 'gopal-goal-2',
  title: 'Final review pass',
  deliverable: 'Site reviewed against launch checklist',
  success_criteria: ['all 3 URLs return 200', 'checklist at docs/launch-checklist.md filled'],
  status: 'open', priority: 'low', created_at: datetime()
})
CREATE (w)-[:SERVES]->(:EntityGoal {node_id: 'gopal-goal-2'})
```

The real task 7 has none of these — it is a scheduled-task prompt, not a WorkItem.

A scheduled task that says only "continue working on X" fails the definition of work. The
schedule (`schedule.json` tasks) is the *invitation* to work; the WorkItem is the *contract*
of what work means. Delta's scheduler keeps firing, but the progress layer ignores
scheduled-task executions that never produce a WorkItem with a deliverable.

### B2. What is NOT work

- **Auto commits** — `auto: sync project work` is bookkeeping, not progress.
- **Empty outbox acks** — "done", "ok", "handled" without an artifact.
- **Scheduled task fires** — firing is not completing; only the produced deliverable counts.
- **Repeated reports** — a daily embed that restates yesterday is maintenance noise, scored low.
- **Busywork on stale state** — seedforthing's daily scan re-scoring the same 28 commenters
  while the launch posts "still not cycled" is activity without progress.

### B3. Data vs inference

**Data (measured, deterministic, cheap):**

| Signal | Source | Real-work test |
|---|---|---|
| Git commit | commit message + diff stat | message passes classifier (below); diff has non-config files |
| Outbox response | `delta-config/outbox/*.json` | substance score: length, embed, numbers, attached file, live URL |
| Artifact file | files created/changed outside `delta-config/` | exists, modified since last review |
| Deployment | Vercel/Railway URL | `curl` returns 200 |
| Schedule mutation | `schedule.json` | status flips + `last_run_notes` gains substance |
| User engagement | inbox/outbox logs | human responds to the work, not just ack |

**Inference (SuperAgent judgement, applied to borderline cases):**

- Read the artifact and judge: is this a real deliverable or placeholder?
- Read an outbox message and judge whether it moved the project.
- Read commit-message embeddings against a "real work" centroid when heuristics are ambiguous.
- Judge whether "no progress" is `stalled` (should be working) vs `complete` (nothing left)
  vs `dormant` (correctly paused). Only the SuperAgent can separate these three.

Inference is expensive; data is cheap. Design principle: **data scores everything, inference
adjudicates only where score is ambiguous** (0.3–0.7). This keeps the fleet honest at scale
without an LLM reading every commit.

### B4. Marker weights

Every progress signal becomes a `:ProgressEvent {marker, evidence, weight}`:

| Marker | Weight |
|---|---|
| Real commit (classified) | 1.0 |
| Outbox with artifact file attached | 0.8 |
| Outbox embed with "Shipped" field + numbers | 0.7 |
| Outbox plain text > 80 chars containing numbers | 0.5 |
| Deployment URL confirmed 200 | 1.2 |
| Schedule status change + substantive notes | 0.6 |
| New artifact file (non-config) | 0.4 |
| Auto commit / empty ack | 0.0 |

**Rule:** a project is *producing real progress* only when it accumulates ≥ 1.0 weight per
`stall_days` window from markers that `:EVIDENCE` a WorkItem. This single number drives
stall detection, direction scoring, and the SuperAgent's attention.

### B5. Detection Cypher**Commit classifier** (heuristic layer — run on ingest; `is_real` decided here):

```cypher
MATCH (c:Commit)
WHERE c.message =~ '(?i)^(auto|sync|ci|chore|wip|update|minor)\s*[:\-]?'
   OR size(c.message) < 12
SET c.is_real = false
```

```cypher
// Positive signal: known work-type prefixes + descriptive length
MATCH (c:Commit)
WHERE c.message =~ '(?i)^(build|feat|fix|design|learn|memory|report|deploy)[:\-]'
  AND size(c.message) > 25
SET c.is_real = true
```

Anything left unclassified (e.g. `9123434 ci: GitHub Actions deploy pipeline`) is bumped to
the SuperAgent's ambiguity queue once per day. A commit with `is_real = true` creates a
ProgressEvent:

```cypher
MATCH (c:Commit {is_real: true})
OPTIONAL MATCH (w:WorkItem {entity: c.repo})
CREATE (pe:ProgressEvent {
  node_id: 'pe-' + randomUUID(),
  entity: c.repo, marker: 'commit',
  evidence: c.sha + ' :: ' + c.message,
  weight: 1.0, created_at: datetime()
})
WITH pe, w WHERE w IS NOT NULL
MERGE (pe)-[:EVIDENCE]->(w)
```

**Stall detection** (drives `active` → `stalled`):

```cypher
MATCH (p:Project {lifecycle_state: 'active'})
OPTIONAL MATCH (pe:ProgressEvent)
WHERE pe.entity = p.node_id AND pe.weight >= 0.5
  AND pe.created_at > datetime() - duration({days: coalesce(p.stall_days, 7)})
WITH p, max(pe.created_at) AS last_real, count(pe) AS real_events
WHERE coalesce(last_real, datetime('1970-01-01')) < datetime() - duration({days: coalesce(p.stall_days, 7)})
RETURN p.name, real_events, last_real
ORDER BY last_real
```

---

## C. Direction Mapping

Lifecycle answers "is this entity alive?" Direction answers "is it alive *for the right
reason*?"

### C1. Mandate → Goals

The `SEED.md` is parsed (by the SuperAgent on seeding, or on demand) into one
`:EntityMandate` and 3–5 `:EntityGoal` nodes. Goals are the only legitimate parent for work.

```cypher
MERGE (m:EntityMandate {node_id: 'mandate-seedforthing'})
SET m.entity = 'seedforthing',
    m.north_star = 'Seedforth dreams into reality via the Seed Sprint',
    m.source = 'SEED.md', m.status = 'active'

MERGE (g:EntityGoal {node_id: 'goal-seedforthing-1'})
SET g.entity = 'seedforthing', g.goal = 'Stand up PPIS MVP',
    g.priority = 1, g.status = 'active',
    g.success_criteria = ['50 profiles scored', '10 Tier 1 targets', 'first Harvey briefs produced']
MERGE (g)-[:DERIVED_FROM]->(m)

MERGE (g2:EntityGoal {node_id: 'goal-seedforthing-2'})
SET g2.entity = 'seedforthing', g2.goal = 'Run daily Seed Sprint sessions',
    g2.priority = 2, g2.status = 'active',
    g2.success_criteria = ['1 pick/day across the two posts', 'session delivered', 'participant logged in CRM']
MERGE (g2)-[:DERIVED_FROM]->(m)
```

Work can only `:SERVES` a goal. A WorkItem with no SERVES edge is *drift by construction* —
this is how the graph makes the "why does this work exist?" question mechanical.

### C2. Direction score (0–100)

Computed nightly per entity, stored as `:DirectionScore`, diffed over time:

```
goal_progress   = active_goals_with_open_work / active_goals (0 when no active goals)
work_alignment  = open_work_with_SERVES / total_open_work    (0 when no open work)
activity_focus  = recent_ProgressEvents_with_SERVES / recent_total (0 when none)

direction_score = round(100 * (0.4*goal_progress + 0.3*work_alignment + 0.3*activity_focus))
```

```cypher
MATCH (p:Project {lifecycle_state: 'active'})
OPTIONAL MATCH (g:EntityGoal {status: 'active'})-[:SERVES]->(p)
WITH p, count(DISTINCT g) AS active_goals
OPTIONAL MATCH (g2:EntityGoal {status: 'active'})-[:SERVES]->(p)
      <-[:SERVES]-(w:WorkItem)
WHERE w.status IN ['open','in_progress']
WITH p, active_goals, count(DISTINCT g2) AS goals_with_work
OPTIONAL MATCH (w2:WorkItem)-[:SERVES]->(:EntityGoal)-[:SERVES]->(p)
WHERE w2.status IN ['open','in_progress']
WITH p, active_goals, goals_with_work, count(DISTINCT w2) AS aligned_open
OPTIONAL MATCH (allw:WorkItem {entity: p.node_id})
WHERE allw.status IN ['open','in_progress']
WITH p, active_goals, goals_with_work, aligned_open, count(DISTINCT allw) AS all_open
OPTIONAL MATCH (pe:ProgressEvent)
WHERE pe.entity = p.node_id AND pe.created_at > datetime() - duration('P7D')
  AND exists((pe)-[:EVIDENCE]->(:WorkItem)-[:SERVES]->(:EntityGoal)-[:SERVES]->(p))
WITH p, active_goals, goals_with_work, aligned_open, all_open, count(DISTINCT pe) AS focused_events
OPTIONAL MATCH (pe2:ProgressEvent)
WHERE pe2.entity = p.node_id AND pe2.created_at > datetime() - duration('P7D')
WITH p, active_goals, goals_with_work, aligned_open, all_open, focused_events, count(DISTINCT pe2) AS all_events
RETURN p.name,
       round(100 * (0.4 * (CASE WHEN active_goals > 0 THEN goals_with_work * 1.0 / active_goals ELSE 0 END)
                  + 0.3 * (CASE WHEN all_open > 0 THEN aligned_open * 1.0 / all_open ELSE 0 END)
                  + 0.3 * (CASE WHEN all_events > 0 THEN focused_events * 1.0 / all_events ELSE 0 END))) AS direction
```

### C3. Drift

`drift` flags when an entity's actual activity stops pointing at its own goals:

- An open WorkItem with no SERVES edge (dangling work).
- > 50% of recent ProgressEvents not `:EVIDENCE` any goal-linked WorkItem.
- Commits/outbox touching topic tags that match no EntityGoal's domain.

Drift is not a crime — it is often the first signal that the *mandate* is wrong and should
be rescoped (a Sutradhaar move), rather than that the agent is misbehaving. The direction
score trendline distinguishes: consistent low score = wrong mandate; sudden drop = drift.

---

## D. SuperAgent Steering Loop

This maps directly onto the constitution's rhythm (Sense → Model → Decide → Act → Integrate)
and adds the data sources. The SuperAgent is the only actor that writes `LifecycleEvent`
with `triggered_by: 'superagent'` and executes steering actions.

### D1. The loop

1. **Sense.** Read the fleet table (Section D3 query): lifecycle state, last real progress,
   direction score, open proposals, per entity.
2. **Assess.** Classify each entity into an intervention bucket:
   - `dead-weight` — active but no real progress → confirm stalled → hibernate runtime.
   - `finished` — goals closed, no open work → propose complete → stop the schedule.
   - `drifting` — low direction score with goal mismatch → rescope mandate or re-point work.
   - `thriving` — high score, aligned → leave alone, maybe scale up.
   - `waiting` — blocked on a human/external event → dormant, not stalled.
3. **Decide.** Pick the smallest move with the largest leverage (constitution: one honest
   increment). Prefer actions below the gate.
4. **Act.** Execute below-gate autonomously; queue above-gate for ratification (per
   constitution Gates). Always write a `:Decision` node with rationale.
5. **Learn.** After 7 days, revisit each action: did it produce real progress? Write a
   `:Knowledge {file_type: 'learning'}`. A "mark complete" that had to be reverted teaches
   the classifier the goal was wrong.

### D2. Steering actions and the gate

| Action | Trigger | Gate |
|---|---|---|
| `ConfirmLifecycle` (auto-rule ratification) | auto-rule fired | below — graph + runtime only |
| `WakeStalled` | entity dormant/stalled, blocker cleared | below |
| `ReprioritizeWork` | goal priority shift, blocked critical path | below |
| `MarkComplete` | goals closed, deliverable verified | below unless live customers/money |
| `RescopeMandate` | drift confirmed, new goal set | below (non-contractual) |
| `ArchiveEntity` | irrelevant, or complete 90 days | **above** if client/money/obligations |
| `SeedEntity` | gap + mandate from a demand signal | **above** (real people/money) |
| `MergeEntities` | > 50% goal overlap | **above** if obligations exist |

### D3. The fleet table the SuperAgent reads each cycle

```cypher
MATCH (p:Project)
OPTIONAL MATCH (pe:ProgressEvent)
WHERE pe.entity = p.node_id AND pe.weight >= 0.5
WITH p, max(pe.created_at) AS last_real
OPTIONAL MATCH (d:DirectionScore {entity: p.node_id})
WITH p, last_real, max(d.score) AS direction
OPTIONAL MATCH (ap:ActionProposal {entity: p.node_id, status: 'proposed'})
RETURN p.name, p.lifecycle_state, last_real, coalesce(direction, 0) AS direction,
       collect(ap.type) AS pending_proposals,
       CASE WHEN direction < 40 AND p.lifecycle_state = 'active' THEN 'DRIFTING'
            WHEN last_real < datetime() - duration({days: 7}) AND p.lifecycle_state = 'active' THEN 'DEAD-WEIGHT'
            ELSE 'OK' END AS bucket
ORDER BY bucket
```

---

## E. Graph Schema for Progress

### E1. Node types

```
(:EntityMandate {node_id, entity, north_star, source, status})
(:EntityGoal {node_id, entity, goal, priority, status, success_criteria: [..], due})
(:WorkItem {node_id, entity, goal_ref, title, deliverable, status,
            success_criteria: [..], priority, created_at})
(:ProgressEvent {node_id, entity, marker, evidence, weight, created_at})
(:DirectionScore {node_id, entity, score, aligned, drifting, created_at})
(:LifecycleEvent {node_id, entity, from, to, reason, triggered_by, created_at})
```

### E2. Edges

```
(:WorkItem)-[:SERVES]->(:EntityGoal)
(:EntityGoal)-[:SERVES]->(:Project|Organization)   // goals hang off the entity
(:EntityGoal)-[:DERIVED_FROM]->(:EntityMandate)
(:ProgressEvent)-[:EVIDENCE]->(:WorkItem)
(:ProgressEvent)-[:SUPPORTS]->(:EntityGoal)
(:LifecycleEvent)-[:TRANSITIONS]->(:Project|Organization)
(:Decision)-[:GOVERNS]->(:Project|Organization)    // existing edge, steering decisions
```

`SERVES` is the load-bearing edge: it is what makes drift detectable and direction
computable. A WorkItem without a `:SERVES` edge is, by definition, unaligned work. This one
edge converts "does this work matter?" from philosophy to query.

---

## F. Worked Examples

### F1. gopal-website — finished, never marked done

Symptom: 7 tasks, 6 done, task 7 "in_progress" forever. Commits are "auto: sync project
work". Runtime `active`.

**Sense query finds it:**

```cypher
MATCH (p:Project {name: 'gopal-website'})
OPTIONAL MATCH (pe:ProgressEvent)
WHERE pe.entity = p.node_id AND pe.weight >= 0.5
WITH p, max(pe.created_at) AS last_real
OPTIONAL MATCH (w:WorkItem {entity: p.node_id})
RETURN p.lifecycle_state, last_real,
       sum(CASE WHEN w.status = 'done' THEN 1 ELSE 0 END) AS done_items,
       sum(CASE WHEN w.status IN ('open','in_progress') THEN 1 ELSE 0 END) AS open_items
```

Result: `active`, last real progress 20+ days ago, 6 done, 1 open.

**Assess:** the open WorkItem has no `deliverable` and no `:SERVES` edge — it fails the
definition of work. The site's deploy URL returns 200; the launch goal's success criteria
are met. This is not stalled (nothing is blocked) — it is **finished**.

**Act (below gate):** the SuperAgent marks task 7 `blocked` (no deliverable defined), writes
the LifecycleEvent to `maintenance` (weekly report remains), and ratifies it via a
`ConfirmLifecycle` proposal:

```cypher
MATCH (w:WorkItem {node_id: 'wi-gopal-task7'})
SET w.status = 'blocked', w.reason = 'No deliverable or success criteria; site already complete'

CREATE (le:LifecycleEvent {
  node_id: 'le-' + randomUUID(), entity: 'proj-gopal-website',
  from: 'active', to: 'maintenance',
  reason: 'Goals met, 6/7 tasks done, task 7 not real work, site live (200).',
  triggered_by: 'superagent', created_at: datetime() })

CREATE (ap:ActionProposal {
  node_id: 'ap-' + randomUUID(), type: 'ConfirmLifecycle', entity: 'proj-gopal-website',
  rationale: 'Goals met; transition to maintenance with a weekly report only.',
  confidence: 0.92, status: 'proposed' })
```

**Outcome:** runtime hibernates the agent, schedule reduces to a weekly report, and the
"active" count drops by one. The 7th task stops consuming a "done project" label forever.

### F2. seedforthing — schedule alive, work dead, direction drifting

Symptom: two daily tasks (`seedforth-session-daily`, `public-track-daily`) fire every day.
`last_fired` is fresh (Jun 24–25). But `last_run_notes` say "Same 28 commenters (posts still
not cycled)" and commits are mostly "auto: sync project work". The pipeline is running
against a stale state — one participant picked weeks ago, same comment pool, no session
delivered.

**Sense:** the scheduler logs fire events (not ProgressEvents). Real markers (commit weight,
outbox artifact weight) sum to ~0 for the window → stall detector fires.

**Assess:** this is `waiting`, not `dead`. The blocker is external reality: the two launch
posts haven't cycled, and the SEED.md experiment is gated on Himanshu/Kshitiz. Also
`goal-seedforthing-2` (daily sessions) is the goal that can't move; `goal-seedforthing-1`
(PPIS MVP) is still legitimately active.

**Direction:** work_alignment is high (most WorkItems serve PPIS/session goals) but
goal_progress on goal-2 is 0 and activity_focus is low because daily fires produce no
goal-evidence. DirectionScore ≈ 30 → drift flag: the *schedule* and the *mandate* have
decoupled.

**Act (below gate):** the SuperAgent proposes `Dormant` for the session pipeline with reason
"blocked on post cycling", keeps PPIS as `active`, and creates a single maintenance WorkItem:
"weekly review, not daily fires". It writes a `:Learning`:

```cypher
CREATE (k:Knowledge {
  node_id: 'knowledge-' + randomUUID(),
  file_type: 'learning', scope: 'seedforthing', visibility: 'fleet',
  label: 'Daily schedule against stale state is not progress',
  content: 'seedforthing fired 2 daily tasks for 3 weeks on a static comment pool.
            Rule learned: scheduled-task fires without produced artifacts score 0.
            Blockers on humans -> dormant, not active.',
  produced_by: 'subagent-delta-hub', created_at: datetime() })
```

**Outcome:** the fleet stops burning compute on an unblocked pipeline, the SuperAgent
learns the pattern, and the direction model now treats "fresh schedule, stale reality" as a
`dormant` signal for any future entity.

---

## G. Implementation Phases

**Phase 1 — Progress markers (data layer, week 1-2).**
- `:Commit.is_real` classification (heuristic regex + length; ambiguity queue for the
  SuperAgent).
- Outbox substance scorer on Delta's existing outbox watcher → `:ProgressEvent`.
- Artifact + deployment detectors (file mtimes outside `delta-config`, `curl` 200).
- Wire into `_build_enriched_snapshot` in `delta/app.py` so `registry-snapshot.json`
  carries `last_real_progress` per project.
- Verify: gopal-website shows `last_real` ~30 days; seedforthing shows near-zero weighted
  progress despite fresh `last_fired`.

**Phase 2 — Lifecycle states + auto-transitions (state layer, week 3).**
- `lifecycle_state` property on Project nodes, seeded from current reality (audit pass).
- LifecycleEvent node + TRANSITIONS edge on every state change.
- Auto-rule protocol (`ConfirmLifecycle`) run on the deep cycle (24h).
- Runtime coupling: stalled/complete/dormant entities throttled or hibernated by the
  resource manager; `wake` re-activates on user message or schedule.

**Phase 3 — Entity goals + direction scores (direction layer, week 4-5).**
- SuperAgent parses SEED.md → EntityMandate + 3-5 EntityGoals with measurable criteria.
- WorkItem `:SERVES` enforcement: unaligned work gets a `drift` flag, not a silent pass.
- Nightly DirectionScore + trendline; observatory compass shows score by entity.

**Phase 4 — SuperAgent steering loop (orchestration, week 6-7).**
- Fleet table query (D3) injected into HUB_CLAUDE.md as the session-opener read.
- Steering actions execute below-gate; `RatificationRequest` for above-gate.
- Learn loop: 7-day review of each steering action → `:Learning` + model adjustment.

---

## H. Success Criteria

1. Every entity's `lifecycle_state` matches reality: no `active` entity has zero real
   progress for 7+ days; no finished project stays `active`.
2. No WorkItem lacks a `deliverable` and a `:SERVES` edge.
3. Every entity has 3-5 EntityGoals derived from its SEED.md; every open WorkItem serves one.
4. `DirectionScore` exists per entity, trends nightly, drift flagged before it becomes habit.
5. The SuperAgent opens each cycle with the fleet table (D3) and leaves a `:Decision` node
   for every steering action.
6. gopal-website is `complete`; seedforthing is split into `active` (PPIS) + `dormant`
   (session pipeline) — both visible in one query.

*The compass layer makes the graph answer the two questions no scheduler can: is this real,
and is it pointed the right way. Lifecycle is honesty about the past. Direction is honesty
about the future. The SuperAgent is the hand that turns the compass until it reads true.*
