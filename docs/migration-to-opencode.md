# Delta → SuperAgent: opencode + Mycelium Migration Spec
## v3 — resolved all v2 blockers

**Authors:** Team Lead (orchestrator), Systems Architect, Graph Engineer, Platform/Infra Engineer, Backend Engineer
**Status:** FINALIZED — unanimous team alignment achieved. Approved for sprint planning.
**Last revised:** 2026-07-21
**v3 changes:** Supervisor template fields, setup script ordering, hibernate/stop semantics,
  anti-stacking redesign, auth error channel, hub dispatch, write-path tooling, bootstrap
  Cypher fixes, backup scope, token enforcement deferral, embedding plan

---

## 1. Vision

Delta evolves from a Discord bot spawning Claude Code agents into a **SuperAgent** — the
orchestrating consciousness above the SeedForth fleet. Three pillars:

- **opencode** replaces Claude Code as the agent runtime. opencode runs persistently per
  project (managed by supervisord), communicating via a hybrid model: file-based inbox/outbox
  for async message delivery + HTTP health checks and nudges. Same model across all agents
  (DeepSeek).
- **Mycelium** becomes the unified intelligence layer. Every agent reads from the living
  knowledge graph (Neo4j, read-only via the `mycelium` Go binary). Agents write facts to a
  local Neo4j staging instance on delta-server. A nightly promotion job validates, commits
  to git, opens a PR, and bootstraps to the shared dev graph. Memory is shared, context is
  compacted into graph nodes, decisions are tracked with full Merkle lineage.
- **Organizational structures** are modeled in the graph. Each entity (SeedForth, SolveOS,
  FlowingIndian, etc.) has departments, roles, and agentic assignments. The graph maps who
  does what, powered by mycelium's existing `:Subagent`, `:Knowledge`, and federation types.

The Sutradhaar constitution (superagent/CONSTITUTION.md) defines the superagent's identity:
it conducts energy (leverage → autonomy), senses the fleet through mycelium, and reshapes the
portfolio. Delta is the execution platform that hosts this consciousness. The Hub agent
(Phase 7) embodies this constitution — a primary agent with fleet-wide awareness.

---

## 2. Target Architecture

```
                         Discord / Slack / Web
                               │
                               ▼
                     ┌─────────────────────┐
                     │   Delta (app.py)    │  ← Discord bot, message router
                     │  SuperAgent host    │     systemd: delta.service
                     └────────┬────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
    ┌────────────┐    ┌────────────┐    ┌────────────┐
    │ supervisord│    │ supervisord│    │ supervisord│
    │ opencode   │    │ opencode   │    │ opencode   │
    │ serve:7701 │    │ serve:7702 │    │ serve:7703 │
    │ web:7901   │    │ web:7902   │    │ web:7903   │
    │ Hub Agent  │    │ Project A  │    │ Project B  │ ...
    └─────┬──────┘    └─────┬──────┘    └─────┬──────┘
          │                 │                  │
          │  inbox/outbox   │   inbox/outbox   │  inbox/outbox
          │  (file bridge)  │   (file bridge)  │  (file bridge)
          │                 │                  │
          └────────┬────────┴────────┬─────────┘
                   │                 │
                   ▼                 ▼
         ┌──────────────────┐   ┌──────────────────────┐
         │ Mycelium (Neo4j) │   │ Local Neo4j (staging) │
         │ pulse-server     │   │ delta-server:7687     │
         │ dev:7698 ro      │   │ agent writes land here│
         └────────┬─────────┘   └──────────┬───────────┘
                  │                        │
                  │   nightly promotion    │
                  │   (validate → commit   │
                  │    → PR → merge →      │
                  │    bootstrap)          │
                  └────────────┬───────────┘
                               │
                  ┌────────────┴────────────┐
                  │                         │
                  ▼                         ▼
        ┌──────────────────┐     ┌──────────────────────┐
        │  Qdrant (vector) │     │  Tools / MCP         │
        │  delta:6333      │     │  Rube (Google)       │
        │  sem search      │     │  Unipile (LinkedIn)  │
        └──────────────────┘     │  Vercel (deploy)     │
                                 │  GitHub (repos)      │
                                 │  Browser CDP         │
                                 └──────────────────────┘
```

### Key changes from current architecture

| Before (Claude Code) | After (opencode) |
|---|---|
| tmux + `claude --dangerously-skip-permissions` per project | supervisord-managed `opencode serve` per project |
| Inbox/outbox JSON file bridge + tmux nudge | Same file bridge, but nudge via HTTP health endpoint + file write detection |
| Claude OAuth token for LLM auth | DeepSeek API key in delta.env, passed as env var to serve process |
| Claude `mcp add-json` for tool registration | Static MCP config in per-project `opencode.jsonc` (outside git root) |
| `.claude/settings.json` PostToolUse hooks | opencode `todowrite` tool + Delta-side progress polling |
| Claude Code TUI in web terminal (ttyd) | `opencode web --port` per project for debug access |
| Per-project Linux user + symlinked `.claude` auth | Per-project Linux user + per-user `auth.json` copy + symlinked global config |
| Direct agent access to Anthropic API | All agents through opencode, DeepSeek provider |
| No shared intelligence layer | Mycelium graph (read) + local Neo4j staging (write) |

---

## 3. opencode Migration: The Mechanics

### 3.1 Hybrid model: file bridge preserved, agent launch replaced

**Decision:** The file-based inbox/outbox bridge is preserved for async message delivery.
Only the agent launch mechanism changes from tmux/send-keys to supervisord-managed opencode.

**Why not pure HTTP bridge:** The current file bridge provides natural message queueing
(multiple inbox files stack up; agent processes one at a time), silence/nudge detection
(Delta knows when the agent last read inbox), anti-stacking guards (don't nudge while agent
is processing), and follow-up scheduling. A synchronous HTTP POST model would require
rebuilding all of these from scratch. The file bridge works and is battle-tested.

**What changes:**
- The agent process is `opencode` (not `claude`)
- It runs under supervisord (not tmux)
- The nudge mechanism changes from tmux `send-keys` to a lightweight HTTP health check
  that also signals "check your inbox"
- opencode's native tool set replaces Claude Code's tool set
- Progress tracking moves from file-based hooks to opencode `todowrite` polling

**What stays:**
- app.py writes inbox JSON files per Discord message
- app.py polls outbox directory for agent responses
- Watcher threads for outbox, silence, followups
- Conversation logging in `delta-config/logs/`
- Schedule management via `schedule.json`
- Linux user isolation (`proj-{name}` sandboxes)

### 3.2 Agent lifecycle (replaces lifecycle.py)

**Old flow:**
```
provisioner creates tmux session
  → lifecycle.py writes token file to /tmp/
  → sends `claude --dangerously-skip-permissions` via tmux send-keys
  → Claude Code runs in TUI
  → bridge nudges via send-keys to read inbox
  → agent reads inbox file, writes outbox file
  → app.py polls outbox, sends to Discord
```

**New flow:**
```
provisioner writes supervisor config
  → supervisorctl starts opencode serve as proj-{name}
  → opencode runs in serve mode (headless, no TUI)
  → bridge writes inbox file on Discord message
  → bridge sends HTTP health check + nudge signal
  → agent reads inbox file, writes outbox file
  → app.py polls outbox, sends to Discord
```

### 3.3 Process management: supervisord

**Decision:** supervisord, not systemd template units or bare subprocess.Popen.

**Rationale:**
- supervisord is designed for dynamic child process management from a controlling process
- No `systemctl daemon-reload` on every project create/destroy (global operation, fragile)
- Built-in process restart (autorestart=true), log capture (stdout_logfile, stderr_logfile),
  health checks
- Survives server reboot without Delta needing to restore anything
- `supervisorctl update` is lightweight — just rereads config directory

**Setup (included in setup-server.sh):**
```bash
apt install -y supervisor
```

**Per-project config template** (`/etc/supervisor/conf.d/proj-{name}.conf`):
```ini
[program:proj-{name}]
command=opencode serve --port {serve_port}
user=proj-{name}
directory=/home/proj-{name}/{name}
environment=PATH="/usr/local/bin:/usr/bin:/bin",DEEPSEEK_API_KEY="{deepseek_key}",OPENROUTER_API_KEY="{openrouter_key}",RUBE_BEARER_TOKEN="{rube_token}",GITHUB_TOKEN="{github_token}",VERCEL_TOKEN="{vercel_token}",UNIPILE_DSN="{unipile_dsn}",UNIPILE_API_KEY="{unipile_key}",COMPOSIO_API_KEY="{composio_key}",MYCELIUM_TARGET="dev",LOCAL_NEO4J_URI="bolt://localhost:7687",LOCAL_NEO4J_USER="neo4j",LOCAL_NEO4J_PASSWORD="{local_neo4j_password}"
autostart=true
autorestart=true
startsecs=5
stopwaitsecs=10
memory_max=512M
stdout_logfile=/home/proj-{name}/{name}/delta-config/logs/opencode-stdout.log
stderr_logfile=/home/proj-{name}/{name}/delta-config/logs/opencode-stderr.log
redirect_stderr=false
```

**Lifecycle functions** (rewritten `agent_lifecycle.py`):
```python
def start_agent_serve(project_name: str, serve_port: int) -> bool:
    """Write supervisor config and start the opencode serve process."""
    config_path = f"/etc/supervisor/conf.d/proj-{project_name}.conf"
    write_config(config_path, project_name, serve_port)
    subprocess.run(["supervisorctl", "update"], check=True)
    subprocess.run(["supervisorctl", "start", f"proj-{project_name}"], check=True)
    return _wait_for_healthy(serve_port, timeout=30)

def stop_agent_serve(project_name: str, keep_config: bool = True) -> bool:
    """Stop the serve process. If keep_config=False (teardown), remove supervisor config.
    If keep_config=True (hibernate), stop only — config preserved for restore."""
    subprocess.run(["supervisorctl", "stop", f"proj-{project_name}"])
    if not keep_config:
        config_path = f"/etc/supervisor/conf.d/proj-{project_name}.conf"
        Path(config_path).unlink(missing_ok=True)
        subprocess.run(["supervisorctl", "update"])

def is_agent_running(serve_port: int) -> bool:
    """Health check via HTTP GET /global/health."""
    try:
        resp = requests.get(f"http://127.0.0.1:{serve_port}/global/health", timeout=5)
        return resp.status_code == 200 and resp.json().get("healthy", False)
    except requests.RequestException:
        return False

def get_agent_health(serve_port: int) -> dict:
    """Full health status including session info."""
    try:
        resp = requests.get(f"http://127.0.0.1:{serve_port}/global/health", timeout=5)
        return {"agent_running": True, "response_ms": resp.elapsed.total_seconds() * 1000}
    except requests.RequestException:
        return {"agent_running": False}
```

### 3.4 Inbox/outbox file bridge (preserved)

The file bridge from `project_bridge.py` is preserved with minimal changes:

**Inbox write** (unchanged):
```python
def write_inbox(project_name: str, channel_id: str, user_id: str, text: str):
    msg_id = str(uuid.uuid4())
    msg = {"msg_id": msg_id, "channel_id": channel_id, "user_id": user_id,
           "text": text, "ts": datetime.utcnow().isoformat()}
    inbox_dir = f"/home/proj-{project_name}/{project_name}/delta-config/inbox"
    Path(inbox_dir).mkdir(parents=True, exist_ok=True)
    (Path(inbox_dir) / f"{msg_id}.json").write_text(json.dumps(msg))
    _log_exchange(project_name, "in", msg)
    return msg_id
```

**Outbox polling** (unchanged): polls `delta-config/outbox/` every 1s for new JSON files.

**Nudge mechanism** (changed): Instead of tmux `send-keys`, send an HTTP health check with
a nudge flag. If opencode serve exposes a custom endpoint or we use a file-based nudge
signal, the agent checks the inbox. Simplest approach: the agent's system prompt instructs
it to periodically check the inbox directory. The nudge just writes a `.nudge` flag file
that the agent watches for.

```python
def nudge_agent(project_name: str, serve_port: int):
    """Signal the agent to check inbox. Uses file flag + optional HTTP health check."""
    nudge_file = Path(f"/home/proj-{project_name}/{project_name}/delta-config/.nudge")
    nudge_file.touch()
    # Also poke the serve to wake it if idle
    try:
        requests.get(f"http://127.0.0.1:{serve_port}/global/health", timeout=5)
    except requests.RequestException:
        pass
```

**Progress tracking** (changed): Instead of `watch_progress()` polling a directory written
by PostToolUse hooks, poll opencode's todo endpoint:

```python
def watch_progress(project_name: str, serve_port: int):
    """Poll opencode session todo list for work-in-progress status."""
    while True:
        time.sleep(5)
        try:
            resp = requests.get(
                f"http://127.0.0.1:{serve_port}/session/{session_id}/todo",
                timeout=5
            )
            if resp.status_code == 200:
                todos = resp.json()
                in_progress = [t for t in todos if t.get("status") == "in_progress"]
                if in_progress:
                    # show "working on: X" to Discord if changed
                    ...
        except requests.RequestException:
            pass
```

### 3.5 opencode.jsonc config layout

**Config merge order** (opencode resolution): Project-level > User-level > Global

**Location 1 — Global** (`/root/.config/opencode/opencode.jsonc`):
Shared baseline. Sets model default, global auto-approve permission, mycelium custom tools.
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "model": "deepseek/deepseek-v4-pro",
  "permission": {
    "*": "allow"
  },
  "custom_tool": {
    "mycelium_ask": {
      "description": "Query the shared knowledge graph with a natural language question",
      "parameters": {
        "type": "object",
        "properties": {
          "question": {"type": "string"},
          "target": {"type": "string", "enum": ["dev", "prod"], "default": "dev"}
        }
      },
      "command": ["mycelium", "--target", "${target}", "ask", "${question}"]
    },
    "mycelium_query": {
      "description": "Run a read-only Cypher query against the shared knowledge graph",
      "parameters": {
        "type": "object",
        "properties": {
          "cypher": {"type": "string", "description": "Read-only Cypher query"}
        }
      },
      "command": ["mycelium", "--target", "dev", "shell", "${cypher}"]
    }
  }
}
```

**Location 2 — User-level** (`/home/proj-{name}/.config/opencode/opencode.jsonc`):
Symlinked to `/root/.config/opencode/opencode.jsonc`. All project users share the global
config baseline via this symlink. The provisioner creates this during `create_user()`.

**Location 3 — Project-level** (`/home/proj-{name}/{name}/opencode.jsonc`):
Per-project overrides. Contains project-specific MCP config (Rube, Qdrant), agent
definitions, and model overrides. **MUST be in `.gitignore`** — this file contains
environment variable references to secrets.

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "model": "deepseek/deepseek-v4-pro",
  "mcp": {
    "rube": {
      "type": "remote",
      "url": "https://rube.app/mcp",
      "headers": {
        "Authorization": "Bearer {env:RUBE_BEARER_TOKEN}"
      }
    },
    "qdrant-memory": {
      "type": "local",
      "command": ["mcp-server-qdrant"],
      "environment": {
        "QDRANT_URL": "http://143.110.226.214:6333",
        "COLLECTION_NAME": "tetrahedron-memory",
        "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2",
        "QDRANT_ALLOW_ARBITRARY_FILTER": "true"
      }
    }
  },
  "agent": {
    "build": {
      "mode": "primary",
      "model": "deepseek/deepseek-v4-pro",
      "permission": {"*": "allow"},
      "prompt": "{file:./CLAUDE.md}"
    }
  }
}
```

### 3.6 Auth.json deployment

Per-user copies (not shared symlinks). The provisioner copies auth.json from
`/opt/delta/auth.json.template` (gitignored, deployed by setup-server.sh) to
`/home/proj-{name}/.local/share/opencode/auth.json` with `chmod 600` and
`chown proj-{name}:`.

```json
{
  "deepseek": {
    "type": "api",
    "key": "sk-..."
  }
}
```

DeepSeek API key is also passed as environment variable `DEEPSEEK_API_KEY` in the
supervisor config, so opencode can use either auth.json or env var. The env var in
supervisor config is the primary delivery mechanism; auth.json is the fallback.

### 3.7 opencode web terminal (replaces ttyd)

Each project gets an optional web terminal for debug access:

```bash
opencode web --port {web_port} --hostname 0.0.0.0
```

Web ports (7900+) require firewall rules:
```bash
ufw allow 7900:8099/tcp
```

The serve process (localhost-only, port 7700+) does NOT need firewall rules.

### 3.8 Port allocation

| Range | Purpose | Bind address | Firewall |
|---|---|---|---|
| 7700-7899 | opencode serve (agent API) | 127.0.0.1 | None |
| 7900-8099 | opencode web (debug terminal) | 0.0.0.0 | ufw allow |

**Allocation:** The provisioner calls `_allocate_port()` which finds the lowest unused port
in the appropriate range using the registry. `ProjectInfo` stores both `serve_port` and
`web_port` (nullable — web terminal is optional per project).

---

## 4. Mycelium Integration: The Intelligence Layer

### 4.1 Why mycelium

Currently, each Delta agent works in isolation. They maintain their own SEED.md, their own
conversation logs, their own mental model. Knowledge never crosses project boundaries.

Mycelium is a living Neo4j graph (47k+ nodes on dev) that:
- Stores decisions, invariants, protocols, work items, test cases
- Self-heals via an immune system (invariants with heal_protocols)
- Learns from its own operation (Hebbian — fire together, wire together)
- Supports federation (import external graphs with `:Source` + `:Imported` + `:Adopted`)
- Is self-describable (generates its own documentation via `mycelium docs`)
- Has Merkle integrity (cryptographic chain of state via `:Species` + `:WitnessSignature`)
- Is read-only to all consumers (bolt-proxy rejects writes on dev/prod)

The `mycelium` Go binary is the access point. It is a single compiled artifact with embedded
read-only credentials. Install from `kagrawal29/mycelium` releases. One binary, zero
dependencies (no Python, no JRE, no Neo4j client). Available on PATH for all agents.

### 4.2 How agents use mycelium

Every opencode agent has access to the `mycelium` CLI via custom tools (Section 3.5).

**All agents MUST query mycelium before making decisions:**
```bash
mycelium --target dev ask "has the team decided on <topic>"
mycelium --target dev shell "MATCH (k:Knowledge) WHERE k.category = '<category>' RETURN k.label, k.insight"
```

**Read path** (Phase 4, immediate):
- `mycelium ask` — semantic search via Ollama embeddings + Qdrant, returns top matches
- `mycelium shell` — read-only Cypher, client-side write-verb rejection + server-side bolt-proxy
- `mycelium status` — current chain head, invariant health, test status
- `mycelium doctor` — connectivity check, responds within seconds

**Write path** (Phase 4, nightly promotion):
- Agents write facts to a **local Neo4j staging instance** on delta-server
  (`bolt://localhost:7687` — write-enabled, isolated from shared graphs). Agents connect
  via a dedicated `mycelium-store` custom tool that wraps the Neo4j Python driver with
  a safe subset of operations (MERGE only, schema-validated, scoped by agent identity).
- **Nightly promotion job** (cron at 2am UTC):
  1. **Export**: `python3 /opt/delta/tools/export-staging.py` reads pending nodes from
     local Neo4j (filtered by `promoted = false`), generates `.cypher` files using
     MERGE statements with `// @node_id:` and `// @label:` headers (mycelium-compatible
     format). Each agent's mutations go to a separate file, grouped by `project` property.
  2. **Validate**: `bash /opt/mycelium/graph/runner/validate-merge.sh <file.cypher>`
     runs invariants + tests + Merkle recomputation in a single transaction against the
     `local` target. If validation fails, the file is rejected and logged for review.
  3. **Commit**: Validated `.cypher` files are committed to `kagrawal29/mycelium` on
     a branch named `agent-promotion/{date}`.
  4. **PR + Merge**: A PR is opened. Nightly CI runs `mycelium proof-of-merge` (dry-run
     validation). On green CI, PR is auto-merged.
  5. **Bootstrap**: Post-merge, CI runs `mycelium bootstrap --target dev` which MERGEs
     the new nodes into the dev graph.
  6. **Crystallize**: `mycelium-dev crystallize --target dev` runs the full crystallization
     pipeline: re-verify invariants + tests, mint a new Species, compute manifest_root,
     sign with witness keys, advance the chain head. This is the step that commits agent
     facts into Merkle-provenance state.
  7. **Mark promoted**: Update `promoted = true` on all exported nodes in local Neo4j.
- Agents query the dev graph (read-only via `mycelium` binary). Lag: 0-24 hours behind
  local writes (next nightly promotion).

**This preserves the Merkle chain, invariant validation, witness signatures, and audit
trail.** The crystallization step (step 6) was the missing piece in v2 — without it,
agent facts enter the dev graph but have no Species commitment, no manifest_root, and
no Merkle provenance. Added explicitly.

**`mycelium-store` custom tool** (Phase 4, agent write tool):
```jsonc
{
  "mycelium_store": {
    "description": "Store a fact in the local knowledge graph staging area. Writes are promoted to the shared graph during nightly promotion.",
    "parameters": {
      "type": "object",
      "properties": {
        "fact_type": {"type": "string", "enum": ["decision", "learning", "pattern", "workitem"]},
        "label": {"type": "string", "description": "Human-readable label"},
        "content": {"type": "object", "description": "Structured fact data (properties)"},
        "scope": {"type": "string", "description": "Owning organization"},
        "visibility": {"type": "string", "enum": ["fleet", "org", "private"]}
      }
    },
    "command": ["python3", "/opt/delta/tools/store-fact.py",
      "--type", "${fact_type}", "--label", "${label}",
      "--content", "${content}", "--scope", "${scope}", "--visibility", "${visibility}",
      "--project", "{project_name}", "--agent", "{agent_id}"]
  }
}
```

**`export-staging.py`** (Phase 4, nightly job): A Python script that connects to
local Neo4j at `bolt://localhost:7687`, reads all `(:Knowledge)` nodes with
`promoted = false`, groups them by `project` property, and generates MERGE Cypher
files with `// @node_id:` + `// @label:` headers compatible with mycelium's
bootstrap format. Runs as a cron job on delta-server.

### 4.3 Graph schema for the SeedForth fleet

**Node type strategy:** Use mycelium's existing `:Knowledge` type with `file_type` and
`category` properties, plus secondary labels for query convenience. Do NOT create standalone
label-only types outside the `:Knowledge` umbrella — existing protocols like
`protocol-semantic-classify` operate on `:Knowledge` and would be blind to new types.

```
(:Knowledge:Organization {file_type: "organization", entity_type: "earner|mission|client", status})
  -[:HAS_DEPARTMENT]-> (:Knowledge:Department {file_type: "department", purpose})
    -[:HAS_ROLE]-> (:Knowledge:Role {file_type: "role", responsibilities})
      -[:ASSIGNED_TO]-> (:Subagent {name, system_prompt, model, status})

(:Knowledge:Project {file_type: "project", entity_ref, github_repo, status})
  -[:BELONGS_TO]-> (:Organization)
  -[:HAS_AGENT]-> (:Subagent)

(:Subagent)-[:PRODUCES]-> (:Knowledge {file_type: "decision|learning|pattern|workitem"})
```

**Key design decisions:**
- `:Subagent` is a first-class mycelium type (MYCELIUM.md line 184) with `name, role,
  system_prompt, tools, owner` properties and `:TRACE` + `:USES_SKILL` edges
- `:Organization`, `:Department`, `:Role` are secondary labels on `:Knowledge` — the
  primary type is always `:Knowledge` so existing protocols process them
- `:Decision`, `:Learning`, `:Pattern` (the spec's original proposal) become
  `:Knowledge {file_type: "decision|learning|pattern"}` with optional secondary labels
- All agent-written compacted facts use `:Knowledge` as their primary label
- Every agent-written node carries `project`, `scope`, `visibility`, `compacted_at`,
  and `decay_protected` properties

**Decay protection:** The heartbeat decay protocol prunes unwalked edges. Agent-written
structural edges (`:BELONGS_TO`, `:PRODUCES`, `:ASSIGNED_TO`) carry `decay_protected: true`
so they persist. Compacted facts carry `compaction_retention_days` — after the retention
window, if never queried, decay applies. Frequently queried facts survive via Hebbian
strengthening (fire_count increments).

**Scope and visibility:**
```cypher
CREATE (k:Knowledge:Decision {
  scope: 'solveos',            -- owning org
  visibility: 'fleet',         -- 'fleet' = all, 'org' = same org, 'private' = this agent
  decay_protected: true,
  compaction_retention_days: 90
})
```

**Organizational mapping:**

| Organization | Entity Type | Departments | Roles |
|---|---|---|---|
| SeedForth | Earner | Delta SuperAgent, Client Delivery | Hub Orchestrator, Builder Agent, Onboarding Agent |
| SolveOS | Earner | Lead Gen, Matching, Outreach | LinkedIn Agent, Problem Matcher, Pipeline Manager |
| FlowingIndian | Earner | Marketing, Events, Payments | Content Agent, Event Agent, Payment Agent |
| SceneforthOS | Earner | Brand Intake, Campaign Gen, Payments | Creative Agent, Campaign Agent |
| Revti Digital | Client | LinkedIn Management | Charlie Agent, Ember Agent |
| Sutatva | Mission | Research, Media, Impact | Research Agent, Media Agent |
| Ashoonya | Mission | Coordination, Alignment | Community Agent |
| Prayogshala | Mission | Exploration, Discovery | Research Agent |

**Bootstrap Cypher** (runs once during Phase 4, seeded via mycelium PR flow):
```cypher
// Register concepts for semantic-classify (file_type required per existing convention)
CREATE (:Concept {node_id: 'concept-organization', file_type: 'concept',
  label: 'Organization', description: 'SeedForth organizational entities'})
CREATE (:Concept {node_id: 'concept-department', file_type: 'concept',
  label: 'Department', description: 'Organizational departments'})
CREATE (:Concept {node_id: 'concept-role', file_type: 'concept',
  label: 'Role', description: 'Agentic roles within an organization'})
CREATE (:Concept {node_id: 'concept-project', file_type: 'concept',
  label: 'Project', description: 'Delta platform project'})

// Concepts for agent-written Knowledge types (needed for SEEMS_LIKE classification)
CREATE (:Concept {node_id: 'concept-decision', file_type: 'concept',
  label: 'Decision', description: 'An agentic decision with rationale and outcome'})
CREATE (:Concept {node_id: 'concept-learning', file_type: 'concept',
  label: 'Learning', description: 'A lesson learned by an agent during execution'})
CREATE (:Concept {node_id: 'concept-pattern', file_type: 'concept',
  label: 'Pattern', description: 'A recurring pattern discovered across sessions'})
CREATE (:Concept {node_id: 'concept-compacted-fact', file_type: 'concept',
  label: 'CompactedFact', description: 'A compacted conversation fact stored for graph retrieval'})

// Bootstrap SeedForth organization (node_ids use org-role- prefix convention)
CREATE (sf:Knowledge:Organization {
  node_id: 'org-seedforth',
  label: 'SeedForth', entity_type: 'earner', status: 'active',
  file_type: 'organization', scope: 'seedforth', decay_protected: true
})
CREATE (eng:Knowledge:Department {
  node_id: 'org-seedforth-dept-engineering',
  label: 'Engineering', file_type: 'department',
  scope: 'seedforth', decay_protected: true
})
CREATE (sf)-[:HAS_DEPARTMENT {decay_protected: true}]->(eng)
CREATE (hub:Knowledge:Role {
  node_id: 'org-seedforth-role-hub-orchestrator',
  label: 'Hub Orchestrator', file_type: 'role',
  responsibilities: 'Route messages, fleet awareness, entity proposals',
  scope: 'seedforth', decay_protected: true
})
CREATE (eng)-[:HAS_ROLE {decay_protected: true}]->(hub)

// Subagents are MERGED (they may already exist)
MERGE (sa:Subagent {node_id: 'subagent-delta-hub'})
SET sa.name = 'Delta Hub', sa.role = 'Hub Orchestrator',
    sa.system_prompt = 'You are the SuperAgent orchestrator...',
    sa.tools = ['mycelium_ask', 'mycelium_query', 'rube', 'github'],
    sa.owner = 'delta', sa.status = 'active'
CREATE (hub)-[:ASSIGNED_TO {decay_protected: true}]->(sa)
```

**Note: Upstream mycelium changes required (before Phase 4).** The `decay_protected` property
does not exist in mycelium's decay protocols. Three `.cypher` protocol files in
`kagrawal29/mycelium` must be updated with `WHERE NOT coalesce(n.decay_protected, false)`
guards. Additionally, a new `protocol-decay-compaction` must be created to handle
`compaction_retention_days`-based expiration. These changes are submitted as a PR to
`kagrawal29/mycelium` during Phase 4 prerequisites and bootstrapped to dev before agents
begin writing decay_protected nodes.

**Embedding generation** (Phase 4): After each nightly promotion + crystallize, run
`mycelium embed` to regenerate embeddings for any nodes whose `leaf_hash` changed
(including newly promoted agent-compacted facts). This ensures `protocol-semantic-classify`
can create `:SEEMS_LIKE` edges and the Hebbian feedback loop (fire_count on QueryTrace)
applies to agent-written facts.

### 4.4 Context compacting: graph-based compression

**When context fills:**
1. Agent extracts facts from the conversation into `:Knowledge` nodes on local Neo4j:
   ```
   (:Knowledge {file_type: "decision", label: "...", rationale: "...", decided_by: "subagent-..."})
   (:Knowledge {file_type: "learning", label: "...", insight: "...", learned_by: "subagent-..."})
   (:Knowledge {file_type: "workitem", label: "...", status: "...", assigned_to: "..."})
   (:Knowledge {file_type: "pattern", label: "...", description: "...", confidence: 0.8})
   ```
2. Agent writes these to local Neo4j (via `mycelium-dev inject --target local`)
3. Agent replaces the long conversation history with a compact reference:
   "I have stored the following in mycelium (pending promotion): knowledge node ids X, Y, Z.
   Query them if you need the details."
4. Context window is freed — the details live in the graph, queryable on demand
5. Nightly: promotion job validates and bootstraps to dev graph

**Why graph compacting beats text summarization:**
- Structured — nodes have known types, queryable fields
- Shareable — any agent can query "what did SolveOS decide about pricing?"
- Non-lossy — the graph preserves the original fact, not a degraded summary
- Zero LLM cost for retrieval — one `mycelium ask` round-trip, no output tokens
- Hebbian — frequently queried facts get stronger (fire_count increments on `QueryTrace`)

**Protection from mycelium auto-protocols:**
Facts written by agents carry `decay_protected: true` to prevent heartbeat decay from
orphaning structural edges. The `compacted_at` timestamp and `compaction_retention_days`
property allow configurable retention. After the retention window, if a fact was never
queried (fire_count = 0), it gracefully expires.

---

## 5. Model Strategy

### 5.1 DeepSeek model allocation

| Agent Role | Model | Reasoning |
|---|---|---|
| **Hub Orchestrator** | `deepseek/deepseek-v4-pro` | High intelligence for routing, context, fleet decisions |
| **Builder Agent** (standard projects) | `deepseek/deepseek-v4-pro` | Code generation, tool calling, complex reasoning |
| **LinkedIn Agent** | `deepseek/deepseek-v4-pro` | Tool calling, compliance awareness, content quality |
| **Personal Agent** | `deepseek/deepseek-chat` | Conversational, cheaper output |
| **Onboarding Agent** | `deepseek/deepseek-chat` | Conversational intake, not code-heavy |
| **Explorer subagent** (codebase search) | `deepseek/deepseek-v4-flash` | Fast, cheap, read-only |
| **General subagent** (multi-step tasks) | `deepseek/deepseek-v4-pro` | Full tool access |
| **Compacting agent** | `deepseek/deepseek-v4-flash` | Extract facts — pattern matching, cheap |
| **Summarization agent** | `deepseek/deepseek-v4-flash` | Cheap, fast, text output only |

### 5.2 Cost estimation

| Model | Input/1M | Output/1M |
|---|---|---|
| DeepSeek V4 Pro | $0.435 | $0.87 |
| DeepSeek Chat (V3) | $0.27 | $1.10 |
| DeepSeek V4 Flash | $0.14 | $0.28 |

For a builder agent handling 50+ Discord messages/day with 2000 token context each:
~$0.50/day for V4 Pro. With 5 active agents: ~$75/month. ~10x cheaper than Claude Max.

**Safety valve:** Per-session token budget (e.g. max 50K tokens per message). Admin alert
if daily spend exceeds $5 threshold (configurable). Implemented in app.py, not in opencode.

### 5.3 Provider config

DeepSeek API key lives in:
1. `/opt/delta/delta.env` as `DEEPSEEK_API_KEY` (primary — used by supervisor config)
2. `/home/proj-{name}/.local/share/opencode/auth.json` (fallback — per-user copy)

**Provisioning** (during `create_user()`):
```python
# Copy auth.json template from /opt/delta/auth.json.template
shutil.copy("/opt/delta/auth.json.template",
            f"/home/{username}/.local/share/opencode/auth.json")
os.chown(f"/home/{username}/.local/share/opencode/auth.json",
         pwd.getpwnam(username).pw_uid, pwd.getpwnam(username).pw_gid)
os.chmod(f"/home/{username}/.local/share/opencode/auth.json", 0o600)
```

**Fallback to OpenRouter:** Keep `OPENROUTER_API_KEY` in delta.env as a backup provider.
Configure opencode to try OpenRouter if DeepSeek is rate-limited or down.

---

## 6. opencode config: .claude → opencode.jsonc

### 6.1 What changes

| Current (.claude) | New (opencode) |
|---|---|
| `.claude/settings.json` with hooks | `opencode.jsonc` at project root + user home |
| `claude mcp add-json rube ...` | Static MCP block in `opencode.jsonc` |
| `.claude.json` trust dialog pre-accept | Global `permission.*: "allow"` |
| `CLAUDE_CODE_OAUTH_TOKEN` env var | `DEEPSEEK_API_KEY` in delta.env + auth.json |
| `~/.claude` auth dir (symlinked across users) | Per-user `auth.json` copy + symlinked global config |
| `claude mcp add-json` dynamic registration | No dynamic registration. Static config. |

### 6.2 Rube MCP registration

**Old:** `claude mcp add-json rube '{"type":"http","url":"https://rube.app/mcp","headers":{"Authorization":"Bearer TOKEN"}}' --scope project`

**New:** Static block in project-level `opencode.jsonc`. The `{env:RUBE_BEARER_TOKEN}` syntax
resolves at opencode process startup from the supervisor environment block. No CLI
registration needed. The token lives in `/opt/delta/delta.env`, passed via supervisor config.

### 6.3 Global server config

`/root/.config/opencode/opencode.jsonc` — symlinked into each project user's home:
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "model": "deepseek/deepseek-v4-pro",
  "permission": {"*": "allow"}
}
```

### 6.4 .gitignore additions

Every project's `.gitignore` must include:
```
opencode.jsonc      # contains MCP config with env var references
.opencode/          # opencode local state directory
```

---

## 7. File-level Changes

### 7.1 delta/delta/lifecycle.py → delta/delta/agent_lifecycle.py

**Rename and rewrite.** Functions:

```python
# is_claude_running() -> is_agent_running()
def is_agent_running(serve_port: int) -> bool:
    """Health check via HTTP GET /global/health."""

# start_claude_code() -> start_agent_serve()
def start_agent_serve(project_name: str, serve_port: int, project_dir: str,
                      linux_user: str, env_vars: dict) -> bool:
    """Write supervisor config, supervisorctl update + start, wait for healthy."""

# stop_claude_code() -> stop_agent_serve()
def stop_agent_serve(project_name: str) -> bool:
    """supervisorctl stop, remove config file, supervisorctl update."""

# create_tmux_session() -> removed (supervisord manages processes)

# kill_tmux_session() -> removed

# nudge_lead() -> nudge_agent()
def nudge_agent(project_name: str, serve_port: int):
    """Write .nudge file + optional HTTP health check to wake agent."""

# Added: get_agent_health(), _wait_for_healthy(), _write_supervisor_config()

# Removed: is_session_alive(), is_claude_running() (tmux-specific)
# Removed: start_ttyd(), stop_ttyd() (replaced by opencode web)
# Removed: _allocate_port() (moves to provisioner)
# Removed: get_project_health() (split into is_agent_running() + HTTP health)
```

### 7.2 delta/delta/isolation.py

```python
# ensure_claude_auth_shared() -> ensure_opencode_config_shared()
def ensure_opencode_config_shared() -> None:
    """Make global opencode config accessible by project users."""
    # Ensure /root/.config/opencode/ exists and is readable
    config_dir = Path("/root/.config/opencode")
    if not config_dir.exists():
        return
    subprocess.run(["chmod", "711", "/root"], capture_output=True, text=True)
    subprocess.run(["chmod", "711", "/root/.config"], capture_output=True, text=True)
    subprocess.run(["chmod", "755", str(config_dir)], capture_output=True, text=True)
    for f in config_dir.glob("*"):
        subprocess.run(["chmod", "644", str(f)], capture_output=True, text=True)

# create_user() updated:
def create_user(project_name: str) -> str:
    username = linux_username(project_name)
    home = f"/home/{username}"

    # ... useradd, chown, chmod (unchanged) ...

    # Symlink global opencode config
    user_config_dir = Path(home) / ".config" / "opencode"
    user_config_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["sudo", "ln", "-sf",
                    "/root/.config/opencode/opencode.jsonc",
                    str(user_config_dir / "opencode.jsonc")],
                   capture_output=True, text=True)

    # Copy auth.json (per-user, not symlinked)
    user_data_dir = Path(home) / ".local" / "share" / "opencode"
    user_data_dir.mkdir(parents=True, exist_ok=True)
    auth_template = Path("/opt/delta/auth.json.template")
    if auth_template.exists():
        import shutil
        shutil.copy(str(auth_template), str(user_data_dir / "auth.json"))
        # opencode.db will be created here later — per-project, isolated

    # Set ownership
    subprocess.run(["sudo", "chown", "-R", f"{username}:", str(user_config_dir)],
                   capture_output=True, text=True)
    subprocess.run(["sudo", "chown", "-R", f"{username}:", str(user_data_dir)],
                   capture_output=True, text=True)
    subprocess.run(["sudo", "chmod", "600", str(user_data_dir / "auth.json")],
                   capture_output=True, text=True)

    return username
```

### 7.3 delta/delta/provisioner.py

**Changes in `_finalize_project()`:**

```python
def _finalize_project(name, project_dir, username, project_type, ...):
    # ... template rendering (unchanged) ...

    # 1. Write project-level opencode.jsonc (NOT .claude/settings.json)
    opencode_config = {
        "$schema": "https://opencode.ai/config.json",
        "model": "deepseek/deepseek-v4-pro",
        "mcp": {
            "rube": {
                "type": "remote",
                "url": "https://rube.app/mcp",
                "headers": {"Authorization": "Bearer {env:RUBE_BEARER_TOKEN}"}
            },
            "qdrant-memory": {
                "type": "local",
                "command": ["mcp-server-qdrant"],
                "environment": {
                    "QDRANT_URL": "http://143.110.226.214:6333",
                    "COLLECTION_NAME": "tetrahedron-memory",
                    "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2",
                    "QDRANT_ALLOW_ARBITRARY_FILTER": "true"
                }
            }
        },
        "agent": {
            "build": {
                "mode": "primary",
                "model": "deepseek/deepseek-v4-pro",
                "permission": {"*": "allow"},
                "prompt": "{file:./CLAUDE.md}"
            }
        }
    }
    config_path = Path(project_dir) / "opencode.jsonc"
    config_path.write_text(json.dumps(opencode_config, indent=2))

    # 2. Add opencode.jsonc to .gitignore
    gitignore_path = Path(project_dir) / ".gitignore"
    gitignore = gitignore_path.read_text() if gitignore_path.exists() else ""
    if "opencode.jsonc" not in gitignore:
        gitignore += "\nopencode.jsonc\n.opencode/\n"
        gitignore_path.write_text(gitignore)

    # 3. Remove: .claude/settings.json write
    # 4. Remove: .claude.json trust dialog pre-accept
    # 5. Remove: _register_rube_mcp() (now in opencode.jsonc)
    # 6. Remove: hook_script deployment (progress tracking via todowrite polling)

    # 7. Allocate ports (serve + web)
    serve_port = _allocate_port(registry, range_start=7700, range_end=7899)
    web_port = _allocate_port(registry, range_start=7900, range_end=8099)

    # 8. Start agent via supervisor
    start_agent_serve(name, serve_port, project_dir, username, extra_env={
        "RUBE_BEARER_TOKEN": os.environ.get("RUBE_BEARER_TOKEN", ""),
        "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", ""),
        "VERCEL_TOKEN": os.environ.get("VERCEL_TOKEN", ""),
        "UNIPILE_DSN": os.environ.get("UNIPILE_DSN", ""),
        "UNIPILE_API_KEY": os.environ.get("UNIPILE_API_KEY", ""),
        "COMPOSIO_API_KEY": os.environ.get("COMPOSIO_API_KEY", ""),
        "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY", ""),
    })

    # 9. Register in delta-registry.json with new fields
    registry.register(ProjectInfo(
        name=name,
        project_dir=str(project_dir),
        linux_user=username,
        serve_port=serve_port,
        web_port=web_port,
        runtime="opencode",        # new field
        supervisor_program=f"proj-{name}",  # new field
        # ... existing fields ...
    ))

    # 10. Fix file ownership
    # ... (unchanged) ...
```

**Remove:** `_register_rube_mcp()` function entirely. Rube MCP is now static config.

**Move:** `_allocate_port()` from `lifecycle.py` to `provisioner.py` (provisioner is now the
sole caller; ports are provision-time decisions).

### 7.4 delta/delta/registry.py

**New fields in `ProjectInfo`:**
```python
@dataclass
class ProjectInfo:
    name: str
    project_dir: str
    linux_user: str
    github_repo: str = ""
    discord_channel_id: str = ""
    owner_discord_id: str = ""
    # REPLACED: ttyd_port -> serve_port (open code serve API, localhost)
    serve_port: int = 0
    # NEW: web_port (open code web terminal, 0.0.0.0, optional)
    web_port: int = 0
    # NEW: runtime engine ("claude" for legacy, "opencode" for new)
    runtime: str = "claude"
    # NEW: supervisor program name
    supervisor_program: str = ""
    # NEW: opencode session ID (created on provision, persisted across restarts)
    session_id: str = ""
    # ... existing fields: status, created_at, tmux_session, tmux_lead_pane (deprecated) ...
```

### 7.5 delta/delta/project_bridge.py

**Kept as-is with minor changes:**

**Constructor** — add `serve_port` and `session_id` parameters (optional, default None for
legacy Claude Code projects that don't have them):
```python
class ProjectBridge:
    def __init__(self, project_name: str, project_dir: str,
                 serve_port: int = 0, session_id: str = "",
                 runtime: str = "claude"):
        self.serve_port = serve_port
        self.session_id = session_id
        self.runtime = runtime
        # ... existing init ...
```

- `write_inbox()`, `watch_outbox()`, `watch_followups()`: **preserved as-is**.
- `_nudge()` / `send_to_lead()`: **redesigned**. Instead of tmux send-keys, touches a
  `.nudge` flag file and sends an HTTP health check to wake the serve process.
  Idempotent — touching `.nudge` repeatedly has no side effect. The agent's CLAUDE.md
  instructs it to check the `.nudge` file every 10 seconds, delete it when found, and
  process all pending inbox messages. This eliminates the need for `_is_pane_at_prompt()`.

```python
def _nudge(self) -> None:
    nudge_file = Path(self.project_dir) / "delta-config" / ".nudge"
    nudge_file.touch()
    if self.serve_port:
        try:
            requests.get(f"http://127.0.0.1:{self.serve_port}/global/health", timeout=5)
        except requests.RequestException:
            pass
```

- `_is_pane_at_prompt()`: **removed**. The `.nudge` file approach is idempotent — no
  anti-stacking needed. The silence detection loop in app.py drops its `queued_nudge`
  state machine; it simply checks `check_silence()` and calls `_nudge()` if silent.
- `watch_inbox()`: **removed**. With `.nudge` files being idempotent and the agent
  processing all pending inbox messages on each wake, re-nudging stale inbox files is
  unnecessary. The silence detection loop handles the case where the agent doesn't
  respond to a nudge.
- `check_auth_error()`: **redesigned**. Instead of scanning tmux scrollback, reads from
  a dedicated error file channel. The agent writes to `delta-config/errors/{timestamp}.json`
  when it encounters API auth errors. The bridge reads the most recent error file.

```python
def check_auth_error(self) -> str | None:
    errors_dir = Path(self.project_dir) / "delta-config" / "errors"
    if not errors_dir.exists():
        return None
    error_files = sorted(errors_dir.glob("*.json"), reverse=True)
    if not error_files:
        return None
    try:
        error_data = json.loads(error_files[0].read_text())
        if error_data.get("type") == "auth_error":
            return error_data.get("message", "Auth error detected")
    except (json.JSONDecodeError, OSError):
        pass
    return None
```

- `is_project_active()`: changed from `is_claude_running()` to `is_agent_running(serve_port)`
  for opencode projects. Legacy dispatch via `runtime` field.
- **`capture_tmux_scrollback()`**: **removed** — no tmux scrollback to scan.

**Progress tracking** (replaces `watch_progress`):
```python
def watch_progress(self) -> None:
    """Poll opencode session todo list for work-in-progress status."""
    while True:
        time.sleep(5)
        if not self.session_id or not self.serve_port:
            continue
        try:
            resp = requests.get(
                f"http://127.0.0.1:{self.serve_port}/session/{self.session_id}/todo",
                timeout=5
            )
            if resp.status_code == 200:
                todos = resp.json()
                in_progress = [t for t in todos if t.get("status") == "in_progress"]
                if in_progress and in_progress != self._last_progress_state:
                    self._last_progress_state = in_progress
                    task_labels = [t.get("content", "working") for t in in_progress[:3]]
                    self._on_progress(task_labels)
        except requests.RequestException:
            pass
```

### 7.6 delta/delta/app.py

**Status display** (`_format_all_status`, `_format_project_status`):
- `health["claude_running"]` → `health["agent_running"]`
- Runtime dispatch in health check: if `project.runtime == "opencode"`, call
  `is_agent_running(project.serve_port)`. Otherwise, use existing `is_claude_running()`.
- `_format_all_status()` shows runtime type in status line: "opencode | idle" vs "claude | idle"

**Hub snapshot loop** (`_hub_snapshot_loop`): Add runtime dispatch for health reporting.
The hub (running on Claude Code through Phase 6) must report health for opencode agents.
```python
# In _hub_snapshot_loop, where health is collected per project:
if info.runtime == "opencode":
    health = {"agent_running": is_agent_running(info.serve_port),
              "session_alive": True}  # supervisord ensures liveness
else:
    health = get_project_health(info.tmux_lead_pane)
```

**Silence detection** (`_silence_nudge_loop`): Simplified. The `.nudge` file is idempotent,
so the `queued_nudge` anti-stacking state machine is removed. The loop simply:
1. Call `bridge.check_silence()` — unchanged (uses inbox/outbox timestamps)
2. If silent, call `bridge._nudge()` — idempotent `.nudge` file touch + health check
3. If super-silent (>5 minutes, 20 cycles), escalate to admin alert
No `_is_pane_at_prompt()` call — the agent handles deduplication by deleting `.nudge` after
processing.

**Restore on startup** (`_restore_active_projects`):
- For `runtime == "opencode"` projects: call `supervisorctl start proj-{name}` (config was
  preserved during hibernate/stop with `keep_config=True`). Wait for health check via
  `_wait_for_healthy(serve_port)`. Validate session via HTTP GET.
- For `runtime == "claude"` projects (legacy): existing tmux-based restore via
  `create_tmux_session()` + `start_claude_code()`.
- Session recreation: if HTTP health check passes but session GET returns 404, create new
  session via `POST /session`, update `project.session_id` in registry.

**Onboarding complete handler** (`_handle_onboarding_complete`): AgentRunner dispatch:
```python
runner = get_runner(info)
runner.stop(info, keep_config=True)  # hibernate-style stop
runner.start(info)                    # restart with new template
```

**Restart command** (`_handle_command` "restart"):
```python
runner = get_runner(info)
runner.stop(info, keep_config=True)
runner.start(info)
```

**Peek command** (`peek`, `peek_hub`): For opencode agents, reads recent agent stdout log
from supervisor (`tail -50 /home/proj-{name}/{name}/delta-config/logs/opencode-stdout.log`).
For legacy Claude Code agents, uses existing `capture_tmux_scrollback()`. This keeps the
debug feature operational during migration without tmux dependency.

**Resource manager** (hibernate/restore):
- Hibernate: `stop_agent_serve(project_name, keep_config=True)` — supervisor stops,
  config preserved for restore.
- Restore: `start_agent_serve(project_name, serve_port, ...)` — supervisor starts
  existing program.
- For Claude Code projects: existing `kill_tmux_session()` / `create_tmux_session()` flow.

### 7.7 delta/deploy/setup-server.sh

```bash
#!/bin/bash
set -euo pipefail

echo "=== Delta Server Setup (opencode edition) ==="

# 1. System packages
echo "[1/8] Installing system packages..."
apt update && apt install -y python3-pip python3-venv git curl ufw supervisor

# 2. Node.js 20+ (opencode requirement)
echo "[2/8] Installing Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# 3. GitHub CLI (needed for mycelium install in step 4)
echo "[3/8] Installing GitHub CLI..."
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | \
    dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | \
    tee /etc/apt/sources.list.d/github-cli.list > /dev/null
apt-get update && apt-get install -y gh

# 4. opencode CLI
echo "[4/8] Installing opencode..."
npm install -g opencode-ai

# 5. mycelium CLI (requires gh auth from step 3)
echo "[5/8] Installing mycelium..."
gh release download -R kagrawal29/mycelium -p install.sh
bash install.sh  # installs mycelium to /usr/local/bin/mycelium

# 6. Firewall
echo "[6/8] Configuring firewall..."
ufw allow OpenSSH
ufw allow 7900:8099/tcp   # opencode web terminals
ufw --force enable

# 7. Clone repo + install deps
echo "[7/8] Setting up delta..."
if [ -d /opt/delta ]; then
    cd /opt/delta && git pull
else
    git clone https://github.com/kagrawal29/delta.git /opt/delta
fi
cd /opt/delta && pip3 install -r requirements.txt

# 8. Systemd service + supervisor
cp deploy/delta.service /etc/systemd/system/delta.service
systemctl daemon-reload
systemctl enable delta
systemctl enable supervisor  # auto-start agents on boot

# 9. opencode global config
echo "Writing global opencode config..."
mkdir -p /root/.config/opencode
cat > /root/.config/opencode/opencode.jsonc << 'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "model": "deepseek/deepseek-v4-pro",
  "permission": {"*": "allow"}
}
EOF

# 10. Logrotate for supervisor agent logs
cat > /etc/logrotate.d/delta-agents << 'EOF'
/home/proj-*/**/delta-config/logs/opencode-*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF

echo ""
echo "=== Setup complete ==="
echo ""
echo "Remaining manual steps:"
echo "  1. Create /opt/delta/delta.env with all secrets"
echo "  2. Create /opt/delta/auth.json.template with DeepSeek API key (chmod 600)"
echo "  3. gh auth login --scopes repo (for mycelium release downloads)"
echo "  4. Verify: opencode run --auto --model deepseek/deepseek-v4-pro 'echo hello'"
echo "  5. Verify: mycelium --target dev doctor"
echo "  6. Install local Neo4j for agent write staging (apt install neo4j)"
echo "  7. Start: systemctl start delta"
```

### 7.8 delta/deploy/delta.env.example

```bash
# Discord
DISCORD_TOKEN=your-discord-bot-token
ADMIN_DISCORD_ID=838843068857319445
DISCORD_SERVER_ID=

# Mode
LOCAL_MODE=false
DELTA_SERVER_HOST=143.110.226.214

# DeepSeek API (replaces CLAUDE_CODE_OAUTH_TOKEN)
DEEPSEEK_API_KEY=sk-...

# OpenRouter (fallback if DeepSeek is down)
OPENROUTER_API_KEY=sk-or-v1-...

# Mycelium
MYCELIUM_TARGET=dev

# GitHub
GITHUB_TOKEN=

# Google services via Rube MCP
RUBE_BEARER_TOKEN=

# Vercel deployment
VERCEL_TOKEN=

# Composio (account connections)
COMPOSIO_API_KEY=

# Unipile LinkedIn API
UNIPILE_DSN=https://api34.unipile.com:16492
UNIPILE_API_KEY=

# LinkedIn onboarding
ONBOARDING_CHANNEL_ID=
LINKEDIN_ONBOARDING_CHANNEL_ID=
```

### 7.9 delta/deploy/delta.service

Unchanged from current. The delta app itself manages opencode processes via supervisord.

### 7.10 Project templates

All `project-template/*.md` files:
- Keep filename as `CLAUDE.md` (opencode reads both, avoid code churn)
- Add mandatory instruction: "Query `mycelium ask` or `mycelium shell` before making decisions.
  The graph is the team's shared memory."
- Add mycelium custom tool usage instructions
- Add context compacting protocol: "When context fills, extract facts into local Neo4j staging
  using `mycelium-dev inject`. Nightly promotion will sync them to the shared dev graph."
- Update tool references: "Rube MCP is configured in `opencode.jsonc`. Use it directly."
- Update identity section: "You are an opencode agent running on DeepSeek."
- Hub template (`HUB_CLAUDE.md`): expand to SuperAgent consciousness (Phase 7)
- Add `.nudge` file watcher instruction: "Check delta-config/.nudge every 10 seconds. If
  present, read the inbox, delete .nudge, and process all pending messages."
- Remove: Claude Code-specific instructions, `claude mcp add-json` references,
  `.claude/settings.json` references

### 7.11 REMOVED: project-template/hooks/progress_hook.py

Progress tracking now via opencode `todowrite` tool + Delta-side polling of
`/session/{id}/todo`. The hook mechanism had no opencode equivalent.

---

## 8. Implementation Phases

### Phase 0: Prerequisites (no code changes)
- [ ] Install opencode on delta-server (`npm install -g opencode-ai`) — requires Node 20+
- [ ] Install mycelium on delta-server (`gh release download -R kagrawal29/mycelium -p install.sh && bash install.sh`)
- [ ] Install supervisor (`apt install -y supervisor`)
- [ ] Write `/root/.config/opencode/opencode.jsonc` (global auto-approve + model default)
- [ ] Create `/opt/delta/auth.json.template` with DeepSeek API key (chmod 600, gitignored)
- [ ] Add `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`, `MYCELIUM_TARGET` to `/opt/delta/delta.env`
- [ ] Verify: `opencode run --auto --model deepseek/deepseek-v4-pro "echo hello"` works as root
- [ ] Verify: `sudo -u proj-{name} opencode run --auto "echo hello"` works as project user
- [ ] Verify: `mycelium --target dev doctor` returns green

### Phase 1: Core agent lifecycle (code changes)
- [ ] Add `runtime`, `serve_port`, `web_port`, `supervisor_program`, `session_id` to `ProjectInfo`
- [ ] Rewrite `delta/lifecycle.py` → `delta/agent_lifecycle.py`
  - `start_agent_serve()`, `stop_agent_serve()`, `is_agent_running()`, `nudge_agent()`
  - `_write_supervisor_config()`, `_wait_for_healthy()`
  - Remove all tmux functions
- [ ] Update `delta/isolation.py` — opencode config sharing + per-user auth copy
- [ ] Update `delta/provisioner.py`:
  - Write `opencode.jsonc` per project, add to .gitignore
  - Allocate serve_port + web_port from appropriate ranges
  - Call `start_agent_serve()` instead of `start_claude_code()`
  - Remove `_register_rube_mcp()`
- [ ] Update `delta/app.py`:
  - AgentRunner interface with two backends: `ClaudeCodeRunner`, `OpencodeServeRunner`
  - Conditional dispatch based on `ProjectInfo.runtime`
  - Replace all `is_claude_running()` with interface calls
- [ ] Create test project with `runtime: "opencode"`, verify agent starts via supervisor
- [ ] Verify: agent responds to test Discord messages via file bridge + HTTP nudge

### Phase 2: Message bridge adaptation
- [ ] Update `delta/project_bridge.py`:
  - `_nudge()` → file flag + HTTP health check (no tmux send-keys)
  - `is_project_active()` → `is_agent_running(serve_port)`
  - `check_auth_error()` → scan outbox content for DeepSeek error patterns
  - Remove `capture_tmux_scrollback()`, `_is_pane_at_prompt()`
- [ ] Update `watch_progress()` → poll `GET /session/{id}/todo`
- [ ] Test: multi-message conversation, message queueing (inbox files stack correctly)
- [ ] Test: silence detection (nudge fires after 25s, agent processes)
- [ ] Test: schedule.json recurring tasks still work
- [ ] Test: followup delivery (time-delayed messages)

### Phase 3: MCP + tools wiring
- [ ] Write per-project `opencode.jsonc` with Rube MCP config
- [ ] Write per-project `opencode.jsonc` with Qdrant MCP config
- [ ] Test: Rube MCP (Google Drive, Gmail) works from opencode agent
- [ ] Test: Unipile LinkedIn tools work
- [ ] Test: Browser CDP tool works (`python3 /opt/delta/tools/browser.py` from proj-* user)
- [ ] Test: GitHub push/issues work
- [ ] Test: Vercel deployment works
- [ ] Test: `mycelium ask` and `mycelium shell` custom tools work

### Phase 4: Mycelium integration
- [ ] Set up local Neo4j staging instance on delta-server (`apt install neo4j`, bolt://localhost:7687, write-enabled)
- [ ] Create agent write tool: `/opt/delta/tools/store-fact.py` (MERGE-only, schema-validated, scoped by agent identity)
- [ ] Create nightly export tool: `/opt/delta/tools/export-staging.py` (reads pending nodes, generates .cypher files with @node_id/@label headers)
- [ ] Submit upstream PR to `kagrawal29/mycelium`: add `decay_protected` guards to 3 decay protocols + create `protocol-decay-compaction`
- [ ] Bootstrap: deploy org-structure.cypher to mycelium dev graph via standard PR flow
- [ ] Bootstrap: deploy concept nodes (8 concepts: org, dept, role, project, decision, learning, pattern, compacted-fact) via PR flow
- [ ] Add mycelium custom tools to global opencode config (mycelium_ask, mycelium_query, mycelium_store)
- [ ] Update all agent templates with mycelium usage + context compacting instructions
- [ ] Test: agent queries mycelium before making decisions (read path via mycelium ask/shell)
- [ ] Test: agent writes facts to local Neo4j staging via mycelium_store tool
- [ ] Test: nightly export script generates valid .cypher files from local Neo4j
- [ ] Test: nightly promotion job: export → validate-merge → commit → PR → merge → bootstrap → crystallize
- [ ] Test: `mycelium embed` regenerates embeddings for promoted facts
- [ ] Test: promoted facts appear in `mycelium ask` semantic search results
- [ ] Test: cross-project queries work (agent A queries agent B's promoted facts)

### Phase 5: Full fleet migration
- [ ] Migrate projects one-by-one: set `runtime: "opencode"`, reprovision
- [ ] Keep Claude Code sessions frozen as backup (don't tear down until validated)
- [ ] Run both runtimes in parallel for 48h minimum
- [ ] Validate: all tools work, message delivery works, no regression
- [ ] Tear down Claude Code OAuth + tmux sessions
- [ ] Deploy updated templates (CLAUDE.md variants with mycelium instructions)
- [ ] Update observatory to show opencode serve health instead of tmux session health
- [ ] Remove legacy Claude Code runner code (Phase 6 scope)

### Phase 6: Context compacting
- [ ] Implement graph-based compacting agent (extract facts → local Neo4j staging)
- [ ] Test: compacting runs when context approaches limit
- [ ] Test: compacted facts survive nightly promotion to dev graph
- [ ] Test: compacted facts are queryable by other agents (after promotion)
- [ ] Benchmark: compare token usage (text summary vs graph compacting)
- [ ] Tune: adjust `compaction_retention_days` based on actual query patterns

### Phase 7: SuperAgent consciousness (Hub upgrade)
- [ ] Rewrite Hub CLAUDE.md to embody Sutradhaar constitution
- [ ] Hub reads fleet state from mycelium (not just registry-snapshot.json)
- [ ] Hub tracks leverage in/out per entity via mycelium graph properties
- [ ] Hub proposes entity creation, merging, reseeding
- [ ] Hub reports to admin channel with energy-model summaries
- [ ] Ratification channel (Gate mechanism): Hub proposes → admin approves via Discord
- [ ] Mission entities (Sutatva, Ashoonya, Prayogshala) bootstrapped as graph nodes

### Phase 8: Observability & Operations
- [ ] Per-project opencode logs captured by supervisor → rotated via logrotate (Section 7.7)
- [ ] Prometheus metrics endpoint on delta.app: agent health, message latency, token usage
- [ ] DeepSeek spend tracking: **use DeepSeek's billing API** (`GET https://api.deepseek.com/v1/usage`)
  queried nightly by a delta-side cron job. app.py does NOT enforce token budgets in real-time
  (opencode serves as a separate process and does not expose per-request token usage via HTTP).
  Instead: nightly usage check against $5/day threshold, admin alert on overage. If overage is
  persistent, reduce the `max_tokens` parameter in opencode.jsonc model config or switch to
  cheaper model. Per-message token limits are not enforced — DeepSeek's API returns what it
  returns. This is an accepted constraint of the headless-serve model.
- [ ] opencode binary upgrade procedure: `npm update -g opencode-ai` + `supervisorctl restart all`
  (note: full fleet restart; for zero-downtime, restart projects one-by-one)
- [ ] Backup (daily cron, 3am, before nightly promotion):
  - `/home/proj-*/` — project dirs, SQLite session DBs, conversation logs
  - `/etc/supervisor/conf.d/proj-*.conf` — **added in v3** (without these, DR cannot auto-start agents)
  - `/opt/delta/delta-registry.json` — project registry
  - `/opt/delta/delta.env` — secrets
  - `/var/lib/neo4j/data/` — local Neo4j staging data (agent-written facts pending promotion)
  - **DR restore order**: restore Neo4j data → restore home dirs → restore supervisor configs →
    restore registry → restore delta.env → `supervisorctl reload` → `systemctl start delta`
- [ ] RAM monitoring: MemoryMax=512M per supervisor program, alert at 80% server RAM usage
- [ ] Version pinning: `npm install -g opencode-ai@<version>` in setup script with explicit
  version. Upgrade only after validation on staging.

---

## 9. Runtime Coexistence (AgentRunner Interface)

During the migration (Phases 1-5), both Claude Code and opencode runtimes coexist. A clean
interface prevents codebase fragmentation.

```python
class AgentRunner(Protocol):
    """Interface for agent process management. Implemented by ClaudeCodeRunner and
    OpencodeServeRunner."""

    def start(self, project: ProjectInfo) -> bool: ...
    def stop(self, project: ProjectInfo, keep_config: bool = True) -> bool: ...
    def is_running(self, project: ProjectInfo) -> bool: ...
    def health(self, project: ProjectInfo) -> dict: ...
    def nudge(self, project: ProjectInfo) -> None: ...

class OpencodeServeRunner:
    """Wraps new agent_lifecycle.py functions. Primary runtime after Phase 5."""
    def start(self, project): return start_agent_serve(project.name, project.serve_port, project.project_dir, project.linux_user, {})
    def stop(self, project, keep_config=True): return stop_agent_serve(project.name, keep_config=keep_config)
    def is_running(self, project): return is_agent_running(project.serve_port)
    def health(self, project): return get_agent_health(project.serve_port)
    def nudge(self, project): return nudge_agent(project.name, project.serve_port)

class ClaudeCodeRunner:
    """Wraps existing lifecycle.py functions. Legacy, removed in Phase 5."""
    def start(self, project): return start_claude_code(project.project_dir, project.tmux_lead_pane, project.linux_user)
    def stop(self, project, keep_config=True): return stop_claude_code(project.tmux_lead_pane)
    def is_running(self, project): return is_claude_running(project.tmux_lead_pane)
    def health(self, project): return get_project_health(project.tmux_lead_pane)
    def nudge(self, project): return nudge_lead(project.tmux_lead_pane)

# Dispatch
def get_runner(project: ProjectInfo) -> AgentRunner:
    return OP ENCODE_RUNNER if project.runtime == "opencode" else CLAUDE_RUNNER
```

---

## 10. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| opencode serve crashes silently | Supervisor autorestart (5s). app.py health-checks via HTTP before nudge. Alert if restart loop detected. |
| DeepSeek API rate limits or downtime | Fallback to OpenRouter with same model. Supervisor env includes both keys. opencode tries DeepSeek first, falls back. |
| Mycelium graph is down | Agents continue with local Qdrant memory. Read path fails gracefully. Retry when graph is back. |
| Local Neo4j staging data loss before promotion | Nightly promotion runs at 2am. Data written during the day persists in local Neo4j. Back up local Neo4j before promotion. |
| Session state corruption | SQLite is robust. opencode serve auto-recovers. Fallback: create new session, replay context from SEED.md + mycelium. |
| MCP tool incompatibility | Test each MCP tool in Phase 3 before cutting over. Rube MCP and Qdrant use standard MCP protocol — no opencode-specific issues expected. |
| Process isolation breach | Each serve runs as `proj-{name}` OS user. Per-user auth.json (chmod 600). Supervisor MemoryMax=512M per program. |
| Token cost runaway | Per-message token budget (50K tokens max). Daily spend alert at $5 threshold. Admin can emergency-stop any agent via supervisorctl. |
| Existing project data loss | Phase 5 runs both systems in parallel. All git repos, conversation logs, SEED.md preserved. Frozen Claude Code sessions as rollback. |
| opencode.jsonc committed to git | .gitignore includes opencode.jsonc and .opencode/. Provisioner adds this during `_finalize_project()`. Pre-commit hook validates. |

---

## 11. Success Metrics

- All Delta project agents running on opencode (zero `claude` processes in the system)
- Message delivery works identically to current system (file bridge preserved)
- Every agent queries mycelium at least once per session (read path proven)
- Decisions and learnings flow from local staging → dev graph via nightly promotion (write path proven)
- Context compacting reduces per-session token usage by 40%+ (graph storage replaces text summaries)
- Cost reduction: DeepSeek V4 Pro is ~10x cheaper than Claude Max subscription
- Fleet-level awareness: Hub can answer "what is the state of the fleet?" from mycelium
- Organizational structure modeled in graph: new entities seeded by writing graph nodes
- Zero tmux/send-keys in the system — agent lifecycle managed by supervisord
- AgentRunner interface enables clean runtime switching during migration

---

## 12. Open Decisions

1. **Agent file naming:** Keep `CLAUDE.md` or rename to `AGENTS.md`?
   - opencode reads both. Keeping CLAUDE.md avoids code churn in provisioner template rendering.
   - **Decision: Keep CLAUDE.md.** Revisit in Phase 7 when Hub gets a full rewrite.

2. **Local Neo4j staging instance:** Separate Neo4j instance on delta-server, or a separate
   database on the existing Neo4j (pulse-server)?
   - Trade-off: dedicated local instance = simpler writes, no bolt-proxy conflict. Shared
     pulse Neo4j = one less service to manage, but writes through bolt-proxy are blocked.
   - **Recommendation: Dedicated local Neo4j on delta-server** (bolt://localhost:7687).
     Simple. Isolated. No risk to shared graphs.

3. **open code web terminal:** Enable per-project or admin-only?
   - Each project can have its own opencode web terminal for debug. Adds process overhead.
   - **Recommendation: Admin-only by default** (hub + on-demand for specific projects).
     Supervisor config `autostart=false` for web program; provision on request.

4. **Hibernation model:** With supervisor, hibernation means `supervisorctl stop` + keep config.
   On wake: `supervisorctl start`. Same as current model but via supervisor instead of tmux.
   - **Decision: Identical to current.** No design change needed.

5. **Nightly promotion schedule:** Frequency and timing?
   - **Recommendation: 2am UTC daily.** Collects all mutations from local Neo4j, runs
     validate-merge, commits to mycelium branch, opens PR, merges, bootstraps to dev.

6. **Browser CDP tool access from proj-* users:** The browser tool at `/opt/delta/tools/browser.py`
   makes HTTP requests to localhost CDP ports (9223, 9224). Proj-* users can access localhost
   ports by default on Linux. No additional config needed. Verify in Phase 3.

7. **Ratification system (Gates):** Hub proposes irreversible actions → admin ratifies via
   Discord reaction or command.
   - **Recommendation: Phase 7 feature.** Not blocking Phases 0-5. Discord-native: Hub sends
     proposal to admin channel, admin reacts with checkmark, Hub proceeds.

8. **`mycelium` vs `maverick` naming:** The binary is `mycelium`, installed from
   `kagrawal29/mycelium` releases. The team distribution repo is `Qubit-Capital/maverick`.
   The binary name is `mycelium`. All spec references use `mycelium` CLI.
   - **Decision: Resolved. Binary name = `mycelium`.** Install from upstream releases.
