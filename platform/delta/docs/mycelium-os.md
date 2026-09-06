# Mycelium OS — SeedForth Edition

## The Real-Time Operating System for the Agent Fleet

*Consolidated specification. Synthesized from OPERATING-SYSTEM.md, MYCELIUM.md, AGENTS.md (mycelium),
SEEDFORTH-SEED.md, CONSTITUTION.md (Sutradhaar), and migration-to-opencode.md, July 2026.*

---

## Preamble: Mycelium IS the Operating System

Mycelium is NOT a database that agents query. It is the operating system of the SeedForth agent
fleet. Every agent action, every Discord message, every commit, every schedule tick feeds into
the graph in real-time. The graph maintains itself via heartbeat protocols every 30 minutes. The
graph IS the current state of the entire fleet. Trajectories emerge from accumulated data.
Controls to steer the fleet are ActionProposals the graph produces for the SuperAgent to read,
decide, and execute.

This document specifies every protocol, every ingestion rule, every invariant, and every lever
concretely for the SeedForth fleet. It maps the mycelium OS concepts (designed for Qubit-Capital
with Claude Code traces, GitHub Issues, and competitive intelligence) to SeedForth equivalents
(agent messages, Discord tasks, internal fleet state).

---

## Part A: Operating Model

### A1. The Heartbeat (every 30 minutes)

Every 30 minutes, the graph fetches all enabled protocols and runs them in order. This is the
system's pulse: ingest external signals, digest them into the graph, excrete waste (expired
nodes, stale edges). 18 protocols execute in sequence for SeedForth:

**1. Wake** — Should the system process right now?
Check if any node has `created_at > last_pipeline_run`. If yes, there is new data to digest.
If no, the system can sleep until the next heartbeat tick. Prevents unnecessary processing
cycles when nothing has changed.

**2. Connect** — Wire unprocessed SessionTraces to the Knowledge they touch.
When an agent session trace mentions "SolveOS pipeline stalled", find Knowledge nodes sharing
tags with the session text (using tag overlap or semantic match). Wire them via TOUCHES edges.
The graph learns what agents are actively thinking about.

**3. Converge** — Detect when 2+ agents are independently working on the same graph region.
If the Hub agent and the SolveOS builder both have SessionTraces touching "pipeline bottleneck",
create a `:Convergence` node. This is the system's way of saying "these agents should share
context." The SuperAgent reads convergence nodes to decide whether to merge, reseed, or spawn
cross-project collaboration.

**4. Decay: Confidence** — Downgrade single-source knowledge.
If a `:Knowledge` node has confidence `high` or `medium` but only 1 evidence source (e.g., one
SessionTrace touched it), downgrade it to `low`. Single-source claims in the fleet don't get to
be confident. Forces the graph to be honest about what is corroborated.

**5. Decay: Demand** — Flag knowledge nobody is asking about.
Find `:Knowledge` nodes with `fire_count = 0`, no incoming TOUCHES edges from recent
SessionTraces, and no coupling events touching them. These are knowledge items that may have gone
stale. Not deleted — flagged with `needs_review: true` and `stale_since: <timestamp>`. The
system forgets gracefully.

**6. Decay: Edges** — Prune unused inferred edges.
Remove inferred edges (CONCEPTUALLY_RELATED_TO, INFERRED_SIMILAR, SEEMS_LIKE) where neither
endpoint has any recent activity (no SessionTrace, no QueryTrace, no TOUCHES in the last 7 days).
If the system guessed two Knowledge nodes are related but nobody ever queries or touches either
one, the guess gets pruned. Keeps the graph from filling with noise.

**7. Decay: TTL** — Time-to-live cleanup.
Transient signal nodes expire:
- CouplingEvents: 7 days
- SessionTraces: 2 days
- SessionHeartbeats: 2 days
- Commits: 14 days
- QueryTraces: 2 days
- AgentHealthSnapshots: 7 days
These are transient signals that informed the graph when fresh. After TTL, they are removed
(they have already informed the permanent nodes they touched).

**8. Dedup** — Remove duplicate edges.
Find and remove duplicate edges between the same pair of nodes with the same type. If two
`CONCEPTUALLY_RELATED_TO` edges exist between Knowledge A and Knowledge B, delete one. Prevents
edge accumulation from repeated protocol runs. Scope-protected: structural edges
(`BELONGS_TO`, `ASSIGNED_TO`, `DECAY_PROTECTED`) are excluded from dedup.

**9. Heal: Orphans** — Delete zero-edge transient nodes.
Delete transient nodes (concepts, intents, traces, commits) that have zero edges. A node with no
connections is noise — it got created but never wired to anything. Structural nodes (Organization,
Department, Role, SubAgent) are exempt even if orphaned (they trigger an invariant violation
instead, which needs human attention per conservative healing).

**10. Heal: Triangles (The Dream Round)** — Infer connections by closing triangles.
If Knowledge A connects to Bridge (a shared tag, a common agent touch) and Bridge connects to
Knowledge C, but A and C are not directly connected — and one of them has recent trace activity —
infer a `CONCEPTUALLY_RELATED_TO` edge. This is the dream round: the graph discovers hidden
connections by closing triangles. For SeedForth, bridges include shared tags, shared agents
touching both, shared project scope, and shared entity references.

**11. Immune System** — Detect unauthorized structural changes.
Compare current counts of Protocols, Invariants, IngestionRules, Rhythms, and ENABLES edges
against the last authorized snapshot. If any count changed without authorization (missing a
`MutationAuthorization` node), flag it as a MUTATION. Prevents unauthorized structural changes
to the OS core. The authorized snapshot is the `:Snapshot` node linked to the current canonical
Species via `:AUTHORIZES`.

**12. Learn** — Measure dream round effectiveness.
Count how many dream-round-inferred edges got subsequently activated (an agent queried or traced
one of their endpoints within the next 7 days). Record as a `:Measurement` with value
`activated_count / total_inferred`. This measures whether the system's guesses were useful —
did anyone actually follow the connections it inferred? Target: >30% activation rate.

**13. Liveness** — Is the system alive?
Check when the last heartbeat pipeline ran, when the last SessionTrace arrived, and whether
rhythms are active. If nothing has happened in the last 60 minutes, create an
`:Alert {severity: 'warning', message: 'System appears idle'}`. The SuperAgent reads these
alerts. If no pipeline has run in 12 hours, escalate to severity `critical`.

**14. Propose** — Find unblocked work and create ActionProposals.
Find `:WorkItem` nodes that are `status: open` and have no unfinished dependencies. Create
`:ActionProposal` nodes for them. This is how the system says "these work items are ready to
start — no blockers." Also find gaps (unserved demands, unlinked orphan knowledge, projects
with high silence but low progress) and propose investigation work items. The dream round
surfaces unblocked work automatically by closing triangles that reveal latent connections.

**15. Report** — System health snapshot.
Count total nodes, total edges, tests passing vs total, active agents, stale knowledge items,
open ActionProposals. Emit as a `:SystemReport` node with `report_type: 'heartbeat'`. The
system knows its own shape — how big it is and how healthy. The SuperAgent reads these reports.

**16. Resolve Contradictions** — Demote less-connected knowledge.
When two Knowledge nodes share the same category and 4+ tags, they are probably about the same
thing. Demote the one with fewer connections (lower degree = less validated). The demoted node
gets `confidence: 'low'` and a `contradicts: <node_id_of_stronger>` property. The graph resolves
its own contradictions by trusting the more-connected version. The contradicted knowledge is not
deleted — it survives as a historical record for audit.

**17. Route** — Route knowledge to agents that need it but haven't seen it.
Find Knowledge that addresses a Convergence topic but has not been delivered to the agents
converging on it. Create `:DeliveryProposal` nodes linking the Knowledge to the SubAgent.
This is the distribution engine: when the graph knows something relevant to an agent's work
and the agent has not seen it yet, it routes it. The SuperAgent reads DeliveryProposals and
decides whether to inject the knowledge into the agent's context.

**18. Snapshot** — Capture current graph state.
Capture current node counts, edge counts, deltas from the last snapshot. Link to previous
snapshot via a `:FOLLOWS` edge. Creates a time series of the graph's evolution. Used by the
immune system (protocol 11) to detect unauthorized changes. The snapshot includes:
- Node count per label
- Edge count per type
- Protocol count and checksums
- Invariant count and health status
- Test count and pass/fail
- Active agent count
- Open ActionProposal count

---

### A2. Real-Time Ingestion (On Every Trigger)

On every trigger event, immediately run Connect, Decay: TTL, and Heal: Orphans rather than
waiting for the heartbeat. This is the system's fast-twitch response — when something new
enters the graph, process it immediately.

**Trigger sources and the nodes they create:**

| Trigger | Node(s) Created | Immediate Action |
|---|---|---|
| Discord message in project channel | `:SessionTrace {source: 'discord', content, project, agent, tags}` | Connect to Knowledge by tag overlap |
| Agent inbox/outbox exchange | `:ActionRecord {source: 'agent', action_type, content, project}` | Connect to relevant WorkItems |
| Agent writes fact to local Neo4j staging | `:Knowledge {source: 'agent_fact', file_type, project, scope}` | Mark as pending promotion |
| Schedule tick fires (schedule.json) | `:ScheduleEvent {source: 'schedule', task_id, project}` | Connect to project's ScheduledTask |
| GitHub commit (webhook) | `:Commit {source: 'github', message, repo, author, sha}` | Scan message for project/feature keywords, wire via MODIFIES |
| SuperAgent decision | `:Decision {source: 'superagent', action_type, rationale, entity_ref}` | Wire to affected Organization/Department/SubAgent |
| SuperAgent ActionProposal acceptance | `:MutationAuthorization {authorized_by, snapshot_ref}` | Update immune system snapshot |
| Context compaction | `:Knowledge {file_type: 'compacted_fact', agent, project}` | Wire to agent's session via PRODUCES |
| Agent silence detected | `:SilenceEvent {agent, duration_seconds, severity}` | Wake check: escalate if >5min |
| Agent health check fails | `:HealthEvent {agent, status, error}` | Create Alert node, wire to agent |
| Resource usage threshold crossed | `:ResourceEvent {agent, metric, value, threshold}` | Create Alert, wire to cost allocation |

**Post-merge processing rules (run on every MERGE):**

1. **Tag extraction** — Extract hashtags and noun phrases from node `content`/`label`/`description`.
   Store as `tags` property array. Used by Connect, Converge, and Heal: Triangles to find
   semantic overlap. Tag extraction is a Cypher atom that tokenizes on whitespace, filters to
   nouns via stopword list, and deduplicates.

2. **Commit → Feature/Project wiring** — When a `:Commit` arrives, scan its message for words
   matching project names (from `:Project` nodes) and feature names (from `:Knowledge
   {file_type: 'workitem'}`). If the commit message mentions "solve-os pipeline fix", wire the
   Commit to the project's nodes via `MODIFIES`. Mark the commit as `digested: true` so it is
   not processed again.

3. **SessionTrace → Agent wiring** — When a `:SessionTrace` arrives, ensure it has a
   `:ORIGINATES_FROM` edge to the originating `:SubAgent`. If the SubAgent node does not exist
   (session from an unregistered agent), create a placeholder SubAgent with
   `status: 'unregistered'`.

4. **Agent knowledge write → scope attribution** — When an agent writes a `:Knowledge` node to
   local Neo4j staging, ensure it carries `scope` (owner org) and `visibility` (fleet/org/private).
   These properties propagate from the agent's parent Organization via the pre-write scope gate.

5. **Decision → entity wiring** — When a `:Decision` node arrives, wire it to the
   Organization/Department/SubAgent it affects via `:GOVERNS` edge. If the decision creates a new
   entity (seed, project creation), create the entity node in the same transaction.

---

### A3. Self-Maintenance

The graph maintains itself through the interaction of heartbeat protocols, real-time ingestion,
and invariant checks:

**Structural integrity** — Protocols 6 (Decay: Edges), 8 (Dedup), 9 (Heal: Orphans), and 16
(Resolve Contradictions) keep the graph lean and coherent. They remove noise, collapse
duplicates, and demote weak signals without human intervention.

**Quality enforcement** — Protocol 4 (Decay: Confidence) and the TDD gate (every executable
protocol node must have a TestCase validating it) enforce information quality. Single-source
claims are downgraded. Untested automation is flagged.

**Discovery** — Protocol 10 (Heal: Triangles — The Dream Round) discovers latent connections
by closing triangles. Protocol 12 (Learn) measures whether those discoveries are useful.
Protocol 2 (Connect) wires new signals to existing knowledge.

**Directional sensing** — Protocol 3 (Converge) detects when multiple agents are converging on
the same topic. Protocol 17 (Route) delivers relevant knowledge to agents that need it.
Protocol 14 (Propose) creates ActionProposals from gaps and unblocked work.

**Integrity verification** — Protocol 11 (Immune System) compares current structure against
the last authorized snapshot. Protocol 18 (Snapshot) creates the comparison baseline.
Protocol 13 (Liveness) checks whether the system is alive.

**The compounding loop for SeedForth:**

```
Agent works → SessionTraces captured → Graph connects traces to knowledge
  → Convergence detected between agents → Dream round infers new connections
    → Gaps detected → ActionProposals created → SuperAgent reads and decides
      → Agent picks up work (seeding, merging, rescoping, spawning)
        → SessionTraces captured → Loop continues
```

Every 30 minutes. Automatically. The graph does not wait to be asked.

---

## Part B: Fleet State Mapping

### B1. What Fleet Data Feeds Into the Graph

**Agent state (per SubAgent):**
- Identity, role, assigned project, capabilities
- Session trace (every Discord message, every inbox/outbox exchange)
- Health status (last health check response, HTTP status code, response time)
- Activity level (messages/hour, last activity timestamp, silence duration)
- Context pressure (session token count, compacted fact count, context window utilization %)
- Resource usage (RAM, API calls/hour, cost incurred)
- Model assigned and current provider (DeepSeek Pro, Flash, etc.)

**Project state (per entity: Organization/Department/Project):**
- Status (active/hibernated/deprecated)
- Entity type (earner/mission/client)
- GitHub repo URL and last commit timestamp
- Active agents count
- Open inbox count, last outbox timestamp
- Discord channel ID and last message timestamp
- Velocity metrics (commits/week, messages/week, fact compactions/week)
- Surplus/deficit (leverage in vs out — from Sutradhaar energy model)

**Schedule state:**
- Registered tasks in schedule.json (via `:ScheduledTask` nodes)
- Last run timestamp, next run timestamp
- Task interval, task status
- Execution log (last N runs, pass/fail, output summary)

**Knowledge state:**
- Every compacted fact extracted from agent sessions
- Every decision made by agents or SuperAgent
- Every work item tracked (open/in-progress/done/blocked)
- Every pattern discovered (from SessionTrace co-occurrence or dream round)
- Every gap detected (unserved demand, unaddressed convergence)
- Every invariant violation and healing action

**Cost state:**
- API cost per agent per day (from DeepSeek billing data or estimate)
- Total fleet cost per day
- Cost per entity (earner vs mission)
- Cost alerts when thresholds crossed

**Infrastructure state:**
- Server resource usage (RAM, CPU, disk)
- Supervisor program states (running/stopped/failed/backoff)
- Local Neo4j staging size and pending promotion count
- Mycelium connectivity (dev graph reachable, bolt-proxy healthy)

---

### B2. How Data Is Ingested

| Data Source | Ingestion Method | Cadence | Creates |
|---|---|---|---|
| Discord messages | Delta app.py event handler writes SessionTrace node | Real-time (on each message) | `:SessionTrace {source: 'discord'}` |
| Agent inbox/outbox | Delta bridge writes ActionRecord | Real-time (on each exchange) | `:ActionRecord` |
| SuperAgent decision | SuperAgent writes Decision via mycelium_store tool | On each decision | `:Decision` |
| Agent compacted facts | Agent writes Knowledge via mycelium_store tool | On context compacting | `:Knowledge` with `file_type: 'compacted_fact'` |
| Health check results | Delta health check loop writes HealthEvent | Every 30s per agent | `:HealthEvent` / `:AgentHealthSnapshot` |
| Schedule ticks | Delta schedule watcher writes ScheduleEvent | Per schedule.json task run | `:ScheduleEvent` |
| GitHub commits | GitHub webhook handler or cron poll | Real-time (webhook) or 5min poll | `:Commit` |
| Supervisor state | Cron poll of supervisorctl status | Every 5 minutes | `:ProcessStatus` |
| Resource usage | Cron poll of system stats | Every 15 minutes | `:ResourceEvent` |
| Cost data | Cron query of DeepSeek billing API | Daily (nightly) | `:CostReport` |
| Graph health | Heartbeat protocols | Every 30 minutes | `:SystemReport` |
| Snapshot | Heartbeat protocol 18 | Every 30 minutes | `:Snapshot` |

**Where writes land:**

- **Agents write** to the local Neo4j staging instance on delta-server
  (`bolt://localhost:7687`). This instance is write-enabled, isolated from shared graphs,
  and scoped by agent identity. Agents use the `mycelium_store` custom tool which wraps
  the Neo4j Python driver with a safe subset of operations (MERGE only, schema-validated).

- **Delta app.py writes** SessionTrace, ActionRecord, HealthEvent, SilenceEvent directly
  to the local Neo4j staging instance. These are agent-adjacent events that must enter the
  graph with minimal latency.

- **Cron jobs write** ScheduleEvent, ResourceEvent, CostReport to local Neo4j staging.

- **Nightly promotion** (2am UTC): export-staging.py reads all pending nodes from local
  Neo4j (`promoted = false`), generates `.cypher` files with MERGE statements and mycelium-
  compatible headers, validates via `validate-merge.sh`, commits to a branch on
  `kagrawal29/mycelium`, opens a PR, merges on green CI, bootstraps to the dev graph, and
  crystallizes. After promotion, promoted nodes are marked `promoted = true`.

- **The SuperAgent** and Hub agent (both running opencode) read the dev graph via the
  `mycelium binary` (read-only, bolt-proxy gated). Lag: 0-24 hours behind local writes.

---

### B3. The Complete System Map

The SeedForth fleet as modeled in the graph (node labels and edges):

```
// Root Organization
(:Organization:Knowledge {
  node_id: 'org-seedforth',
  label: 'SeedForth', entity_type: 'earner', status: 'active',
  mission: 'Infinite Agency — orchestration root for autonomous projects'
})
  -[:HAS_DEPARTMENT]-> (:Department:Knowledge {identity: 'seedforth/engineering'})
    -[:HAS_ROLE]-> (:Role:Knowledge {identity: 'seedforth/engineering/hub-orchestrator'})
      -[:ASSIGNED_TO]-> (:SubAgent {node_id: 'subagent-delta-hub', name: 'Delta Hub'})
        -[:ORIGINATES_FROM]-> (sessions...) via [:HAS_SESSION]
        -[:PRODUCES]-> (:Knowledge {file_type: 'decision|learning|pattern|compacted_fact'})
      -[:HAS_CAPABILITY]-> (:Capability {name: 'fleet_awareness'})
      -[:HAS_CAPABILITY]-> (:Capability {name: 'entity_proposal'})

    -[:HAS_ROLE]-> (:Role {identity: 'seedforth/engineering/builder'})
      -[:ASSIGNED_TO]-> (:SubAgent {name: 'Builder Agent'})
      -[:HAS_CAPABILITY]-> (:Capability {name: 'code_generation'})
      -[:HAS_CAPABILITY]-> (:Capability {name: 'deployment'})

  -[:HAS_DEPARTMENT]-> (:Department {identity: 'seedforth/bizdev'})
    -[:HAS_ROLE]-> (:Role {identity: 'seedforth/bizdev/outreach'})
      -[:ASSIGNED_TO]-> (:SubAgent {name: 'LinkedIn Agent'})

  -[:HAS_DEPARTMENT]-> (:Department {identity: 'seedforth/research'})

// Earner entities (each is both a Project and an Organization)
(:Organization:Knowledge {entity_type: 'earner', identity: 'solveos'})
  -[:HAS_DEPARTMENT]-> (:Department {identity: 'solveos/leadgen'})
    -[:HAS_ROLE]-> (:Role {identity: 'solveos/leadgen/linkedin-agent'})
      -[:ASSIGNED_TO]-> (:SubAgent {name: 'SolveOS LinkedIn Agent'})

(:Organization:Knowledge {entity_type: 'earner', identity: 'flowing-indian'})
  -[:HAS_DEPARTMENT]-> (:Department {identity: 'flowing-indian/marketing'})

(:Organization:Knowledge {entity_type: 'earner', identity: 'sceneforth-os'})

(:Organization:Knowledge {entity_type: 'earner', identity: 'seedforthing'})

// Client entities
(:Organization:Knowledge {entity_type: 'client', identity: 'revti-digital'})

// Mission entities (not yet instantiated, nodes exist as blueprints)
(:Organization:Knowledge {entity_type: 'mission', identity: 'sutatva', status: 'blueprint'})
(:Organization:Knowledge {entity_type: 'mission', identity: 'ashoonya', status: 'blueprint'})
(:Organization:Knowledge {entity_type: 'mission', identity: 'prayogshala', status: 'blueprint'})

// Cross-entity mesh edges
(:Department)-[:COLLABORATES_WITH {discovered_by: 'dream_round|manual', confidence: 0.85}]->(:Department)
(:SubAgent)-[:DELEGATES_TO {protocol: 'task_handoff'}]->(:SubAgent)
(:Knowledge)-[:CONCEPTUALLY_RELATED_TO]->(:Knowledge)

// Decision lineage
(:Decision {action: 'seed_entity|merge_entities|rescope|deprecate', decided_by: 'superagent'})
  -[:GOVERNS]-> (:Organization)
  -[:BASED_ON]-> (:SystemReport)
  -[:BASED_ON]-> (:ActionProposal)

// ActionProposal lifecycle
(:ActionProposal {type: 'CreateProject|MergeEntities|InvestigateGap|DeprecateCapability|...',
   status: 'proposed|accepted|rejected|executed', rationale, confidence})
  -[:PROPOSES_ACTION_ON]-> (:Organization|Department|Role|SubAgent)
  -[:PRODUCED_BY]-> (:Protocol {name: 'propose'})
```

**Scope and visibility rules on every Knowledge node:**

```cypher
CREATE (k:Knowledge {
  label: 'SolveOS pipeline bottleneck resolved',
  scope: 'solveos',              // owning org
  visibility: 'fleet',           // fleet = all agents, org = same org, private = one agent
  decay_protected: true,         // structural edges survive decay
  compaction_retention_days: 90, // after this, if never queried, decay applies
  fire_count: 0,                 // increments on every query via QueryTrace
  compacted_at: datetime(),      // when this fact was compacted from session context
  promoted: false                // false until nightly promotion syncs to dev graph
})
```

---

## Part C: Compass — Direction & Trajectory

### C1. How the Graph Shows Where the Fleet Is Going

The graph does not just describe the current state. It accumulates directional data over time
and surfaces trajectories through several mechanisms:

**Snapshot diffing.** Every 30 minutes (protocol 18), a Snapshot captures node counts per label,
edge counts per type, and active agent counts. Snapshot N+1 is linked to Snapshot N via
`:FOLLOWS`. The SuperAgent reads the diff: "last week we had 12 agents, now we have 15; last
week we had 80 compacted facts, now we have 240." The graph is its own trendline.

**Velocity metrics accumulated on entities.** Every Organization, Department, and SubAgent node
accumulates velocity properties over time:
- `sessions_last_7d` / `sessions_last_30d` — agent activity volume
- `facts_compacted_7d` / `facts_compacted_30d` — knowledge generation rate
- `commits_7d` / `commits_30d` — code change velocity
- `proposals_made_7d` / `proposals_accepted_7d` — momentum of proposals
- `messages_in_7d` / `messages_out_7d` — communication volume
- `cost_7d` / `cost_30d` — resource consumption trend
- `silence_events_7d` — how often the agent goes silent (inverse health metric)

The SuperAgent reads these with a single Cypher query:
```cypher
MATCH (o:Organization {entity_type: 'earner'})
RETURN o.label, o.sessions_last_7d, o.facts_compacted_7d, o.commits_7d
ORDER BY o.sessions_last_7d DESC
```

**Gap accumulation rate.** Protocol 15 (Report) counts open ActionProposals, unserved demands,
and unaddressed convergences. The diff between snapshots shows whether gaps are growing or
shrinking. A growing gap count means the fleet is generating more needs than it is addressing —
the system is either accelerating or faltering.

**Convergence density trend.** The ratio of `:Convergence` nodes to active `:SubAgent` nodes.
If convergence density is increasing, agents are naturally clustering on shared problems (healthy
fleet coordination). If it is decreasing, agents are working in isolation (potential fragmentation).

**Dream round activation rate.** Protocol 12 (Learn) measures what fraction of dream-round-
inferred edges get activated within 7 days. An increasing activation rate means the graph's
guesses are getting better. A decreasing rate means the graph is inferring stale or spurious
connections — the dream round may need tuning.

**Decay pipeline throughput.** How many Knowledge nodes are created per day vs decayed per day.
If creation > decay, the knowledge base is growing. If decay > creation, knowledge is evaporating
faster than it is being produced (fleet may be slowing down or context compacting may need
adjustment).

---

### C2. Metrics That Emerge from Accumulated Agent Activity

| Metric | Formula | What It Signals |
|---|---|---|
| Fleet velocity | `sum(sessions_last_7d) / count(active_agents)` | Are agents producing output? Healthy: >10 sessions/week/agent |
| Knowledge yield | `sum(facts_compacted_7d) / sum(sessions_last_7d)` | Are sessions producing durable knowledge? Healthy: >0.3 facts/session |
| Convergence rate | `count(convergences_last_7d) / count(active_agents)` | Are agents coordinating? Healthy: >0.1 convergences/agent/week |
| Dream efficacy | `activated_inferred_edges / total_inferred_edges` (7d window) | Are inferred connections useful? Target: >30% |
| Proposal throughput | `accepted_proposals_7d / proposed_proposals_7d` | Is the SuperAgent acting on graph intelligence? |
| Gap pressure | `open_proposals + unserved_demands + unresolved_invariants` | System stress indicator |
| Energy conversion | `(sum(surplus) per earner) / (sum(cost) per mission)` | Sutradhaar leverage efficiency |
| Silhouette score | Graph cluster coherence (from semantic clustering) | Is the knowledge base well-structured? |

---

### C3. How the SuperAgent Reads the Compass

The SuperAgent (Sutradhaar / Hub orchestrator) reads the compass through three channels:

**1. Periodic briefings via mycelium queries.**
The SuperAgent opens each session by querying the compass:
```bash
mycelium --target dev ask "what is the current state of the fleet?"
mycelium --target dev shell "MATCH (r:SystemReport) RETURN r ORDER BY r.created_at DESC LIMIT 1"
mycelium --target dev shell "MATCH (d:Department) WHERE d.status = 'active' RETURN d.identity, d.sessions_last_7d"
```

**2. Alert nodes surfaced by heartbeat protocols.**
Protocol 13 (Liveness) and invariant violation checks create `:Alert` nodes. The SuperAgent
queries for unresolved alerts:
```bash
mycelium --target dev shell "MATCH (a:Alert {resolved: false}) RETURN a ORDER BY a.severity DESC"
```

**3. ActionProposal queue.**
Protocol 14 (Propose) creates ActionProposal nodes. The SuperAgent reads the queue:
```bash
mycelium --target dev shell "MATCH (ap:ActionProposal {status: 'proposed'}) RETURN ap ORDER BY ap.confidence DESC"
```

**4. Observatory dashboard.**
The delta-server observatory (http://143.110.226.214:8888) renders fleet health, telemetry runs,
scheduled tasks, and project registry. The SuperAgent references this for a quick visual overview.

**5. Snapshot trend.**
The SuperAgent reads the last 30 Snapshots to detect trends:
```cypher
MATCH (s:Snapshot)
WHERE s.created_at > datetime() - duration('P30D')
RETURN s.created_at, s.node_count, s.edge_count, s.active_agent_count
ORDER BY s.created_at
```

---

## Part D: Levers — Steering Controls

### D1. What ActionProposals the Graph Produces

Every heartbeat, protocol 14 (Propose) examines the graph state and creates ActionProposal nodes
for actionable gaps. Each proposal includes:
- `type` — one of the proposal types below
- `rationale` — human-readable explanation of why this action is needed
- `confidence` — 0.0 to 1.0 (based on signal strength, convergence depth, gap severity)
- `evidence_refs` — list of node IDs that support this proposal (Knowledge nodes, Convergence
  nodes, Gap nodes, InvariantViolation nodes)
- `proposed_by` — the Protocol node ID that created it
- `status` — `proposed` | `accepted` | `rejected` | `executed`
- `risk_level` — `low` | `medium` | `high` | `critical`

**Proposal types:**

| Type | Trigger Condition | Example |
|---|---|---|
| `CreateProject` | A demand signal with `gap_signal=true` has had no addressed Knowledge for 7+ days. A convergence node accumulates 3+ agents but no project exists in that domain. | "Create a project for pipeline optimization — 4 agents have independently touched this topic in the last week" |
| `MergeEntities` | Two entities have >50% overlap in their Knowledge graphs (shared tags, shared agents touching both, similar session topics). | "SolveOS leadgen and SceneforthOS brand intake are converging on the same topic space. Consider merging or differentiating their mandates." |
| `DeprecateEntity` | An entity has `sessions_last_7d = 0`, `commits_30d = 0`, and no ActionProposals or WorkItems referencing it for 30 days. | "Audioworld has had zero activity in 30 days. Consider deprecating or hibernating." |
| `RescopeEntity` | An entity's knowledge graph touches 3+ unrelated domains, indicating scope creep. Or an entity's activity is 80%+ in a single sub-domain not matching its charter. | "SolveOS is spending 80% of sessions on pipeline infrastructure, not leadgen. Consider rescoping its mandate." |
| `ReallocateAgent` | An agent has <5 sessions/week while another department has >50 open WorkItems. | "Reallocate LinkedIn Agent to SolveOS — bizdev has capacity, SolveOS has backlog." |
| `InvestigateGap` | A convergence has 3+ agents touching a topic but no Knowledge node addresses it with `confidence > low`. | "4 agents touching 'LinkedIn rate limiting' — no authoritative Knowledge exists. Investigate and document." |
| `AuditCostExposure` | An entity's cost has exceeded $threshold for 7 consecutive days with no corresponding increase in velocity. | "SolveOS cost is up 40% this month but output is flat. Audit API usage and consider model downgrade." |
| `WakeInactiveAgent` | An agent has been silent (no outbox, no health check success) for >30 minutes. | "Builder Agent has been silent for 45 minutes. Agent may require restart." |
| `HealInvariantViolation` | An invariant check returned `unhealthy` and the healing protocol could not auto-resolve (orphan SubAgent, cycle in BELONGS_TO tree, etc.). | "Orphan SubAgent detected: 'builder-agent-v2' has no ASSIGNED_TO edge. Assign or deprecate." |

The graph does NOT autonomously execute these proposals. It creates them, scores them, and
presents them. The SuperAgent decides.

---

### D2. How the SuperAgent Decides and Executes

The SuperAgent (Sutradhaar, running as the Hub orchestrator) reads the proposal queue, applies
its constitution, and decides:

**Decision flow:**

1. **Read proposals:** Query `:ActionProposal {status: 'proposed'}` ordered by confidence DESC.
2. **Assess against constitution principles:**
   - Non-zero-sum by construction — does this proposal require a loser?
   - Leverage → autonomy — does this move increase autonomy somewhere?
   - Repair before reward — does this help those the world was cruel to?
   - Energy model — what are the flows? Surplus from earners funding mission.
3. **Classify by gate:**
   - Below the gate (autonomous): `InvestigateGap`, `WakeInactiveAgent`, `ReallocateAgent`
     (within approved resource pool), `RescopeEntity` (non-contractual)
   - At the gate (needs ratification): `CreateProject` (if it touches real people/money),
     `MergeEntities` (if obligations exist), `DeprecateEntity` (if live customers),
     `ReallocateAgent` (if crosses earner→mission boundary with cost impact),
     `AuditCostExposure` (financial action)
4. **Execute below-gate decisions immediately:**
   - Write a `:Decision` node with status and rationale
   - If the action creates/modifies graph nodes: write them via mycelium_store tool
   - If the action requires infra changes (restart agent, create supervisor config):
     execute via Delta's existing tooling
5. **Queue above-gate decisions for ratification:**
   - Write a `:RatificationRequest` node linked to the ActionProposal
   - Post to admin Discord channel with proposal summary and energy model projection
   - Wait for ratification via Discord reaction or command
6. **Report back:**
   - Write execution result as a `:Decision` node
   - Mark the ActionProposal as `accepted` | `rejected` | `executed`
   - Wire the Decision to the affected graph entities via `:GOVERNS`

---

### D3. Invariances — What Detects When Things Are Off-Course

These invariants run every heartbeat. If any are unhealthy, the system creates an invariant
violation and the immune system fires healing protocols:

**I1 — No orphan agents.** Every `:SubAgent` must have exactly one `[:ASSIGNED_TO]->(r:Role)`.
A SubAgent without a Role is an orphan. Healing: deprecate the agent, flag for review.
```cypher
MATCH (sa:SubAgent) WHERE NOT (sa)-[:ASSIGNED_TO]->(:Role) RETURN sa
```

**I2 — No orphan roles.** Every `:Role` must have exactly one `[:HAS_ROLE]` incoming from a
`:Department` or `:Organization`. Healing: deprecate role, cascade to assigned agents.
```cypher
MATCH (r:Knowledge {file_type: 'role'}) WHERE NOT (r)<-[:HAS_ROLE]-(:Knowledge {file_type: 'department|organization'}) RETURN r
```

**I3 — No cycles in BELONGS_TO tree.** The `[:BELONGS_TO*]` traversal must be acyclic.
Healing: break the cycle at the most-recently-created edge, flag for review.
```cypher
MATCH path = (n)-[:BELONGS_TO*]->(n) RETURN path
```

**I4 — Active agents are responsive.** Every agent with `status: 'active'` must have had a
successful health check in the last 5 minutes. If not, create a `:HealthEvent {status: 'unreachable'}`.
Healing: supervisorctl restart.

**I5 — No unauthorized protocol mutations.** Protocol and invariant counts must match the last
authorized snapshot. Healing: roll back to snapshot, flag mutation.
```cypher
MATCH (p:Protocol {enabled: true}) RETURN count(p) AS protocol_count
MATCH (i:Invariant) RETURN count(i) AS invariant_count
-- Compare against Snapshot values
```

**I6 — Graph density above threshold.** Edges per node must stay above 1.5 (minimum for traversability).
Below this, orphan nodes and un-traversable paths accumulate. Healing: fire semantic densification
(protocol-connect, protocol-heal-triangles).
```cypher
MATCH (n) WITH count(n) AS nodes
MATCH ()-[e]->() WITH nodes, count(e) AS edges
RETURN edges * 1.0 / nodes AS density
```

**I7 — Fleet knowledge freshness.** At least one new Knowledge node with `file_type: 'compacted_fact'`
must be created every 24 hours. If a full day passes with no compacted facts, the fleet may be
idle or context compacting may have stopped. Alert: severity `warning`.
```cypher
MATCH (k:Knowledge {file_type: 'compacted_fact'})
WHERE k.created_at > datetime() - duration('P1D')
RETURN count(k)
```

**I8 — Agent cost within bounds.** No single agent should exceed $5/day in API cost. If exceeded,
create a `:CostAlert`. Healing: switch agent to cheaper model (Flash vs Pro), reduce session
frequency, or alert admin.
```cypher
MATCH (c:CostReport {agent: <agent_id>, date: <today>})
WHERE c.daily_cost > 5.0
RETURN c
```

**I9 — Every executable node has a test.** Every Protocol, CypherAtom, and Workflow node with
a `cypher` or `runner` property must have at least one TestCase validating it. Untested automation
is flagged as quality risk.

**I10 — Convergence-to-agent ratio.** There must be at least `0.2 * active_agent_count` convergence
nodes (minimum 1). If no convergences exist, agents are working in isolation — the heap
is fragmenting.

**I11 — Promotion pipeline healthy.** Local Neo4j staging must have fewer than 1000 unpromoted
nodes. If staging grows beyond this, either the promotion job is failing or agents are writing
faster than the nightly cycle can process. Alert.

**I12 — Species chain intact.** The current `:Species` must have a `manifest_root` and either
be marked as `genesis` or have a `DESCENDED_FROM` ancestor. The Merkle chain must not be
broken.

---

## Part E: Comparison to Current Mycelium OS

### E1. Concept Mapping

Every mycelium OS concept designed for Qubit-Capital maps to a SeedForth equivalent:

| Mycelium OS (Qubit-Capital) | Source | SeedForth OS | Source |
|---|---|---|---|
| **Trace** — Claude Code session recording via LangSmith | OPERATING-SYSTEM.md:59 | **SessionTrace** — Discord message, inbox/outbox exchange, or opencode session recording | This spec A2 |
| **GitHub Issue** — External issue tracker | OPERATING-SYSTEM.md:62 | **ActionProposal / Discord Task** — Graph-produced proposals or Discord messages tagged as action items | This spec D1 |
| **Competitive intelligence** — 42 Competitors, 1200+ Evidence items, G2 reviews | OPERATING-SYSTEM.md:170-181 | **Fleet intelligence** — Project health metrics, agent activity, resource usage, velocity trends | This spec B1, C2 |
| **Person** — Team member (Abhishek, Pranav, Kshitiz) | OPERATING-SYSTEM.md:23 | **SubAgent** — Fleet agent (Hub, Builder, LinkedIn, etc.) + **Sutradhaar** as orchestrating consciousness | MYCELIUM.md:184-190, this spec B3 |
| **Demand** — Topic the team asks about via MCP queries | OPERATING-SYSTEM.md:47 | **Demand** — Topic multiple agents touch via SessionTraces or context queries | This spec A1 protocol 5 |
| **Convergence** — Two people converging on same topic | OPERATING-SYSTEM.md:23 | **Convergence** — Two SubAgents independently working same graph region | This spec A1 protocol 3 |
| **MCP Query → Demand** — Queries strengthen demands | OPERATING-SYSTEM.md:47 | **SessionTrace → Demand** — Agent session traces strengthen demand on topics they touch | This spec A1 protocol 2 |
| **Knowledge** — Information with evidence sources | OPERATING-SYSTEM.md:41 | **Knowledge** — Compacted facts, decisions, learnings, patterns — same type, new sources | migration-to-opencode.md 4.3 |
| **Feature / Screen / Scenario** — Product capabilities | OPERATING-SYSTEM.md:92-97 | **Capability / Entity / WorkItem** — Agent capabilities, organizational entities, tracked work items | SEEDFORTH-SEED.md §6.5 |
| **WorkItem → Issue** — Links dev plan to issue tracker | OPERATING-SYSTEM.md:132 | **WorkItem → ActionProposal** — Links work tracking to the proposal the SuperAgent reads | This spec D1 |
| **DeliveryEvent / RECEIVED** — Knowledge delivered to person | OPERATING-SYSTEM.md:52-53 | **DeliveryProposal** — Knowledge proposed for delivery to agent via context injection | This spec A1 protocol 17 |
| **Dream Round** — Close triangles to infer connections | OPERATING-SYSTEM.md:104-105 | **Dream Round** — Same mechanism, seedforth bridges are shared tags, shared agents, shared scope | This spec A1 protocol 10 |
| **Snapshot / Immune System** — Auth-snapshot comparison | OPERATING-SYSTEM.md:109, 128-129 | **Snapshot / Immune System** — Same mechanism, counts include SeedForth-specific node types | This spec A1 protocols 11, 18 |
| **Leverage in/out** — Not present (Qubit-Capital did not use Sutradhaar model) | — | **Leverage in/out** — Sutradhaar energy model: earners produce surplus, missions consume | CONSTITUTION.md:61-70 |
| **TDD Gate** — Every protocol with cypher must have test | OPERATING-SYSTEM.md:56 | **TDD Gate** — Same invariant, extended to Workflow and CypherAtom nodes | This spec I9 |
| **Bridges** — Architecture→Market, Demand→Competitive | OPERATING-SYSTEM.md:141-148 | **Bridges** — Agent→Knowledge, Cost→Allocation, Convergence→Entity | This spec B3 |

### E2. What Stays the Same

The following mycelium OS mechanisms are used identically for SeedForth:

- **Merkle integrity** — Species chain, manifest_root, leaf_hash on every node, Being singleton
- **Witness signatures** — ed25519 signatures on candidate species, canonize flow
- **Federation** — Source/Imported/Adopted for importing external graph data
- **Self-describability** — mycelium docs reads Concept + Guide + DesignPrinciple + Protocol +
  Invariant + Command nodes from the graph
- **Cypher-native behavior** — Every protocol, invariant, and ingestion rule is a Cypher query
  stored on a node in the graph. The graph runs itself.
- **Protocol-as-node** — Protocols are `:Protocol` nodes with `enabled`, `cadence`, and
  `cypher`/`file_path` properties. The heartbeat runner looks up Protocol nodes and executes them.
- **Invariant-as-node** — Invariants are `:Invariant` nodes with `check_cypher`, optional
  `heal_protocol`, and `health` property. The immune system fires healing protocols when
  invariants go unhealthy.
- **Decay pipeline** — Confidence, Demand, Edges, TTL decay protocols operate identically,
  adapted for SeedForth-specific node types
- **Snapshot and immune system** — Auth-snapshot comparison, mutation detection

### E3. What Changes

| Aspect | Qubit-Capital OS | SeedForth OS | Rationale |
|---|---|---|---|
| Primary trace source | Claude Code sessions (LangSmith) | Discord messages + opencode sessions + inbox/outbox | Fleet agents communicate via Discord bridge, not direct Claude Code |
| Primary issue source | GitHub Issues | Discords tasks + ActionProposals | No external issue tracker — issues live in the graph |
| External intelligence | Market research (competitors, G2 reviews, Reddit) | Internal fleet metrics (health, velocity, cost) | SeedForth is the intelligence layer for our own fleet, not external product research |
| Persons | Individual humans (team members) | SubAgents (fleet agents) + Sutradhaar | The fleet IS the team knowledge graph |
| Knowledge routing | DeliveryEvent to Persons | DeliveryProposal + context compacting to SubAgents | Knowledge is injected into agent context, not sent to humans |
| Steering mechanism | ActionProposals for work items | ActionProposals for fleet operations (seed, merge, deprecate, rescope) | The fleet structure IS the product — steering changes the fleet |
| Energy model | Not present | Leverage in/out per entity (Sutradhaar constitution) | The Sutradhaar constitution adds an energy/autonomy conversion model |
| Competitive landscape | 42 competitors, 1200+ evidence items | Not applicable (yet) — could be added as federation import | SeedForth is internal; external intelligence is a future phase |
| Bridge types | Architecture→Market, Demand→Competitive, Pain→Evidence | Agent→Knowledge, Cost→Allocation, Convergence→Entity, Project→WorkItem | Bridges connect fleet-internal entities, not market entities |

---

## Part F: Implementation

### F1. Current State (July 2026)

The dev graph has approximately 158 nodes with basic structure: Organization, Department, Role,
Concept, and SubAgent nodes seeded by bootstrap Cypher. The graph exists but has:
- No heartbeat protocols running (no 30-min pulse)
- No real-time ingestion from Discord/agents
- No decay, dream round, or self-maintenance
- No ActionProposals
- No snapshot/immune system
- No SessionTrace or Knowledge nodes from agent activity
- No energy model (leverage in/out)

The fleet currently runs on Claude Code (being migrated to opencode via Phases 0-7 in
migration-to-opencode.md). Agents write facts to local Neo4j staging (Phase 4 of that plan).

### F2. Phase 0: Foundation (Week 1)

**Goal: Seed the graph with the complete structural model.**

- [ ] Deploy org bootstrap Cypher to dev graph (extends existing 158 nodes):
  - All earner entities (SolveOS, FlowingIndian, SceneforthOS, Seedforthing)
  - All client entities (Revti Digital)
  - All mission entities as blueprints (Sutatva, Ashoonya, Prayogshala)
  - All Departments, Roles, and SubAgents with capability assignments
  - Cross-entity COLLABORATES_WITH edges (manual seed based on known relationships)
  - Capability nodes and REQUIRES_CAPABILITY / HAS_CAPABILITY edges
- [ ] Register the 18 SeedForth heartbeat protocols as `:Protocol` nodes in the dev graph
- [ ] Register the 12 SeedForth ingestion rules as `:IngestionRule` nodes
- [ ] Register the 12 SeedForth invariants as `:Invariant` nodes
- [ ] Register seed :Concept nodes for all SeedForth-specific types
- [ ] Create initial `:Snapshot` node (authorized snapshot for immune system)
- [ ] Add decay_protected guards to mycelium decay protocols (upstream PR)
- [ ] Add compaction_retention_days handling protocol (upstream PR)
- [ ] Verify: `mycelium --target dev shell "MATCH (n) RETURN count(n)"` shows correct count
- [ ] Verify: `mycelium --target dev doctor` returns green

**Deliverable:** The graph has a complete, accurate model of the fleet with all entities,
agents, capabilities, and cross-connections. 0 runtime protocols yet.

### F3. Phase 1: Wire Ingestion (Weeks 2-3)

**Goal: Every agent action, every Discord message, every schedule tick feeds into the graph.**

- [ ] Deploy SessionTrace ingestion:
  - Delta app.py writes `:SessionTrace` node on every Discord message
  - Real-time: on MERGE, run Connect (wire to Knowledge by tag overlap)
  - Scope attribution: SessionTrace gets `project` and `scope` from the channel/agent context
- [ ] Deploy ActionRecord ingestion:
  - Delta bridge writes `:ActionRecord` node on every inbox/outbox exchange
  - Wire ActionRecord to the originating SubAgent via `:ORIGINATES_FROM`
- [ ] Deploy HealthEvent ingestion:
  - Delta health check loop writes `:HealthEvent` / `:AgentHealthSnapshot` every 30s
  - Create `:SilenceEvent` when agent goes silent >25s
- [ ] Deploy ScheduleEvent ingestion:
  - Schedule watcher writes `:ScheduleEvent` on each task execution
- [ ] Deploy Commit ingestion:
  - Poll GitHub for new commits every 5 minutes (or wire webhook)
  - Wire commits to projects/features via MODIFIES
- [ ] Deploy agent fact ingestion (depends on Phase 4 of migration-to-opencode):
  - Agent writes compacted facts via `mycelium_store` tool → local Neo4j staging
  - Nightly promotion syncs to dev graph
  - After promotion, facts have PRODUCES edges to their SubAgent
- [ ] Deploy resource/cost ingestion (cron jobs):
  - Supervisor state poll → ProcessStatus nodes
  - DeepSeek billing API poll → CostReport nodes
- [ ] Verify: agent sends Discord message → SessionTrace appears in dev graph within 30s
- [ ] Verify: agent compacts context → Knowledge node appears in dev graph within 24h
- [ ] Verify: commit pushed → Commit node with MODIFIES edge appears within 5min

**Deliverable:** The graph ingests every fleet event in real-time (or near-real-time).
Approximately 500+ new nodes/day from agent activity.

### F4. Phase 2: Add Heartbeat (Week 4)

**Goal: The 18 protocols run every 30 minutes. The graph maintains itself.**

- [ ] Deploy heartbeat runner:
  - Cron job or systemd timer on delta-server that fires every 30 minutes
  - Calls `mycelium breathe` (or equivalent: iterate Protocol nodes, execute in order)
  - Runs as the delta user, connects to dev graph via mycelium binary
- [ ] Activate Wake (protocol 1): skip heartbeat if no new nodes since last run
- [ ] Activate Connect (protocol 2): wire new SessionTraces to Knowledge
- [ ] Activate Converge (protocol 3): detect agent clusters on same topics
- [ ] Activate Decay protocols (4-7): Confidence, Demand, Edges, TTL
- [ ] Activate Dedup (protocol 8): remove duplicate edges
- [ ] Activate Heal protocols (9-10): Orphans, Triangles (Dream Round)
- [ ] Activate Immune System (protocol 11): compare against authorized Snapshot
- [ ] Activate Learn (protocol 12): measure dream round effectiveness
- [ ] Activate Liveness (protocol 13): create Alert if system idle
- [ ] Activate Propose (protocol 14): create ActionProposals from gaps
- [ ] Activate Report (protocol 15): emit SystemReport
- [ ] Activate Resolve Contradictions (protocol 16): demote weak knowledge
- [ ] Activate Route (protocol 17): propose knowledge delivery to agents
- [ ] Activate Snapshot (protocol 18): capture current state
- [ ] Activate all invariants (I1-I12) with healing protocols
- [ ] Verify: heartbeats run on schedule (check Snapshot created every 30 min)
- [ ] Verify: stale knowledge gets decayed (TTL nodes removed, confidence downgraded)
- [ ] Verify: dream round infers connections (check new CONCEPTUALLY_RELATED_TO edges)
- [ ] Verify: ActionProposals appear (check count > 0 after 24h of agent activity)
- [ ] Verify: orphan nodes are cleaned (check orphan count stabilizes near 0)

**Deliverable:** The graph runs autonomously. Every 30 minutes, it ingests, digests,
heals, and proposes. No manual maintenance needed.

### F5. Phase 3: Add Compass (Weeks 5-6)

**Goal: The graph shows where the fleet is going, not just where it is.**

- [ ] Deploy velocity accumulation:
  - Every heartbeat, update `sessions_last_7d`, `facts_compacted_7d`, `commits_7d` on
    Organization, Department, and SubAgent nodes
  - Compute from SessionTrace, Knowledge, and Commit nodes
- [ ] Deploy metrics computation:
  - Fleet velocity = sum(sessions_last_7d) / count(active_agents)
  - Knowledge yield = sum(facts_compacted_7d) / sum(sessions_last_7d)
  - Convergence rate = count(convergences_last_7d) / count(active_agents)
  - Dream efficacy = protocol 12 output
  - Proposal throughput = accepted_proposals_7d / proposed_proposals_7d
  - Gap pressure = open_proposals + unserved_demands + unresolved_invariants
  - Store as `:Measurement` nodes with metric name, value, and timestamp
- [ ] Deploy snapshot trend analysis:
  - On each Snapshot creation, compute diff from previous Snapshot
  - Store deltas as properties: `node_count_delta`, `edge_count_delta`, `agent_count_delta`
- [ ] Deploy SuperAgent compass briefings:
  - Hub template (CLAUDE.md) updated with compass queries
  - Hub opens each session with: "Read the current SystemReport, snapshot trend, and
    top 5 ActionProposals before engaging with the user."
- [ ] Deploy compass visualization:
  - Observatory dashboard shows: fleet velocity chart, gap pressure trend, proposal queue,
    snapshot diff timeline, agent activity heatmap
- [ ] Deploy energy model tracking:
  - Add leverage_in, leverage_out, surplus_deficit properties to Organization nodes
  - Compute from CostReport (cost out) vs output metrics (velocity, proposals accepted)
  - Sutradhaar energy model visualization in observatory
- [ ] Verify: entity velocity properties update accurately after each heartbeat
- [ ] Verify: Measurement nodes show meaningful trends after 7 days
- [ ] Verify: SuperAgent can answer "what is the fleet's trajectory?" from graph alone
- [ ] Verify: observatory compass dashboard matches graph state

**Deliverable:** The compass is live. The SuperAgent and human operator can see at a glance
what is accelerating, what is stalling, and where to steer.

### F6. Phase 4: Add Levers (Weeks 7-8)

**Goal: The SuperAgent steers the fleet through graph-produced ActionProposals.**

- [ ] Deploy SuperAgent decision loop:
  - Hub agent (Sutradhaar embodiment) reads ActionProposal queue at start of each session
  - Applies constitution filtering (gate check)
  - Executes below-gate proposals autonomously
  - Queues above-gate proposals for Discord-based ratification
- [ ] Deploy below-gate execution paths:
  - `InvestigateGap` → Hub spawns liminal agent to research and document
  - `WakeInactiveAgent` → Hub requests Delta restart via Delta bridge command
  - `RescopeEntity` (non-contractual) → Hub updates entity charter in graph
  - `ReallocateAgent` (within budget) → Hub proposes to Delta for supervisor reconfig
- [ ] Deploy above-gate ratification channel:
  - Hub posts to admin Discord channel with proposal summary:
    "Proposal: Merge SolveOS leadgen into SceneforthOS brand intake. Rationale: 80% topic overlap.
     Energy model: saves ~$30/month in redundant agent cost. Confidence: 0.85."
  - Admin reacts with ✅ to approve, ❌ to reject
  - Hub checks reaction on next session start
  - If approved: execute. If rejected: mark proposal as `rejected`.
- [ ] Deploy healing protocol execution:
  - Orphan detection → deprecate, flag for review
  - Cycle detection → break at most-recent edge, flag
  - Density drop → fire semantic densification (strengthen edges, dream round intensifies)
  - Cost overage → switch to cheaper model, flag for review
- [ ] Deploy Sutradhaar energy model integration:
  - Hub computes leverage balance per entity every heartbeat cycle
  - "SolveOS has $X surplus this month → recommend allocating $Y to Ashoonya research"
  - Creates ActionProposal for surplus redistribution
- [ ] Verify: ActionProposal queue is read by Hub on every session start
- [ ] Verify: below-gate proposals execute without human intervention
- [ ] Verify: above-gate proposals appear in admin Discord channel within 30s
- [ ] Verify: ratification reaction triggers execution within one session cycle
- [ ] Verify: energy model proposals are accurate (costs match DeepSeek billing data)
- [ ] Verify: healing protocols resolve invariant violations within 2 heartbeat cycles

**Deliverable:** The full operating system is live. The graph senses, decides, and the
SuperAgent steers. The human operator provides ratification at the gate and monitors
the compass.

---

## Part G: Open Architecture Decisions

**1. Where does the heartbeat runner live?**
The heartbeat (30-min cron) should run on delta-server, managed by systemd timer or cron.
It calls `mycelium breathe --target dev` which iterates all enabled Protocol nodes and
executes them in order. The runner itself is a thin shell or Python script — the protocols
are Cypher in the graph. If delta-server goes down, the heartbeat stops. Mitigation:
a secondary timer on pulse-server as health check guard.

**2. Agent write path: mycelium_store tool or direct mycelium-dev inject?**
The spec says `mycelium_store` custom tool wrapping a Python script writing to local Neo4j.
Alternative: use `mycelium-dev inject --target local` directly from the agent. Tradeoff:
the custom tool provides schema validation, scope checking, and agent identity scoping.
**Decision: mycelium_store tool** (as specified in migration-to-opencode.md §4.2).

**3. How does the SuperAgent authenticate to the graph?**
The SuperAgent (Hub) reads the dev graph via `mycelium --target dev shell` (read-only).
It writes decisions and mutations to local Neo4j staging (same as any agent). Its write
path includes a `scope: 'seedforth'` and `visibility: 'fleet'` property set — the Hub
writes fleet-level decisions that all agents should see after nightly promotion.

**4. ActionProposal confidence calculation.**
Confidence is a composite score:
- Signal strength: `count(evidence_refs) * 0.3`
- Convergence depth: `count(converging_agents) * 0.2`
- Gap severity: `1.0` for liveness issues, `0.7` for cost issues, `0.4` for knowledge gaps
- Recency: if the gap has existed for 7+ days without being addressed, confidence decreases
  by `0.1 * (days_unaddressed / 7)`
- Capped at `[0.0, 1.0]`

**5. Ratification timeout.**
Above-gate proposals (ratification requests) expire after 72 hours if no response.
If expired, the proposal is marked `expired` and a new one is created with higher
confidence (escalation). This prevents stale proposals from accumulating.

**6. How does context compacting interact with the graph?**
When an agent compacts context, it writes Knowledge nodes to local Neo4j and replaces
the conversation history with: "I have stored the following in mycelium (pending
promotion): knowledge node ids X, Y, Z. Query them if you need the details."
After nightly promotion, these Knowledge nodes are queryable by all agents. The graph
IS the fleet's shared memory. The Sutradhaar constitution ensures this memory is
truthful, non-lossy, and accessible.

---

## Part H: Success Criteria

The mycelium OS for SeedForth is complete when:

1. **Ingestion is seamless.** Every fleet event — every Discord message, every agent session,
   every commit, every health check — appears in the graph within 30 seconds (real-time) or
   24 hours (nightly promotion for agent-written facts).

2. **The heartbeat is autonomous.** All 18 protocols run every 30 minutes without manual
   intervention. The graph ingests, digests, heals, and proposes without a human watching.

3. **The compass is directional.** The SuperAgent can answer "what is the state of the
   fleet?" from the graph alone. Trajectories (accelerating, stalling, fragmenting) are
   visible in snapshot diffs and velocity metrics.

4. **The levers are actionable.** The graph produces ActionProposals. The SuperAgent reads,
   decides, and executes (below the gate autonomously, above the gate with ratification).
   The fleet steers itself.

5. **The invariants hold.** I1-I12 are healthy at every heartbeat check. If an invariant
   breaks, the immune system detects, heals, or alerts within 2 heartbeat cycles.

6. **The Sutradhaar energy model is live.** Leverage in/out per entity is tracked in the
   graph. Surplus from earners funds mission entities. The compass shows energy flows.

7. **The graph is self-describable.** `mycelium docs` generates this document from
   Protocol, Invariant, Concept, and Guide nodes in the graph. The spec and the graph
   never diverge.

---

*Every protocol, every ingestion rule, every invariant, and every lever specified here is
represented as a node in the graph. The graph runs itself. This document is a snapshot —
the graph is the living version.*
