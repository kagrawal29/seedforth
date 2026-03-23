# SeedForth — Orchestration Root

This is the parent repo for all SeedForth projects. It contains no application code — only this registry and coordination file.

## Conventions

- No emojis in code or commits
- Concise communication — lead with the answer
- Every project has its own git repo (local or remote)
- All remote repos are private under `kagrawal29/`

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
```

## Project Registry

| Project | Folder | GitHub Repo | What It Does | Tech | Status |
|---------|--------|-------------|-------------|------|--------|
| Website | `website/` | `kagrawal29/seedforth-website` | SeedForth landing page, Infinite Agency concept | HTML/CSS/JS | Active |
| Agent-Vinod | `Agent-Vinod/` | `Qubit-Capital/Agent-Vinod` | Discord bot for autonomous project management | Python | Active |
| arie | `arie/` | `kagrawal29/arie` | LinkedIn intelligence agent (single-user prototype) | Python | Active |
| ember | `ember/` | `kagrawal29/ember` | Multi-tenant LinkedIn management (scaled arie) | Python | Active |
| tetrahedron | `tetrahedron/` | `kagrawal29/tetrahedron` | Remote server orchestrator (manages audioworld) | Python | Active |
| audioworld | `audioworld/` | `kagrawal29/audioworld` | LinkedIn outreach system on remote server | Python | Active |
| news-commodity-link | `news-commodity-link/` | `kagrawal29/news-commodity-link` | News/commodity correlation | Python/Flask | Hibernating |
| pulse-dashboard | `pulse-dashboard/` | `kagrawal29/pulse-dashboard` | Next.js dashboard | Next.js | Hibernating |
| AI Product Quotes | `AI_product_quotes/` | `kagrawal29/ai-product-quotes` | Client brief-to-proposal pipeline | — | Config-only |
| Ojas Life | `Ojas-life/` | `kagrawal29/ojas-life` | Brand identity & business docs | — | Config-only |
| Perf Marketing | `performance-markting-dashboard/` | `kagrawal29/performance-marketing-dashboard` | Marketing dashboard mockup | — | Config-only |
| Sports Corridor | `Sports Corridor/` | `kagrawal29/sports-corridor` | Business plans | — | Config-only |
| Solve OS | `solveOS/` | `kagrawal29/solve-os` | Problem Solving as a Service — lead gen intelligence and opportunity matching | Python | Active |
| AI Camera Proposal | `ai_camera_proposal/` | local only | AI road inspection proposal docs | — | Config-only |
| Delta Hub | `delta-projects/delta-hub/` | `kagrawal29/delta-hub` | Delta ecosystem hub | — | Hibernating |

### Relationships

- **arie** is the single-user prototype; **ember** is the multi-tenant production version
- **tetrahedron** orchestrates **audioworld** on a remote server
- **delta-projects/** is a container folder — individual projects inside have their own repos
- **Solve OS** is SeedForth's commercial entry product — uses LinkedIn signals to match problems to solvers, lead gen first

### Per-Project CLAUDE.md

Each project with active development should have its own `CLAUDE.md` at its root describing project-specific conventions, architecture, and current state.

## Workflows

### Adding a new project
1. Create folder in SeedForth root (or clone existing repo)
2. `git init` if new, or ensure `.git/` exists
3. Add entry to the Project Registry table above
4. Add folder to `.gitignore`
5. Optionally create remote: `gh repo create kagrawal29/<name> --private --source=. --push`

### Working on a project
1. `cd <project-folder>/`
2. Work in that project's git context
3. Commits, branches, PRs all happen within the project repo

### Updating this registry
Keep the Project Registry table current when projects are added, archived, or change status.
