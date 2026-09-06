---
id: architecture-production-readiness-gap
category: architecture
discovered: 2026-04-06
last-validated: 2026-04-06
confidence: high
type: knowledge
source: VC-AI-Assoicate deep analysis — feature-complete frontend, no backend
distributed-to: [VC-AI-Assoicate#5]
effectiveness: null
tags: [production, backend, database, auth, deployment, api, copilotkit, langgraph, fixtures, docker, cicd, staging]
relevant-when: planning backend work, prioritizing residency tasks, assessing what exists vs what's missing, setting up deployment
related: [architecture-fixture-first-development, architecture-memory-layer-decisions, architecture-research-to-product-pipeline, architecture-fsd-audit-critical-issues]
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Production Readiness Gap Analysis

## What
VC-AI-Associate is a feature-complete frontend with zero backend infrastructure. The residency's primary challenge is bridging this gap to enterprise-grade production.

## Why
### What Exists (Done)
- 14 widgets, all with Storybook DoD
- Design system with CI enforcement
- SSR-safe Next.js 15 + React 19
- CopilotKit AI chat integration (fixture-backed)
- 5-layer quality gates
- Motion/accessibility audited

### What's Missing (Critical Path)
1. **Database layer** — no schema, no migrations, no ORM. Fixtures are the current "database."
2. **Authentication/authorization** — no user auth, no session management, no RBAC beyond UI
3. **Real AI backend** — CopilotKit runtime exists but points to mock agent runner, not LLM
4. **LangGraph agents** — referenced in CLAUDE.md as server-only, but no agent code in repo
5. **API layer** — no REST/GraphQL endpoints, no data validation beyond Zod schemas
6. **Deployment** — no Docker, no CI/CD for production, no staging environment
7. **Email/calendar integration** — UI exists but no real Gmail/Calendar API connection
8. **Search** — no full-text indexing, only client-side fixture filtering

### What's Partially Done
- SSR/hydration (5+ fixes in last 2 weeks — stabilizing but fragile)
- Motion interactions (external audit done, 8 fixes applied, may need more)

## How to Apply
The residency should prioritize these workstreams:
1. **Backend API + Database** — enables real data flow, unlocks everything else
2. **Auth** — required before any multi-user testing
3. **AI agent integration** — CopilotKit → real LangGraph agents
4. **Deployment pipeline** — staging environment for team testing
5. **Integration APIs** — Gmail, Calendar, LinkedIn data feeds

## Evidence
- Zero database-related commits in 902-commit history
- CopilotKit mock agent runner at shared/fixtures/mocks/
- No Docker/deployment files in repo
- Service provider pattern (DealRepo, AgentRunner) makes swap feasible
