# Mycelium — SeedForth graph control plane

This is the Mycelium component of the SeedForth platform repository. The
platform architecture, repository topology, runtime topology, and sync rules
live in the parent directory; start with
[`../../SEEDFORTH-PLATFORM-PLAN.md`](../../SEEDFORTH-PLATFORM-PLAN.md).

Mycelium is a Neo4j-based graph the SeedForth platform thinks through. It
holds decisions, code structure, project state, protocols, and relationships.
The live graph runs in `mycelium-neo4j` on `185.192.96.100`; source-controlled
Cypher and protocols define reviewed behavior.

This directory is the deployed, sanitized platform import. See
[`MIGRATION.md`](MIGRATION.md) for provenance and
[`LEGACY-BOUNDARY.md`](LEGACY-BOUNDARY.md) for the files that are not active
runtime entrypoints. Legacy Maverick/Pulse material is reference-only.

## Current SeedForth operation

The canonical platform repository is `kagrawal29/seedforth`; use the parent
platform docs for architecture and deployment. The live graph is Neo4j on the
SeedForth runtime server (`185.192.96.100`), and graph behavior is executed by
Delta's graph runner under systemd. Do not use the historical installer and
target model below to deploy SeedForth services.

The standalone Mycelium repository is retained for provenance. New changes
land in `platform/mycelium`, are tested from the platform root, and are
deployed only through an immutable SeedForth release.

> The remaining sections are retained as historical contributor/reference
> material from the imported Mycelium project. Their Maverick, Pulse-server,
> and old target names do not describe the active SeedForth topology.

This repo is the team distribution. Clone it, run one script, and you're in.

---

## 30 seconds — install the binary (recommended)

v1.0.0 ships as a static Go binary. No Python, no JDK, no WSL for reads — one file on your PATH and you can query the team's graph from any shell, any IDE, and every Claude Code subprocess on your laptop.

**One-time prereq:** [GitHub CLI](https://cli.github.com/) + `gh auth login` (maverick is a private repo, so release assets require auth).

### macOS / Linux

```bash
gh release download -R Qubit-Capital/maverick -p install.sh && bash install.sh
mycelium --target dev shell "MATCH (b:Being) RETURN b.project, b.autonomous_score ORDER BY b.project"
```

### Windows (native PowerShell — no WSL needed for the binary)

```powershell
gh release download -R Qubit-Capital/maverick -p install.ps1
powershell -ExecutionPolicy Bypass -File .\install.ps1
mycelium --target dev shell "MATCH (b:Being) RETURN b.project, b.autonomous_score ORDER BY b.project"
```

The installer symlinks `mycelium` system-wide (`/usr/local/bin` on Unix, user PATH on Windows), so every Claude Code session on your machine — in any repo, not just maverick — can call it. See [`AGENTS.md`](AGENTS.md) for the "Use from Claude Code" quick reference + a paste-into-`~/.claude/CLAUDE.md` snippet.

**Writes** (contributing new Cypher, protocols, invariants) still use the repo-based contributor path below.

---

## For contributors — clone the repo

### macOS / Linux

```bash
gh repo clone Qubit-Capital/maverick   # or: git clone https://github.com/Qubit-Capital/maverick.git
cd maverick
bash setup-team.sh
mycelium --target dev shell "MATCH (b:Being) RETURN b.project, b.autonomous_score ORDER BY b.project"
```

### Windows contributors (via WSL2)

One-time, from **PowerShell as Administrator**:

```powershell
wsl --install -d Ubuntu
```

Reboot when prompted. On next login, Ubuntu opens a terminal and asks you to pick a Linux username + password (any, keep it simple).

Then, in the **Ubuntu** shell (not PowerShell):

```bash
sudo apt update && sudo apt install -y git curl python3 python3-pip
cd ~
git clone https://github.com/Qubit-Capital/maverick.git
cd maverick
bash setup-team.sh
mycelium --target dev shell "MATCH (b:Being) RETURN b.project, b.autonomous_score ORDER BY b.project"
```

Everything after this point works the same as macOS / Linux — you're in a real Ubuntu environment. Use VS Code with the "Remote - WSL" extension for a seamless editor experience (`code .` from the Ubuntu shell inside your maverick folder). Full Windows details: [`docs/windows-setup.md`](docs/windows-setup.md).

---

### Verify: six rows back

You should see:

```
maverick-dev                  100.0
maverick-dev-friend           100.0
maverick-market-research      100.0
maverick-marketing            100.0
mycelium                      100
vc-ai-associate               100.0
```

If you see those, you're connected to the live shared graph. Read-only. 47,000+ nodes, pulsing every 30 seconds.

---

## The three targets

Everything you do is against one of these:

| target | where | write? | use for |
|---|---|---|---|
| **`local`** | your laptop | **yes** | experiment, edit, break things |
| **`dev`** | shared pulse-server | **no — read-only** | see what the team knows, query, ask questions |
| **`prod`** | shared pulse-server | **no — read-only** | product-facing; leave alone unless you work on it |

Switch per command with `--target`:

```bash
mycelium --target dev shell "MATCH (g:Gap) WHERE g.severity='critical' RETURN g.label LIMIT 5"
mycelium --target local shell "CREATE (:MyExperiment {note: 'trying stuff'})"
```

No `--target` flag defaults to `local`, so accidental writes never hit the shared graph.

---

## What you can do from here

```bash
# Ask questions (semantic search, zero LLM cost)
mycelium --target dev ask "what patterns exist for handling authentication"

# Raw Cypher (reads on dev, anything on local)
mycelium --target dev shell "MATCH (p:Project) RETURN p.name, p.role_in_forest"

# Pull a writable copy of the current dev graph into your local Neo4j
mycelium fork dev

# Local experimentation — now your edits don't affect anyone
mycelium --target local shell "MERGE (k:Knowledge {node_id: 'my-first-note'}) SET k.content = 'learned X today'"
```

Full command reference: [`docs/TEAM_GUIDE.md`](docs/TEAM_GUIDE.md).

---

## Contributing changes back

1. Branch: `git checkout -b dev/<your-name>/<short-desc>`
2. Edit `.cypher` in `graph/protocols/` or `graph/knowledge/`, or Python in `scripts/`
3. Test against your local graph: `mycelium --target local shell < graph/knowledge/my-new-file.cypher`
4. Commit, push, open a PR against `main`
5. Reviewer merges → admin fires the new cypher against `dev` → everyone sees it on the next heartbeat

Three merge gates — why a PR gets rejected:

1. **Forest Promise** — every node must carry `{project: X}`. No silent cross-subgraph writes. See `:SovereigntyRule` nodes in the graph.
2. **Test coverage** — new Protocols need a TestCase; new Invariants need a heal_protocol.
3. **Idempotence** — use `MERGE` not `CREATE`; no unguarded `DETACH DELETE`.

Full list with exact reject reasons: [`docs/TEAM_GUIDE.md`](docs/TEAM_GUIDE.md).

---

## What's actually running

- **Neo4j 2026.03.1** (dev + prod instances on `pulse-server`, bound to 127.0.0.1)
- **bolt-proxy** on public ports `7698` (dev) and `7699` (prod) — enforces read-only
- **Qdrant** (semantic embeddings, mirrored on pulse and delta) — 52,481 vectors, 768d nomic
- **Ollama** with `nomic-embed-text` for local embedding calls (zero-cost semantic search)
- **`apoc.periodic.repeat('forest-heartbeat', 30)`** — updates every `:Being` every 30s

You don't need to know any of this to use the graph. You'll pick it up as you touch specific pieces.

---

## If something breaks

| symptom | fix |
|---|---|
| `mycelium --target dev shell` hangs or returns nothing | `mycelium --target dev status` — if silent, check bolt-proxy: `curl -I http://5.78.206.137:7698` |
| `Authentication failure` | Re-run `bash setup-team.sh` — credentials refresh from the repo |
| `target 'dev' is read-only` on a read | Older CLI. `git pull && bash setup-team.sh` |
| CLI not found after setup | Close + reopen your terminal (`$PATH` reloads), or run `~/.local/bin/mycelium` directly |
| Native Windows errors (`bash: command not found`) | You need WSL — see [`docs/windows-setup.md`](docs/windows-setup.md) |
| Everything looks fine but queries return weird data | `mycelium --target dev status` — if heartbeat >60s stale, ping ops |

Deeper: [`docs/TEAM_GUIDE.md`](docs/TEAM_GUIDE.md) and [`docs/credentials.md`](docs/credentials.md).

---

## When to reach for what

| you want to | look at |
|---|---|
| Read the forest and ask questions | this README + [`docs/TEAM_GUIDE.md`](docs/TEAM_GUIDE.md) |
| Set up on Windows | [`docs/windows-setup.md`](docs/windows-setup.md) |
| Understand architecture / how it all fits | [`MYCELIUM.md`](MYCELIUM.md) + [`OPERATING-SYSTEM.md`](OPERATING-SYSTEM.md) |
| Contribute a change | [`CONTRIBUTING.md`](CONTRIBUTING.md) + [`docs/TEAM_GUIDE.md`](docs/TEAM_GUIDE.md) |
| Rotate credentials (operator only) | [`docs/credentials.md`](docs/credentials.md) |
| Deploy / ops | [`deploy/`](deploy/) |
| See what the graph already knows | query it: `mycelium --target dev ask "<anything>"` |

---

**Core principle:** the graph is the source of truth. This README, `docs/`, `CLAUDE.md`, every `.cypher` file — these are pointers. If any of them disagree with the graph, trust the graph.

```bash
mycelium --target dev ask "what matters right now"
```

That's a good way to start.
