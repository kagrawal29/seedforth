# SeedForth — Orchestration Root

This is the parent repo for all SeedForth projects. It contains no application code — only this registry and coordination file.

## Core principle — think in graph, not files and scripts

Mycelium (the delta-server Neo4j graph, `bolt://143.110.226.214:7687`) is the system's **program**, not just its memory. New behavior, rules, capabilities, decisions, cadence, and state all live IN the graph as nodes (`:Protocol`, `:CypherAtom`, `:Knowledge`, `:Model`, `:SubAgent`, `:Decision`, …), executed by `graph-runner.py` on heartbeat/dream/deep cadences. Files and scripts are only for external I/O (`:ExternalAtom`) — webhooks, message sending, attachment downloads.

Before writing a Python script or a config file, ask: **does this belong in the graph?** Write a node and let the graph-runner execute it.

- Capability is self-describable — `:CypherAtom.semantic` lets agents discover what they can do by meaning.
- State and the rules that transform it live together — no drift between a script and the data it reads.
- Hebbian hardening (`fire_count` on `QueryTrace`) only works when the behavior lives in the graph.

## Conventions

- No emojis in code or commits
- Concise communication — lead with the answer
- Every project has its own git repo (local or remote)
- All remote repos are private under `kagrawal29/`
- Never request `delete_repo` scope on GitHub CLI
- Docs and strategy before code when scaffolding new projects

## Directory Structure

```
SeedForth/
  CLAUDE.md              # This file — the orchestration brain
  .gitignore
  website/               # Git clone of kagrawal29/seedforth-website
  docs/                  # PDFs, docx, loose research docs
  Agent-Vinod/           # Discord bot (Qubit-Capital/Agent-Vinod)
  ai_camera_proposal/    # Camera proposal docs
  AI_product_quotes/     # Client brief-to-proposal pipeline
  arie/                  # LinkedIn intelligence agent (single-user)
  audioworld/            # LinkedIn outreach system on remote server
  delta/                 # Discord agent platform (own repo)
  delta-projects/        # Delta ecosystem container
    bootcamp-delta/
    cajon-sensei/
    flowing-reels/
    delta-hub/
    test-hub-check/
  ember/                 # Multi-tenant LinkedIn management
  news-commodity-link/   # News/commodity correlation
  Ojas-life/             # Brand identity & business docs
  performance-markting-dashboard/  # Marketing dashboard mockup
  pulse-dashboard/       # Next.js dashboard
  Sports Corridor/       # Business plans
  solveOS/               # Problem Solving as a Service — lead gen intelligence
  tetrahedron/           # Remote server orchestrator
  revti-digital/         # Charlie agent system for Revti Digital
  flowing-indian/        # Flowing Indian website (Next.js, Vercel)
  sceneforth-os/         # Sceneforth OS Starter Reel Pack micro-earner (Next.js, local only)
  seedforthing/          # SeedForth dream-to-reality pipeline (PPIS lead-gen game, Delta-managed)
```

## Project Registry

| Project | Folder | GitHub Repo | What It Does | Tech | Status |
|---------|--------|-------------|-------------|------|--------|
| Website | `website/` | `kagrawal29/seedforth-website` | SeedForth landing page, Infinite Agency concept | HTML/CSS/JS | Active |
| Agent-Vinod | `Agent-Vinod/` | `Qubit-Capital/Agent-Vinod` | Discord bot for autonomous project management | Python | Active |
| arie | `arie/` | `kagrawal29/arie` | LinkedIn intelligence agent (single-user prototype) | Python | Active |
| ember | `ember/` | `kagrawal29/ember` | Multi-tenant LinkedIn management (scaled arie) | Python | Active |
| tetrahedron | `tetrahedron/` | `kagrawal29/tetrahedron` | Remote server orchestrator (manages audioworld) | Python | Active |
| delta | `delta/` | `kagrawal29/delta` | Discord bot giving projects their own Claude Code | Python | Active |
| audioworld | `audioworld/` | `kagrawal29/audioworld` | LinkedIn outreach system on remote server | Python | Active |
| news-commodity-link | `news-commodity-link/` | `kagrawal29/news-commodity-link` | News/commodity correlation | Python/Flask | Hibernating |
| pulse-dashboard | `pulse-dashboard/` | `kagrawal29/pulse-dashboard` | Next.js dashboard | Next.js | Hibernating |
| AI Product Quotes | `AI_product_quotes/` | `kagrawal29/ai-product-quotes` | Client brief-to-proposal pipeline | — | Config-only |
| Ojas Life | `Ojas-life/` | `kagrawal29/ojas-life` | Brand identity & business docs | — | Config-only |
| Perf Marketing | `performance-markting-dashboard/` | `kagrawal29/performance-marketing-dashboard` | Marketing dashboard mockup | — | Config-only |
| Sports Corridor | `Sports Corridor/` | `kagrawal29/sports-corridor` | Business plans | — | Config-only |
| Solve OS | `solveOS/` | `kagrawal29/solve-os` | Problem Solving as a Service — lead gen intelligence and opportunity matching | Python | Active |
| Revti Digital | `revti-digital/` | `kagrawal29/revti-digital` | Charlie agent system for Revti Digital — Discord + Drive + Gmail | Python | Active |
| Flowing Indian | `flowing-indian/` | `kartiksahu/flowing-indian-website` | Movement/flow practice site — marketing + events/Razorpay funnel. Deploys to flowingindian.com via Vercel | Next.js 16 / TS / Tailwind | Active |
| AI Camera Proposal | `ai_camera_proposal/` | local only | AI road inspection proposal docs | — | Config-only |
| Delta Hub | `delta-projects/delta-hub/` | `kagrawal29/delta-hub` | Delta ecosystem hub | — | Hibernating |
| Mycelium | `tetrahedron/projects/mycelium/` (repo); graph on delta-server `mycelium-neo4j` :7687 | `kagrawal29/mycelium` | **Single source of truth** — living knowledge graph mapping complete system state (projects, agents, goals, tools, decisions, fleet health). Neo4j + APOC + Qdrant + Ollama. Delta and Charlie are interfaces over it. | Python / Cypher | Active |
| Maverick | `tetrahedron/projects/maverick/` | `Qubit-Capital/maverick` | Deprecated team-distribution fork of mycelium for Qubit Capital residency. Not part of SeedForth's active system; its CLI references are purged. | Python / Cypher | Deprecated |
| Sceneforth OS | `sceneforth-os/` | local only | Starter Reel Pack micro-earner — guided brand intake, bespoke campaign concept preview, test-mode Razorpay checkout gate. Thin customer-facing slice of the wider Sceneforth OS vision; not the full production system. Built, local-only, not deployed. | Next.js 16 / TS strict / Tailwind | Built (not live) |
| Heritage Food Diary | `heritage-diaries` (delta-managed, server-only) | local only | Om Kanwar's heritage food brand — agentic brand-partnership machine (₹10L/mo goal). First Charlie OS deployment: one CEO agent (Charlie) over revenue/research/operations divisions. Uses WhatsApp + LinkedIn + Instagram (Unipile). | Python / Delta | Active |
| Seedforthing | `seedforthing/` | local only | SeedForth's own dream-to-reality pipeline — PPIS lead-gen game (LinkedIn outreach via Unipile, 9-min sprint, 21-day arc) with a self-healing coordinator. | Python / JS | Active |

### Relationships

- **arie** is the single-user prototype; **ember** is the multi-tenant production version
- **tetrahedron** orchestrates **audioworld** on a remote server; observatory monitors **delta**
- **delta** was extracted from tetrahedron into its own repo; server path is `/opt/delta`
- **delta-projects/** is a container folder — individual projects inside have their own repos
- **Solve OS** is SeedForth's commercial entry product — uses LinkedIn signals to match problems to solvers, lead gen first
- **Mycelium is the single source of truth.** The living graph lives on delta-server (`mycelium-neo4j`, `bolt://143.110.226.214:7687`, ~15k nodes). It maps complete system state — projects, agents, goals, tools, decisions, fleet health — and is kept current by the ingest/heartbeat cron. Delta and Charlie are interfaces that navigate it.
- **Maverick is deprecated.** The old Qubit-Capital team-distribution CLI + pulse-server graphs (bolt-proxy :7698/:7699) are legacy and off-limits for SeedForth operations. References are purged from the agent templates.
- **Delta platform has two personas per project:** **Delta** (internal/Discord, full access) and **Charlie** (client-facing/WhatsApp, warm non-technical voice, scoped permissions). Clients see only Charlie.
- **Messaging channels:** **WhatsApp** via `whatsapp_webhook.py` + `whatsapp_config.json` on delta-server (agent number `+48 739 478 485`, routing in `/opt/delta/tools/whatsapp_config.json`). **LinkedIn + Instagram** via **Unipile** (`api38.unipile.com:16885`). Separate mechanisms.
- **Charlie OS** is the "one CEO agent over divisions" pattern, first deployed in **Heritage Food Diary**. Its intelligence layer is the mycelium graph — agents read/write it via `graph-tool.py`.

### Per-Project CLAUDE.md — Session Continuity

Each project with active development MUST have its own `CLAUDE.md` at its root. This is how project-specific agents pick up and continue without losing context.

A project CLAUDE.md must include:
- **Current State** — what phase the project is in, what exists, what doesn't
- **Next Steps** — ordered list of what to do next, so a fresh session knows exactly where to start
- Project overview, architecture, conventions, data models
- Infrastructure details (APIs, MCP servers, storage)

When setting up a new project, always create a CLAUDE.md with current state and next steps. When finishing a work session on a project, update the current state and next steps before stopping. This way, `cd <project> && claude` starts a session that can continue autonomously.

MCP servers and tools should be configured in `<project>/.claude/settings.json` so they auto-connect when working from that directory.

## Workflows

### Adding a new project
1. Create folder in SeedForth root (or clone existing repo)
2. `git init` if new, or ensure `.git/` exists
3. Create `CLAUDE.md` with current state, next steps, and project overview
4. Configure MCP servers in `<project>/.claude/settings.json` if the project needs external APIs
5. Add entry to the Project Registry table above
6. Add folder to `.gitignore`
7. Optionally create remote: `gh repo create kagrawal29/<name> --private --source=. --push`

### Working on a project
1. `cd <project-folder>/`
2. Work in that project's git context
3. Commits, branches, PRs all happen within the project repo

### Updating this registry
Keep the Project Registry table current when projects are added, archived, or change status.
