# Mycelium — teammate's Claude context

You are Claude Code running inside a teammate's clone of `Qubit-Capital/maverick` — the team distribution of Mycelium, the living knowledge graph. This file tells you everything you need to work effectively here without going outside the repo.

**Read this once. After that, everything you do flows through the graph.**

> **New to this repo?** Read [`AGENTS.md`](AGENTS.md) first — it's the two-minute "what is this, how do I use it" for agents and humans, including the one-line install.

---

## The primary loop: read the shared graph before coding

The team's decisions, protocols, invariants, and evidence live in a shared Neo4j graph on `delta-server` (143.110.226.214:7687, container: `mycelium-neo4j`). Pulse-server is off-limits for all SeedForth ecosystem operations. Before you build, research, or recommend anything — ask the graph what it already knows.

```bash
# Direct query via SSH to delta-server Neo4j
ssh delta-server "docker exec mycelium-neo4j cypher-shell -u neo4j -p '<password>' '<cypher>'"

# Or via local mycelium CLI configured with delta-server target
mycelium --target delta ask "has the team decided on <topic>"
mycelium --target delta ask "what patterns exist for <problem>"
mycelium --target delta shell "MATCH (d:Decision) WHERE d.area='<area>' RETURN d.label, d.rationale"
```

The graph is authoritative. If this file (or any file in the repo) disagrees with what the graph says, trust the graph.

---

## The targets

| target | bolt | mode | purpose |
|---|---|---|---|
| **`local`** | `bolt://localhost:7687` | **rw** | the teammate's own laptop — safe to edit/break |
| **`delta`** | `bolt://143.110.226.214:7687` | **rw** | SeedForth ecosystem graph on delta-server (container: `mycelium-neo4j`), Neo4j 5.26 Community |
| **`falkor`** | `redis://143.110.226.214:6380` | **rw** | FalkorDB on delta-server (container: `docker-falkordb-1`) for Redis-protocol graph operations |

Pulse-server (5.78.206.137) is **off-limits** for all SeedForth operations.

No `--target` flag defaults to `local`.

---

## What the teammate can do from here

```bash
# Semantic search (zero LLM cost — local Ollama nomic-embed-text + Qdrant)
mycelium --target delta ask "<question>"

# Raw Cypher
mycelium --target delta shell "<cypher>"

# Live status — Beings, heartbeat, invariants
mycelium --target delta status

# Pull the current delta graph into local for experimentation
mycelium fork delta

# See what local differs from delta
mycelium drift --from delta

# Pull delta→local changes additively (MERGE, no destructive wipes)
mycelium sync --from delta
```

---

## Contributing changes (the only path to mutate dev)

Writes to dev are not live-pushable. The promote path is cypher-as-code in this repo:

1. Branch: `git checkout -b feature/<username>/<short-desc>`
2. Edit `.cypher` in `graph/protocols/` (executable atoms fired by heartbeat) or `graph/knowledge/` (schema/state — :Purpose, :Invariant, :FractalEcho, etc.). Every cypher file must start with `// @node_id:` + `// @label:` headers — `mycelium bootstrap` uses them.
3. Test locally: `mycelium --target local shell < graph/knowledge/<your-file>.cypher`
4. Sanity: `mycelium --target local shell "<query that proves it landed>"`
5. `mycelium drift --from dev` to preview what you're proposing
6. Push, open PR against `kagrawal29/mycelium:main` (that's the upstream core; `Qubit-Capital/maverick` syncs from it)
7. Merge → autodeploy pulls the PR onto `delta-server` and runs `mycelium bootstrap` against delta → the next 30s heartbeat picks up changes

### Three merge gates (why a PR gets rejected)

1. **Forest Promise** — every node carries `{project: X}`; no silent cross-subgraph edges. See `:SovereigntyRule` nodes in the graph.
2. **Test coverage** — new Protocols need a TestCase; new Invariants need a `heal_protocol`.
3. **Idempotence** — use `MERGE` not `CREATE`; no unguarded `DETACH DELETE`; constraints/indexes wrapped in `IF NOT EXISTS`.

Full details with exact reject reasons: `docs/TEAM_GUIDE.md`.

---

## What's on disk vs what's in the graph

| location | source of truth for |
|---|---|
| `graph/protocols/*.cypher` | Protocol nodes (heartbeat-fireable behaviors) — `bootstrap` MERGEs them in |
| `graph/knowledge/*.cypher` | Knowledge/state nodes (invariants, promises, templates, unlocks) |
| `graph/signals/*.cypher` | Accumulated trace/hebbian signals — ingest protocol absorbs them on heartbeat |
| `docs/*.md` | Human-facing documentation (teammate workflow, windows setup, credentials) |
| `scripts/*.py` | I/O glue (embed, panel, qdrant sync, ingest) |
| `mycelium` (root) | Bash CLI dispatcher — routes to atom runner or special commands |
| Neo4j on delta-server | **THE SOURCE OF TRUTH for runtime** — container `mycelium-neo4j` on delta-server (143.110.226.214:7687) |

Files are bootstrap pointers. The graph doesn't get stale. Files do. When in doubt: **query the graph**.

---

## The minimum faculty set (Being Template v1)

Every sovereign `:Being` in the forest must carry these five, scoped with `{project: X}`:

1. `:Purpose` — why this Being exists
2. `:Invariant` with `heal_protocol` — what must stay true + how to self-repair
3. `:TestCase` — a claim the Being verifies about itself
4. `:WorkItem` — where it's going next
5. `:Protocol` with `schedule` — what it does on each heartbeat

If you're adding a new scope (new sub-project), you need all five. The invariant `invariant-being-has-full-faculties` enforces this.

---

## Operating model (how work flows)

```
GitHub issue created
  → WorkItem node in graph
    → DEPENDS_ON edges from "depends on #N" in issue body
      → dream round detects unblocked WorkItems
        → :ActionProposal surfacing the work
          → human executes, closes issue
            → WorkItem status auto-syncs to 'done'
              → downstream items unblock on next heartbeat
```

The graph plans its own evolution. Your role is execution, not orchestration.

---

## Platform note (Windows)

If the teammate is on Windows, they're running this via **WSL2 with Ubuntu**. The `mycelium` CLI + Neo4j tools + Ollama are Unix-native; native Windows isn't supported. Inside the Ubuntu shell everything works identically to macOS/Linux.

If a command fails with *"bash: command not found"* or *"/bin/sh: mycelium: No such file"*, the teammate may be running in PowerShell/cmd instead of WSL — redirect them to `docs/windows-setup.md`.

---

## Rules of engagement

- **Think in graph, not files and scripts.** The graph is the program. New behavior, cadence, capability, and decisions are authored as `:Protocol` / `:CypherAtom` / `:Knowledge` / `:Model` nodes and executed by `graph-runner.py` on its cadences — not as Python scripts or config files. Files/scripts are only for external I/O (`:ExternalAtom`): webhooks, sending messages, downloading attachments. Before writing a script, ask whether it should be a graph node instead.
- **Graph is source of truth** — `:Decision`, `:Invariant`, `:Protocol`, `:FailureMode` nodes in the shared graph are authoritative. Files, GitHub issues, memory, CLAUDE.md — all are *external surfaces* of the graph, never substitutes. If they disagree with the graph, trust the graph and update them.
- **Scope isolation (enforced by `:Invariant invariant-scope-isolation`).** Every node you author for the shared (dev/prod) graph MUST carry `scope ∈ {team, product}`. `scope='personal'` is forbidden on shared graphs — personal-continuity state (session handoffs, per-architect TODOs, session narratives) stays in your **local** Neo4j + your local memory file. `:Protocol protocol-scope-isolation-check` fires on every heartbeat and surfaces violations as `:ActionProposal`. If your node appears there, fix it.
- **Deploy flow (enforced by `:Decision decision-deploy-flow-v1` + `:Invariant invariant-prod-admin-only`).** Teammate → PR to `dev` branch → autodeploy to delta graph → admin reviews → admin opens PR `dev → main` → admin manually triggers prod autodeploy. Never PR directly to `main`. Never hot-patch delta-server graph. Prod bootstraps are admin-triggered only.
- **Never accept pasted secrets** in chat. Redirect to a separate terminal.
- **Never write to dev or prod directly** from the CLI — the proxy blocks it anyway; attempts poison your bolt session.
- **Never create without MERGE** on signal/knowledge nodes (dedup matters).
- **Max 3 parallel agents** against local Neo4j (1G heap limit).
- **Kill long-running scripts before reporting "done"** — stale processes race each other.
- **Query the graph before coding** — forty-plus decisions already exist; don't re-litigate.
- **Verify cypher lands before claiming done.** Bootstrap skips silently on parse errors today (wi-sync-05 / #76 will fix). After MERGE, query the node back from the graph to confirm — otherwise your edit is invisible.

---

## Common queries (paste-and-go)

```bash
# What is the state of everything?
ssh delta-server "docker exec mycelium-neo4j cypher-shell -u neo4j -p '<password>' 'MATCH (p:Project) RETURN p.name, p.status, p.category, p.runtime ORDER BY p.category, p.status, p.name'"

# What is active right now?
ssh delta-server "docker exec mycelium-neo4j cypher-shell -u neo4j -p '<password>' 'MATCH (p:Project) WHERE p.status = \"active\" RETURN p.name, p.description, p.runtime'"

# What servers do we have and what runs on them?
ssh delta-server "docker exec mycelium-neo4j cypher-shell -u neo4j -p '<password>' 'MATCH (s:Server) OPTIONAL MATCH (s)-[:HAS_SERVICE]->(svc:Service) OPTIONAL MATCH (a:Agent)-[:RUNS_ON]->(s) RETURN s.name, collect(DISTINCT svc.name) AS services, collect(DISTINCT a.name) AS agents'"

# What depends on what?
ssh delta-server "docker exec mycelium-neo4j cypher-shell -u neo4j -p '<password>' 'MATCH (a)-[:DEPENDS_ON]->(b) RETURN a.name, labels(a)[0], b.name, labels(b)[0]'"

# Which projects have repos?
ssh delta-server "docker exec mycelium-neo4j cypher-shell -u neo4j -p '<password>' 'MATCH (p:Project)-[:HAS_REPO]->(r:Repository) RETURN p.name, r.full_name'"

# What are all available CypherAtoms (LLM interaction surface)?
ssh delta-server "docker exec mycelium-neo4j cypher-shell -u neo4j -p '<password>' 'MATCH (ca:CypherAtom) RETURN ca.node_id, ca.semantic, ca.fire_count ORDER BY ca.node_id'"

# Execute a CypherAtom directly:
ssh delta-server "docker exec mycelium-neo4j cypher-shell -u neo4j -p '<password>' '<paste cypher from atom>'"

# Forest constitution — rules and invariants:
ssh delta-server "docker exec mycelium-neo4j cypher-shell -u neo4j -p '<password>' 'MATCH (promise:ForestPromise)-[:DECLARES]->(r:SovereigntyRule) RETURN r.node_id, r.rule, r.severity ORDER BY r.severity DESC'"

# Delta-managed projects status:
ssh delta-server "docker exec mycelium-neo4j cypher-shell -u neo4j -p '<password>' 'MATCH (p:Project {category: \"delta-managed\"}) RETURN p.name, p.status, p.project_type ORDER BY p.status, p.name'"
```

---

## Current State (2026-07-22)

**Graph live on delta-server** (bolt://143.110.226.214:7687, container `mycelium-neo4j`).

- **158 nodes, 184 edges, density 1.16** — 9/9 invariants passing
- **9 Invariants** with `check_cypher` and `heal_protocol`. Each verifiable via cypher traversal.
- **9 TestCases** with `assertion_cypher` returning `{actual, expected, pass}`. Each validates one invariant.
- **18 CypherAtoms** — the LLM interaction surface. Atomic, named, semantic cypher queries.
- **2 Protocols** — `protocol-ecosystem-status` (ecosystem map) + `protocol-run-tests` (test runner)
- **46 Projects** (23 SeedForth + 22 delta-managed)
- **3 Agents:** Tetrahedron, Delta, AudioWorld/Charlie
- **2 Servers:** delta-server (10 services), charlie-server (2 services)
- **13 Repositories** — all mapped to projects

### Design invariants (the 9 things the graph enforces)
1. `inv-nodes-have-project` — every core node carries `{project: X}`
2. `inv-graph-density` — edges/node >= 0.8
3. `inv-server-has-services` — every server has services listed
4. `inv-atom-has-semantic` — every CypherAtom has description
5. `inv-project-with-repo-has-repo-edge` — projects with repos link to them
6. `inv-every-invariant-has-test` — meta-invariant: tests for all invariants
7. `inv-graph-is-source-of-truth` — the graph doesn't lie about service health
8. `inv-cross-domain-edges-typed` — all cross-project edges use allowed bridges
9. `inv-agent-has-server` — every agent tethered to a server

### Bootstrap files
- `graph/knowledge/seedforth-forest-foundation.cypher` — ForestPromise, Being, SovereigntyRules, Concepts, Scales
- `graph/knowledge/seedforth-ecosystem-map.cypher` — Servers, Services, Projects, Agents, Repos, cross-connections, initial CypherAtoms
- `graph/knowledge/seedforth-invariants-tests.cypher` — 9 Invariants + 9 TestCases + test-runner protocol
- `graph/knowledge/seedforth-ecosystem-fixes.cypher` — charlie-server services + missing repo links (debt paid)

### CypherAtom — the LLM interaction surface

CypherAtom is the basic unit of interaction between LLM and graph. Each atom has:
- `node_id` — unique identifier (e.g. `atom-status-all`)
- `semantic` — natural language description for discovery
- `cypher` — the executable query body
- `fire_count` — Hebbian weight (incremented on each execution)

LLMs discover atoms by semantic search, compose them via `:FOLLOWS` chains, and feed results between them via `:FEEDS` edges. The LLM never writes raw cypher — it discovers pre-existing atoms and composes them.

---

## Where to go deeper

- `docs/TEAM_GUIDE.md` — full teammate guide with git flow, merge rules, fallback playbook
- `docs/windows-setup.md` — Windows/WSL2 setup
- `docs/credentials.md` — credential rotation and security
- `CONTRIBUTING.md` — branching model, coding standards
- `MYCELIUM.md`, `OPERATING-SYSTEM.md` — architecture deep dives
- `graph/knowledge/seedforth-forest-foundation.cypher` — the constitution
- `graph/knowledge/seedforth-ecosystem-map.cypher` — the map
- `graph/protocols/*.cypher` — the DNA of the system (read them like source code)

Always query the graph first: `ssh delta-server "docker exec mycelium-neo4j cypher-shell -u neo4j -p '<password>' '<cypher>'"`
