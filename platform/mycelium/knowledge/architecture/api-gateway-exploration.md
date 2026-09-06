---
id: architecture-api-gateway-exploration
category: architecture
type: exploration
discovered: 2026-04-10
last-validated: 2026-04-10
confidence: low
source: Abhishek LangSmith traces 2026-04-10 — Zuplo deep dive session (15 turns, 5.99M tokens)
tags: [api-gateway, zuplo, api-management, sse, streaming, pricing, developer-portal]
relevant-when: choosing API management layer, planning customer-facing API, evaluating API gateways, cost estimation for API infrastructure
related: [architecture-tech-stack-completed, architecture-production-readiness-gap]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Active Exploration: API Gateway / Management Layer (Zuplo)

## What
Abhishek is evaluating Zuplo as an API management layer for Maverick's customer-facing API. Research is in progress — coordinate before making API gateway decisions.

## Who
Abhishek — 2026-04-10, VC-AI-Associate context

## Key Findings So Far

### Zuplo Pricing (confirmed from pricing page)
| Plan | Price | Requests/mo | Notes |
|------|-------|-------------|-------|
| Free | $0/mo | 100K | Basic features |
| Builder | $25/mo | 100K included, up to 1M ($100/100K overage) | |
| Enterprise | Custom ($1,000+/mo annual) | Unlimited | Required for SSE |

### Critical Finding: SSE Streaming Requires Enterprise
AI streaming endpoints (SSE) through Zuplo require the Enterprise plan ($1,000+/mo). This is a hard feature gate — no workaround on Free/Builder tiers. Since Maverick's AI agents stream responses to users, this constraint is architecturally significant.

### Architecture
Zuplo uses a reverse proxy on Web Workers (Cloudflare-like). TypeScript-native policies, 89+ built-in policies, GitOps workflow. Auto-generates API documentation from OpenAPI specs (relevant since PostgREST generates OpenAPI).

### Social Media Signal
Zero relevant practitioner discussions found across Twitter and Reddit for API management platforms. Xpoz MCP was installed for social search — still returned no signal. Zuplo has only 15 G2 reviews — well-regarded but small user base.

## Status
OPEN — research in progress. Abhishek is evaluating whether an API management layer is needed on top of the existing Hono + PostgREST stack. The SSE cost gate may be a deciding factor.

## Context
The settled tech stack (see `tech-stack-completed.md`) now uses **Hono** (not Next.js API routes) for AI streaming, webhooks, MCP, auth flows, and PostgREST for CRUD. An API management layer like Zuplo would add: rate limiting, API keys, developer portal, and documentation. The question is whether those features justify the cost vs. building them with Hono middleware and existing tools.

## Evidence
- Abhishek LangSmith traces, 2026-04-10 (turns 1-10, 5.99M tokens)
- Multi-agent research deployed (3 agents for Zuplo deep dive)
- Xpoz MCP installed for social media search validation
