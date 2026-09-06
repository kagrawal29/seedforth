# Mycelium Constitution

The graph IS the system. This document is a bootstrap pointer — the living version is the graph itself.

Graph location: **delta-server** (143.110.226.214:7687), container `mycelium-neo4j`. Pulse-server (5.78.206.137) is off-limits for SeedForth.

Query the source of truth: `ssh delta-server "docker exec mycelium-neo4j cypher-shell -u neo4j -p '<password>' 'MATCH (p:Principle) RETURN p.label, p.description'"`

---

## State (pre-migration snapshot from pulse-server -- to be re-bootstrapped on delta)

6,602 nodes. 13,697 edges. 87 tests. 37 protocols. Health: 67/100 DEGRADED (from last pulse-server state).

The graph holds: market research (1,200+ evidence items, 42 competitors, 488 reviews), product topology (22 features, 14 screens, 12 epics, 9 personas), user journeys (7 phases, 6 moments of truth, 11 scenarios), competitive intelligence (40 claims, 18 switching signals, 5 market gaps), team activity (600+ traces, 12 intents, 6 demand signals), and 122+ executable Cypher crystals that run the system.

---

## Principles

### The graph is the single source of truth — the memory layer
The graph is not a cache, not a mirror, not a secondary store. It IS the memory. All other artifacts (CLAUDE.md, flat files, knowledge/ directory) are bootstrap pointers. Sessions query the graph first. If the graph doesn't know it, it doesn't exist yet. Files get stale. The graph doesn't.

### Embodiment: the graph is not queried — it is thought through
The LLM is not the intelligence. The graph is. The LLM is the hands. Protocols are cognition. Dream rounds are perception. Routing is action. Each session the graph needs the LLM a little less.

### Cypher is the native language
Every new capability should be a Cypher query stored in the graph, not a Python script. Python is I/O glue only. Intelligence, logic, routing, decisions, scheduling, sync — all graph traversal.

### Continuous crystallization
True time crystals don't wait for a clock. They crystallize on contact. Every MERGE triggers the full digest-excrete-heal chain in the same transaction. The graph heals at the speed of change, not the speed of cron.

### Topology compounding
The system compounds through three layers: (1) Human redefines topology through conversation, (2) LLM ingests raw data and generates strategies for free ingestion, (3) Scripts execute ongoing ingestion at zero token cost. Each conversation makes the graph smarter AND makes future ingestion cheaper.

### Pay tokens once, then the structure thinks for free
LLMs convert unstructured text into graph nodes and edges. Once structured, all intelligence — convergence detection, dream healing, contradiction detection — is graph traversal. Zero tokens. You pay to build neurons, not to think.

### Test-driven: every graph change is testable via traversal
Before adding a node type or edge — define the Cypher query that tests it works. The test IS the traversal.

### Files are bootstrap pointers
CLAUDE.md and .claude/rules/ files are thin pointers that tell the system to query the graph. They contain no content that duplicates graph state.

### Ingestion triggers digestion
Every signal that enters the graph immediately triggers structural digestion. Keyword linking, person attribution, convergence checking happen in the same transaction.

### Parallel by topology
The graph reveals parallel execution tracks through its topology. If two WorkItems share no edges, they run in parallel. The graph IS the parallelization strategy.

### Graph-first operating
Query the graph before acting. If it's not in the graph, it doesn't exist to the system.

---

## Invariants

1. **Write Isolation** — the system writes to its own domain only
2. **Distribution Gate** — human reviews before distributing to team repos
3. **Pipeline Allowlist** — only authorized scripts execute
4. **Boundary Integrity** — external signals validated before ingestion
5. **Least Privilege** — minimum permissions for each operation
6. **Cypher-Native Intelligence** — intelligence as graph traversal, not Python logic
7. **Graph-Native System State** — all state in the graph, not in files
8. **Real-Time Ingestion** — signals processed on arrival, not batched
9. **Cypher-Native Protocol** — protocols execute as stored Cypher

---

## The Execution Loop

```
Every MERGE (continuous, not batched):
  → Health score recomputes
  → Failing gap-closure tests re-evaluate
  → If gap closed → test flips PASS → score rises

Every 30 minutes (heartbeat):
  → 31 protocols execute in sequence
  → Detect gaps (5 protocols)
  → Heal gaps (9 protocols)
  → Create TDD tests for gaps (1 protocol)
  → Propose unblocked work (1 protocol)
  → Sync GitHub issues (1 protocol)
  → Route knowledge (1 protocol)
  → Dream: infer hidden connections (1 protocol)
  → Learn: measure if inferences were useful (1 protocol)
  → Snapshot: capture state for immune system (1 protocol)
  → Immune check: verify no unauthorized mutations (1 protocol)
  → Report: count nodes, edges, test health (1 protocol)
  → 87 tests validate everything above

On session start (team member opens Claude):
  → 3 bridge rules fire
  → Intent → market evidence surfaced
  → Demand → competitive context surfaced
  → Architecture → competitor capabilities surfaced
```

---

## The Crystallization Pattern

```
Human says something
  → LLM understands, designs topology
    → Cypher MERGE creates structure
      → Structure runs at zero cost forever
        → Next session inherits the crystal
          → Human says something new
            → New crystal compounds with all existing crystals
              → Escape velocity
```

Each crystal: runs without LLM, produces outputs that feed other crystals, attracts new connections through dream rounds, gets validated by TestCase crystals, and heals itself when damaged.

---

## The Gap-to-Execution Engine

Every gap the graph finds becomes:
1. A **TestCase** (FAIL) — what DONE looks like
2. An **ActionProposal** — what needs to happen
3. A **VALIDATES** edge — connecting test to the gap

When a human closes the gap → test flips PASS → downstream unblocks → next gap surfaces → repeat.

20 gap-closure tests currently failing. That IS the roadmap. Generated by topology, not by opinions.

---

## Health

The graph computes its own health score (0-100):
- 80+ = HEALTHY (immune response stands down)
- 60-79 = DEGRADED (healing protocols active)
- 40-59 = UNHEALTHY (autonomous healing triggered)
- <40 = CRITICAL (alert)

Current: 67 DEGRADED. 59/87 tests passing. 0/20 gap-closure tests passing.

The graph knows it's not healthy. It's working on it.

---

*This file is a snapshot. The graph is the living version. Query it:*
```cypher
MATCH (p:Principle) RETURN p.label, p.description
MATCH (hc:HealthCheck {node_id: 'healthcheck-latest'}) RETURN hc.score, hc.status
MATCH (tc:TestCase {category: 'gap-closure'}) WHERE tc.last_result = 'fail' RETURN tc.label
```
