# AGENTS.md — Read This First

Every Claude (or human) dropped into this repo should read this file before touching anything else. It tells you what the repo is, what the graph is, and how to use it without breaking it.

## What this is

**Maverick** is the team distribution of **Mycelium** — a living knowledge graph that the team uses to think together. The graph stores prior decisions, architectural invariants, operational runbooks, WorkItems, TestCases, and semantic neighborhoods. Before you propose anything new, ask the graph.

The repo at `main` on `github.com/Qubit-Capital/maverick` is the teammate-facing artifact: clone it, install the CLI, and you can query the team's graph from any shell, any IDE, any subprocess. Upstream work lands on `github.com/kagrawal29/mycelium` and syncs into maverick via PR.

## Quick start (humans and agents, same command)

### Prerequisite (one-time)
Maverick is a **private** repo, so release assets require GitHub auth. Install [GitHub CLI](https://cli.github.com/) and log in once:
```bash
gh auth login           # pick GitHub.com → HTTPS → authenticate via browser
```
Ask the owner (Kshitiz) to add you to `Qubit-Capital/maverick` first if you can't see the repo.

### macOS / Linux
```bash
gh release download -R Qubit-Capital/maverick -p install.sh
bash install.sh
mycelium --target dev shell "MATCH (b:Being) RETURN count(b)"
```

### Windows (PowerShell)
```powershell
gh release download -R Qubit-Capital/maverick -p install.ps1
powershell -ExecutionPolicy Bypass -File .\install.ps1
mycelium --target dev shell "MATCH (b:Being) RETURN count(b)"
```

That's it. No Python. No JDK. No WSL. No Ollama. No Neo4j install. The installer auto-detects your OS, grabs the right binary from the latest release (through `gh`, since the repo is private), verifies its SHA256, installs it to `~/.mycelium/bin/mycelium`, and symlinks `/usr/local/bin/mycelium` so every shell and every Claude Code subprocess sees it on PATH. The binary itself embeds read-only team credentials at release time and connects to the dev graph on first call.

## How mycelium works

**One binary, two surfaces.**

- **Read verbs** (`status`, `shell`, `ask`, `health`, `doctor`, `version`, `config`, `help`) run natively in the Go binary — fast, no dependencies, safe from any machine.
- **Write verbs** (`bootstrap`, `start`, `stop`, `swarm`, `dream`, `ingest-repo`, `fork`, `sync`, `drift`, `dump`, `restore`, `migrate`, `target`, `inject`) dispatch to `mycelium-dev` — the contributor-side bash + Python toolchain. Readers never need it. Contributors install it once and the same `mycelium X` command line gains those verbs transparently.

**If you're an agent you are almost always reading.** Start with `mycelium --target dev shell` and `mycelium ask` before editing anything. Writes belong in PRs with team review.

## Use this from Claude Code (every session, every project)

After `install.sh` finishes, `mycelium` is on `PATH` system-wide (via `/usr/local/bin/mycelium` symlink). Every Claude Code session — in any repo on your laptop, not just maverick — can call it directly:

```bash
mycelium --target dev ask "what do we know about X"
mycelium --target prod shell "MATCH (d:Decision) WHERE d.topic CONTAINS 'auth' RETURN d.label, d.date"
```

**What it is:** the collective intelligence of everything the team has done on maverick — decisions, WorkItems, architectural invariants, test cases, session reflections, semantic neighborhoods — as a live queryable graph. Your own contributions land there too once they're committed and ingested, so you can find your past work alongside the rest.

**Why you want it:** instead of an LLM grep-loop through files to answer "has the team already decided X" or "what did we learn about Y", you run one Cypher or one semantic `ask` and get the answer in milliseconds. Zero tokens. One round-trip.

**When to reach for it (as an agent):**
- Before proposing architecture: `mycelium --target prod ask "has the team decided on <topic>"`
- Before writing a new WorkItem: check if one already exists — `mycelium --target dev shell "MATCH (w:WorkItem) WHERE w.title CONTAINS '<keyword>' RETURN w.id, w.status"`
- When you see an invariant or protocol mentioned: look it up — `mycelium --target prod shell "MATCH (i:Invariant {name:'<name>'}) RETURN i"`
- When debugging something that feels familiar: `mycelium --target prod ask "have we seen <symptom> before"`
- To dump what's queryable: `mycelium --target dev shell "CALL db.labels()"`

**Add to your global Claude Code instructions** (`~/.claude/CLAUDE.md`) so every session knows to reach for it:
```
The `mycelium` CLI is on PATH and exposes the team's shared knowledge graph
(Qubit-Capital/maverick). Before proposing anything non-trivial, query it:
  mycelium --target prod ask "<natural language>"
  mycelium --target dev shell "<read-only Cypher>"
Writes go through `mycelium-dev` in a PR, not through `mycelium`.
```

## For Claude agents specifically

- `mycelium` is available on `PATH` for every subprocess, every session. Don't try to alias, activate a venv, or source anything — just call it.
- Default target is configurable via `MYCELIUM_TARGET` env var. If unset, pass `--target dev` explicitly.
- Query tracing: not graph-native yet (v1.0.0). Denied writes are logged to pulse-server's journal via `bolt-proxy`. Successful reads aren't traced today — enabling Neo4j's `db.logs.query` or a graph-native `:QueryTrace` node is a v1.1 decision.
- Before recommending anything new, check the graph first:
  ```bash
  mycelium --target prod ask "has the team decided on X"
  mycelium --target prod shell "MATCH (d:Decision) WHERE d.topic CONTAINS 'Y' RETURN d.label, d.date"
  ```
- Before writing code that touches the graph schema, read `docs/architecture/binary-cli.md` + `docs/contributor-setup.md`.

## Safety envelope

- The `shell` command refuses write verbs (`CREATE`, `MERGE`, `DELETE`, `SET`, `REMOVE`, `DROP`, `DETACH`) client-side *and* server-side. Attempts will fail loud.
- The `dev` and `prod` targets go through a read-only Bolt proxy on pulse-server. You can't accidentally mutate shared graphs.
- Contributors who need to write use `mycelium-dev` against `--target local` first, commit, open a PR.

## Branching + merge policy

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Two-tier: feature → `dev` → `main` via PR. No direct pushes to `dev` or `main`. Upstream of this repo is `kagrawal29/mycelium`; this repo is the team distribution.

## Where the docs live

| Topic | Path |
|---|---|
| Binary architecture (why Go, how dispatch works, rotation runbook, schema) | `docs/architecture/binary-cli.md` |
| Contributor write-path setup | `docs/contributor-setup.md` |
| Install (reader one-liner) | `docs/install.md` |
| Credential rotation runbook | `docs/operations/credential-rotation.md` |
| Staging Neo4j (pulse `:7700`) | `docs/operations/staging-environment.md` |
| Smoke-test timer (pulse hourly) | `docs/operations/smoke-testing.md` |
| Branch policy | `docs/operations/OPERATING-SINGLE-BRANCH.md` |
| End-to-end team-ready test (8 scenarios) | `test/e2e-team-ready.sh` |

## If the graph is down

`mycelium doctor --target dev` tells you within a few seconds. Cascade:
1. Check [https://github.com/Qubit-Capital/maverick/actions](https://github.com/Qubit-Capital/maverick/actions) for red CI smoke tests.
2. Check pulse-server's `mycelium-smoke.service` timer (`systemctl list-timers mycelium-smoke`).
3. If both dev + prod are down, the Bolt proxies on pulse may have tripped. SSH: `systemctl restart bolt-proxy-dev bolt-proxy-prod`.

## What NOT to do

- Don't install Neo4j, Ollama, or Qdrant to read the graph. The binary embeds what it needs.
- Don't fork the graph schema in a branch without `mycelium drift` to preview impact.
- Don't paste secrets into an agent conversation. Session traces go to LangSmith.
- Don't bypass `mycelium` with raw `cypher-shell` or direct Bolt calls — those leave no trace, fire no protocols, and fragment the graph's self-model.

## Version + support

`mycelium version` prints the embedded version stamp. Open an issue at [Qubit-Capital/maverick](https://github.com/Qubit-Capital/maverick/issues) with the stamp + a minimal repro.
