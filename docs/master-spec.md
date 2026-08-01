# SeedForth SuperAgent — Master Spec
## The Unified Intelligence Layer, End to End

*Consolidated from migration-to-opencode.md, mycelium-os.md, rhythm-and-immune.md,
progress-and-direction.md, system-health-redesign.md, and the live system audit (Aug 2026).*

---

## Part 0 — Where We Are (Honest)

### What works
- **21 agents** running as opencode serve + DeepSeek V4 Pro, supervisor-managed
- **Clean message pipe**: Discord → deliver_message → HTTP → opencode → callback
- **Hub (SuperAgent)** live on port 7700, fleet-aware
- **Rhythms** running: fast pulse (5m), heartbeat (30m), dream (4h), deep (24h), long (7d)
- **Immune system**: 15 invariants at 100% health, 100% test coverage, closed-loop detect→heal→verify→escalate
- **Graph-native protocols**: 16 heartbeat protocols stored as Protocol/CypherAtom nodes, executed by graph-runner
- **Neo4j helper**: 160x faster than cypher-shell (0.03s vs 5s per query)

### What's broken / missing
| Gap | Detail |
|---|---|
| **Per-project context not in graph** | SEED.md, decisions.md, tools, profiles, artifacts all trapped in files. Graph knows only `{name, status}` per project |
| **Traces broken (fixed)** | SessionTrace used cypher-shell (silently failed). Fixed to HTTP API |
| **Hebbian layer dead** | 0 Query nodes, 0 QueryTrace, fire_count stale. Agents' `graph` tool writes no traces |
| **Protocols not decomposed** | Heartbeat protocols are single fat atoms, not fine-grained executable chains |
| **No progress markers** | No WorkItem/ProgressEvent. Schedules run on autopilot |
| **No lifecycle** | active/hibernated only. gopal-website (finished) still "active" |
| **No direction** | No EntityGoal/mandate. SuperAgent reads state, doesn't steer |
| **SuperAgent doesn't act** | Creates ActionProposals but nothing consumes and executes them |

---

## Part 1 — Architecture: The Unified Intelligence Layer

```
                         Discord (user speaks to ONE Delta)
                                    │
                    ┌───────────────▼───────────────┐
                    │  SuperAgent (Hub, opencode)   │
                    │  Sense → Assess → Decide →    │
                    │  Act → Learn (steering loop)  │
                    └───────────────┬───────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
  ┌─────────────┐            ┌──────────────┐           ┌─────────────┐
  │  Project    │            │  Project     │           │  Project    │
  │  Agents     │            │  Agents      │           │  Agents     │
  │  (7 active) │            │  (isolated)  │           │  (isolated) │
  └──────┬──────┘            └──────┬───────┘           └──────┬──────┘
         │                          │                          │
         └────────────┬─────────────┴────────────┬─────────────┘
                      │                          │
                      ▼                          ▼
            ┌─────────────────┐          ┌─────────────────┐
            │   THE GRAPH     │          │   Runtime       │
            │   (Neo4j,       │          │   (supervisor,  │
            │   source of     │          │   DeepSeek,     │
            │   truth)        │          │   Discord)      │
            └─────────────────┘          └─────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
  ┌─────────┐   ┌──────────┐   ┌──────────┐
  │ Rhythms │   │ Immune   │   │ Progress │
  │ 5m/30m  │   │ System   │   │ +        │
  │ 4h/24h  │   │ (detect→ │   │ Direction│
  │ 7d      │   │ heal→    │   │ (compass)│
  │         │   │ verify)  │   │          │
  └─────────┘   └──────────┘   └──────────┘
```

**Core principle: the graph is the source of truth and the execution layer.**
Files are inputs (SEED.md) and artifacts (code, posts), but state, intent, progress,
and behavior live in the graph.

---

## Part 2 — The Per-Project Context Map (NEW)

Every project gets one graph-resident context model. This is the foundation — nothing
above it works without it.

### 2.1 What each project needs in the graph

```
EntityMandate {north_star, source: SEED.md}          ← the WHY (parsed from SEED.md)
  └─ EntityGoal ×3-5 {goal, priority, status,        ← the DIRECTION (measurable)
       success_criteria}
       └─ WorkItem {deliverable, success_criteria,   ← the WHAT (must SERVES a goal)
            status, priority}
            └─ ProgressEvent {marker, evidence,      ← the PROGRESS (weighted)
                 weight}
EntityProfile ×N {role, involvement}                  ← WHO (from SEED.md prose)
Tool ×N {name, purpose, status}                       ← WHAT'S BUILT (from tools/, configs)
Artifact ×N {type, path, url, status}                 ← WHAT'S PRODUCED (code, posts, reports)
Decision ×N {topic, choice, rationale}                ← MEMORY (from decisions.md, transcribed)
```

Edges: `WorkItem -[:SERVES]-> EntityGoal -[:SERVES]-> Project`,
`ProgressEvent -[:EVIDENCE]-> WorkItem`, `EntityGoal -[:DERIVED_FROM]-> EntityMandate`

### 2.2 Context ingestion (seeder)

A `context-ingest.py` that lifts file knowledge into graph nodes:
- Parse SEED.md → EntityMandate + EntityGoals (via SuperAgent LLM, then store)
- Parse `memory/decisions.md` → Decision/Knowledge nodes
- Scan `tools/` → Tool nodes
- Scan `opencode.jsonc` → configured tools/capabilities
- Scan project dir → Artifact nodes (git repos, data files, deployments)
- Run on seed, and on every lifecycle event (re-parse SEED.md)

### 2.3 The `SERVES` edge is load-bearing

A WorkItem with no `:SERVES` edge = drift by construction. This converts
"does this work matter?" from philosophy to a Cypher query.

---

## Part 3 — Traces + Hebbian Learning (NEW)

### 3.1 Every read leaves a trace

The `graph` tool (and any agent Cypher query) must write:
- `:Query {cypher_hash, text, fire_count}` — one per unique Cypher, fire_count++
- `:QueryTrace {agent, timestamp, touched_ids}` — per invocation, links to touched nodes
- On each run: `MERGE (q:Query {cypher_hash}) SET q.fire_count = coalesce(q.fire_count,0)+1`

This makes the graph learn what the fleet actually asks about. Frequently-asked
paths strengthen (Hebbian). Never-asked paths decay.

### 3.2 Atom-aware execution (trace cascade)

When an agent's query results include a CypherAtom or Protocol node, the agent can
execute it. That execution:
1. Creates a QueryTrace touching those nodes
2. Increments fire_count on the atom + touched nodes
3. The atom's FOLLOWS chain continues → deeper execution → more traces

This is the "fire together, wire together" cascade. Depth is unlimited by design
(FOLLOWS chains of any length).

### 3.3 What's needed (currently dead)

- `graph` tool wrapper that records Query + QueryTrace (use neo4j_helper, 0.03s)
- A rhythm that strengthens frequently-fired paths / decays unused ones
- Atom-aware prompt: agents told "query results may contain executable protocols; you may run them"

---

## Part 4 — Protocol Decomposition (NEW)

### 4.1 The problem

Heartbeat protocols are stored as single fat atoms. Mycelium's design calls for
fine-grained atoms chained via FOLLOWS — the graph as a real executable program layer.

### 4.2 Example: 02-connect decomposed

```
Current (1 fat atom):
  MATCH (st:SessionTrace) WHERE NOT exists(st.digested)
  MATCH (k:Knowledge {project: st.project})
  MERGE (st)-[:TOUCHES]->(k)
  SET st.digested = true

Decomposed (4 atoms):
  atom-connect-00: MATCH (st:SessionTrace) WHERE NOT exists(st.digested) WITH st
  atom-connect-01: MATCH (k:Knowledge {project: st.project}) WHERE k IS NOT NULL
  atom-connect-02: MERGE (st)-[:TOUCHES]->(k)
  atom-connect-03: SET st.digested = true
  00 →[FOLLOWS]→ 01 →[FOLLOWS]→ 02 →[FOLLOWS]→ 03
```

Each atom has a `semantic` description so the graph can explain its own reasoning.
The chain is a walk the graph (or an agent) can navigate and understand.

### 4.3 What to decompose

All 16 heartbeat/dream protocols, plus the immune system's heal actions.
Each becomes a 3-8 atom chain with semantic labels.

---

## Part 5 — Progress + Direction (from progress-and-direction.md)

### 5.1 Lifecycle states
`seed → active → stalled → maintenance → complete → archived`, plus `dormant`.
Separate from runtime `status`. Every transition writes a `:LifecycleEvent` (audited).
Auto-rules only flag; SuperAgent ratifies via `ConfirmLifecycle`.

### 5.2 Work definition
A WorkItem is real only with: `deliverable`, `success_criteria`, `:SERVES` edge.
Scheduled-task fires are invitations, not work. Auto-commits ("auto: sync") score 0.

### 5.3 Progress markers (weighted)
| Marker | Weight |
|---|---|
| Real commit (classified, not "auto:") | 1.0 |
| Deployment URL returns 200 | 1.2 |
| Outbox with artifact attached | 0.8 |
| Outbox embed with "Shipped" + numbers | 0.7 |
| New artifact file (non-config) | 0.4 |
| Auto-commit / empty ack | 0.0 |

A project produces progress only if it accumulates ≥1.0 weight per stall-window.

### 5.4 Direction score
`0.4·goal_progress + 0.3·work_alignment + 0.3·activity_focus`. Drift flagged when
>50% recent progress isn't goal-linked. Consistent low score = wrong mandate; sudden
drop = drift.

### 5.5 SuperAgent steering loop
Sense fleet table → Assess buckets (dead-weight/finished/drifting/thriving/waiting)
→ Decide smallest high-leverage move → Act below gate / propose above gate → Learn
(7-day review → :Learning node).

---

## Part 6 — Implementation Phases (Updated Sequence)

### Phase 1: Per-Project Context Ingestion (FOUNDATION — do first)
- [ ] `context-ingest.py`: parse SEED.md → EntityMandate + EntityGoals
- [ ] Transcribe `memory/decisions.md` → Decision/Knowledge nodes
- [ ] Scan `tools/` + `opencode.jsonc` → Tool nodes
- [ ] Scan project dir → Artifact nodes
- [ ] Seed all 7 active projects
- [ ] Verify: every project has mandate, goals, tools, artifacts in graph

### Phase 2: Trace + Hebbian Layer (every read leaves a trace)
- [ ] `graph` tool wrapper writes :Query + :QueryTrace + fire_count (fast HTTP API)
- [ ] SessionTrace confirmed flowing (already fixed)
- [ ] Hebbian protocol: strengthen fired paths, decay unused (weekly)
- [ ] Verify: query the fleet, watch Query nodes + fire_count grow

### Phase 3: Protocol Decomposition (graph as executable program)
- [ ] Decompose 16 heartbeat/dream protocols into 3-8 atom chains
- [ ] Each atom has semantic description
- [ ] Verify: graph-runner walks chains, executes in order, records ProtocolRun
- [ ] Verify: atom-aware cascade (query → find protocol → run → more traces)

### Phase 4: Progress Markers (data layer)
- [ ] Commit classifier (`is_real`) on ingest
- [ ] Outbox substance scorer → ProgressEvent
- [ ] Artifact + deployment detectors
- [ ] Wire into `_build_enriched_snapshot` in app.py
- [ ] Verify: gopal-website shows last_real ~30d; seedforthing near-zero

### Phase 5: Lifecycle + Direction (state layer)
- [ ] `lifecycle_state` on Project nodes, seeded from reality
- [ ] LifecycleEvent node + TRANSITIONS edge
- [ ] Auto-rule ConfirmLifecycle on deep cycle
- [ ] EntityGoal parsing + DirectionScore nightly
- [ ] Drift flag + WorkItem SERVES enforcement

### Phase 6: SuperAgent Steering (orchestration)
- [ ] Fleet table query injected into HUB_CLAUDE.md as session opener
- [ ] SuperAgent consumes ActionProposals, executes below-gate
- [ ] Learn loop: 7-day review → :Learning
- [ ] Verify: gopal-website → complete, seedforthing → split active/dormant

### Phase 7: Graph UI + NL Interface (human visibility)
- [ ] Web UI: force-directed graph viz + Cypher box + NL query
- [ ] Deploy on delta-server, expose

---

## Part 7 — Success Criteria

1. Every project has a complete context map in the graph (mandate, goals, tools, artifacts)
2. Every agent query leaves a Query + QueryTrace; fire_count grows; unused paths decay
3. Protocols are decomposed into semantic atom chains; the graph explains its own reasoning
4. Every entity's lifecycle matches reality — no finished project stays active
5. No WorkItem lacks a deliverable + SERVES edge
6. DirectionScore trends nightly; drift flagged early
7. SuperAgent opens each cycle with the fleet table and leaves a :Decision for every action
8. gopal-website → complete; seedforthing → active(PPIS) + dormant(session); visible in one query
9. Human can see + query the graph via the UI

---

*The compass layer makes the graph answer the two questions no scheduler can:
is this real, and is it pointed the right way. Lifecycle is honesty about the past.
Direction is honesty about the future. The SuperAgent is the hand that turns the
compass until it reads true.*
