---
id: architecture-tech-stack-completed
category: architecture
type: knowledge
discovered: 2026-04-07
last-validated: 2026-04-10
confidence: high
source: docs/research/tech-stack-decisions.md in VC-AI-Assoicate (commit 6b3c3dd, abhishek6383, 2026-04-10 — PgBouncer pooling + backend workflow; commit 78064b8f — decisions #43-44; commit 529ccc9a — Hono + cloud switch; original commit 103ddd5a, 2026-04-07)
tags: [tech-stack, docker, coolify, keycloak, postgrest, redis, drizzle, minio, nango, trigger-dev, infisical, posthog, langfuse, sentry, hono, deployment]
relevant-when: making backend infrastructure decisions, choosing any service in the stack, deployment planning, cost estimation
related: [architecture-trigger-dev-vs-temporal, architecture-memory-layer-decisions, architecture-security-scanning-stack, architecture-api-gateway-exploration, architecture-postgrest-client-type-safety]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 3
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
  last_scored: 2026-04-12
---

# Full Tech Stack Decisions — 44 Decisions, 3 Pending

## What
44 tech stack decisions are now settled (as of 2026-04-10). 3 remain pending (#22 AI Agent Framework, #23 AI Streaming, #24 Real-time Notifications). The driving constraint: on-premises deployment for enterprise clients + OSS preference + Docker-first. This ruled out Vercel, Clerk, Neon, Upstash, and other vendor-locked SaaS tools.

## Stack Summary

| Layer | Decision | Replaces | Reason |
|-------|----------|----------|--------|
| **Deployment** | Docker + Coolify | Vercel | On-prem requirement |
| **Database** | PostgreSQL 16 + PgBouncer (PostgREST bypasses PgBouncer — has own pool) | Neon/Supabase | Portability, no vendor lock |
| **Auth** | Keycloak (self-hosted) | Clerk | SSO + on-prem required |
| **CRUD API** | PostgREST (auto-generated) | tRPC | 100% CRUD completeness; universal REST for all consumers |
| **Custom API** | **Hono** (replaces Next.js API routes) | Next.js API routes | Lightweight, Web Standards-based, runs on Workers/Node/Bun. Handles AI streaming, webhooks, MCP server, file upload, auth, exports |
| **Caching** | Redis 7 (Docker) | Upstash | Self-hosted, $0 |
| **ORM** | Drizzle + drizzle-zod | — | TypeScript-native, lightweight |
| **Job queue** | Trigger.dev v3→v4 (self-hosted) | Temporal | See trigger-dev-vs-temporal entry |
| **File storage** | MinIO (S3-compatible) | Cloudflare R2 | On-prem capable |
| **Email** | Resend + SMTP fallback | — | Interface pattern for on-prem swap |
| **Integrations** | Nango (self-hosted) | — | 250+ connectors, MIT, $0 self-hosted |
| **Secrets** | Infisical (self-hosted) | — | OSS, Docker |
| **Observability** | **PostHog (cloud) + Sentry (cloud)** + Pino + Prometheus/Grafana + Langfuse + Uptime Kuma | Axiom, LaunchDarkly, LangSmith | PostHog + Sentry switched to cloud — self-hosted versions consume ~2GB RAM each, not worth it for a small team |
| **Payments** | Stripe (V2) | — | Design partners on free plan |
| **Testing** | Vitest + Playwright + DeepEval + k6 | — | Existing frontend stack extended |
| **AI coding** | Claude Code + spec-kit + Superpowers | — | Primary development approach |

## Key Architectural Decisions Explained

### PostgREST replaces tRPC
tRPC is TypeScript-only — can't serve Slack bot, MCP server, external consumers. PostgREST auto-generates complete REST from Postgres schema, guaranteeing 100% CRUD for all 30+ tables. AI-assisted code was missing CRUD operations — PostgREST solves this structurally.

### Nango for integrations
Nango handles OAuth token refresh + rate limiting for 250+ connectors (Salesforce, HubSpot, Gmail, Slack, etc.). Self-hosted Docker, $0 vs $250-500/mo cloud. Decided in context of CRM integration research.

### Sentry + PostHog → Cloud (2026-04-10)
Originally planned as self-hosted (consistent with the "self-host everything" principle). Abhishek evaluated RAM impact: self-hosted Sentry and PostHog each consume ~1-2GB RAM at idle. For a small team during residency, cloud tiers (free/low-cost) provide the same functionality without the infrastructure burden. This is a pragmatic exception to the self-hosted principle — the on-prem option remains available for enterprise deployment later.

### Hono Replaces Next.js API Routes (2026-04-10)
Custom API layer switched from Next.js API routes to Hono. Hono is a lightweight Web Standards-based framework that runs on Workers, Node, Bun, and Deno. It handles AI streaming (SSE), webhooks, MCP server, file upload, auth flows, and PDF exports — keeping the Next.js app focused on frontend rendering.

### Decisions #37-42 (2026-04-10)
Six additional decisions settled by Abhishek: data retention policies, external API design, i18n approach, embedding model selection, resilience patterns, and image processing (Sharp for resize/crop). TipTap + Yjs + Hocuspocus confirmed for rich text collaboration. Papermark for data rooms. Playwright for server-side PDF generation.

### Decision #43: Keycloak Client Integration (2026-04-10)
`@keycloak/keycloak-admin-client` for programmatic Keycloak admin operations (user CRUD, role assignment, realm config). Official Keycloak-maintained package. Commit 78064b8f.

### Decision #44: PostgREST Client & API Type Safety (2026-04-10)
`postgrest-js` (via `@supabase/postgrest-js`) for PostgREST API calls — provides type-safe query building with resource embedding support. For Hono custom endpoints, `hono/client` recommended (zero-config, types from route definitions). Decision validated via 3-advocate group debate (postgrest-advocate, orval-advocate, openapi-advocate — unanimous convergence). See `architecture-postgrest-client-type-safety` for full evaluation. Commit 78064b8f.

### PgBouncer Pooling Strategy (2026-04-10)
PostgREST connects **directly to Postgres**, bypassing PgBouncer. All other services (Hono, Trigger.dev, Nango, Keycloak) connect through PgBouncer. Reason: PostgREST has a built-in connection pool and uses **prepared statements** (pre-compiled SQL queries reused across requests). PgBouncer in transaction mode strips prepared statement state between transactions, breaking PostgREST's optimization. Routing PostgREST through PgBouncer would degrade performance, not improve it. Commit 6b3c3dd.

### Backend Development Workflow Finalized (2026-04-10)
`docs/backend-development-workflow.md` in VC-AI-Associate rewritten with all 40 finalized tech stack decisions (Section 2 was "heavily outdated" — still referenced old playbook decisions like tRPC, Clerk, etc.). Now consistent with `tech-stack-decisions.md`. Development methodology (spec-kit, TDD, cross-model review) and quality gates unchanged. Remaining blockers before development starts: #22 (AI Agent Framework), #23 (AI Streaming). Commits 253c55d, 6b3c3dd.

### Complete Docker Compose
26 containers estimated (up from 16 in initial plan): app, hono-api, postgrest, postgres, pgbouncer, redis, minio, keycloak, trigger-dev, nango, langfuse, uptime-kuma, clamav, infisical, prometheus, grafana, nango-server, hocuspocus, falkordb, and more + Traefik reverse proxy. Sentry and PostHog offloaded to cloud.

### 3 Pending Decisions
| # | Topic | Status | Dependency |
|---|-------|--------|------------|
| 22 | AI Agent Framework | Pending | — |
| 23 | AI Streaming | Pending | Depends on #22 |
| 24 | Real-time Notifications | Pending | — |
| 29 | Memory Layer | Pending confirmation | Waiting on memory team |

## Evidence
- `docs/research/tech-stack-decisions.md` (VC-AI-Assoicate)
- Authored: Abhishek + Claude Code (April 6-10, 2026)
- Original commit: 103ddd5a (2026-04-07T05:19)
- Hono + cloud switch: 529ccc9a (2026-04-10T08:57)
- Decisions #37-42: 42ee3c98 (2026-04-10T08:02)
- Merged PR #8: 3248fc3c (2026-04-10T08:06)
- Decisions #43-44: 78064b8f (2026-04-10T11:32)
- PgBouncer pooling + backend workflow: 6b3c3dd, 253c55d (2026-04-10T13:25)
- Backend workflow rewrite: Abhishek LangSmith traces 2026-04-10 (13:08-13:27)
- PostgREST client group debate: Abhishek LangSmith traces 2026-04-10 (turns with postgrest-advocate, orval-advocate, openapi-advocate)
