# Deep GitHub Ingest — 2026-04-06
Full history scan of both core repos.

## VC-AI-Assoicate
- **Lifespan:** Nov 15, 2025 - Apr 5, 2026 (142 days)
- **902 commits**, 4 PRs, 3 contributors
- **Primary builder:** NBTEAM-25 (Claude Code agent, 92.5% of commits)
- **Senior architect:** Sahil Agrawal (12 commits — ESLint rules, design system, barrel exports)
- **Early research:** Codex CLI (7 commits — PRD, tech stack decisions)
- **Stack:** Next.js 15, React 19, TypeScript, Tailwind, shadcn/ui, CopilotKit, TipTap, Storybook 10
- **Architecture:** FSD + Atomic Design + Compound Components
- **Quality:** 5-layer defense (pre-commit, pre-push, CI, branch protection, severity escalation)
- **Feature completeness:** Pipeline, Deal Workspace (5 tabs), Design System, Settings, Workflow Builder, Knowledge Base, Watchlist, Voice Notes, Scheduled Tasks, Onboarding, Portfolio Conflict Detection — all DoD complete
- **Missing for production:** Real backend (using fixtures), database layer, auth, deployment pipeline
- **Recent focus:** SSR/hydration fixes, motion audit (Emil Kowalski review), production parity

## maverick-market-research
- **Lifespan:** Mar 26 - Apr 6, 2026 (11 days)
- **15 commits**, 3 PRs (all auto-merged), 38 issues (37 closed), 2 contributors
- **Data operator:** Saurabh Thapa (data collection, scripting, API integration)
- **Analyst/strategist:** Sahil Agrawal (positioning, personas, LinkedIn deep research)
- **Pipeline:** Scrape (dumb/fast/greedy) → LLM Filter → Tag → Analyze → Report
- **Coverage:** Reddit (9,779 raw, 651 relevant), Twitter (35K+ practitioner tweets), LinkedIn (4,210 posts), YouTube (593 videos), G2 (233 reviews), GitHub (37 repos)
- **28 competitors tracked** across 3 tiers + 9 new discoveries
- **18 strategic documents** produced
- **Phase 4 just launched:** Competitor Marketing Research structure (28 brands x 7 platforms)
- **Key finding:** VCs want fewer tools that execute, not more tools that display. AI already core infra.
- **Methodology evolution:** Xpoz keyword search failed (90% noise) → pivoted to TwitterAPI.io, Reddit OAuth API, RapidAPI

## Cross-Repo Observations
- Sahil Agrawal is the common architect across both repos
- Research findings directly map to product features (pain points → feature inventory)
- Both repos use Claude Code with hooks — different patterns (quality gates vs data capture)
- Market research completed Phase 1-3 in 7 days; product frontend built in 142 days
- Product is fixture-based; needs real backend to become production-ready
- Research identified 5 validated market gaps that align with product architecture
