---
id: architecture-postgrest-client-type-safety
category: architecture
type: knowledge
discovered: 2026-04-10
last-validated: 2026-04-10
confidence: high
source: Abhishek LangSmith traces 2026-04-10 — 3-advocate group debate (postgrest-advocate, orval-advocate, openapi-advocate); commit 78064b8f in VC-AI-Assoicate
tags: [postgrest, postgrest-js, orval, openapi-fetch, hono-client, type-safety, api-client, evaluated-alternative]
relevant-when: choosing API client library, implementing PostgREST calls from frontend, setting up type-safe API layer, working with Hono endpoints
related: [architecture-tech-stack-completed, architecture-phase1-decisions-settled, architecture-api-gateway-exploration]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# PostgREST Client & API Type Safety — postgrest-js Chosen (SETTLED)

## What
The API client strategy is decided: **postgrest-js** (`@supabase/postgrest-js`) for PostgREST endpoints (90% of API surface), **hono/client** for Hono custom endpoints (10%). Orval and openapi-fetch were evaluated and rejected.

## Evaluation

Abhishek ran a group discussion with 3 advocate agents, each arguing for a different approach:

| Option | Advocate | Verdict |
|--------|----------|---------|
| **postgrest-js** | postgrest-advocate | **Chosen** — native resource embedding support, type-safe query builder, reads foreign key direction from `database.types.ts` |
| **Orval** (code generation from OpenAPI) | orval-advocate | **Conceded** — generates wrappers, but can't match postgrest-js's native embedding. "PostgREST's value IS resource embedding." |
| **openapi-fetch** (generic OpenAPI client) | openapi-advocate | **Conceded** for PostgREST, recommended for Hono. Split emerged: use hono/client (simpler) instead. |

All 3 converged unanimously on postgrest-js for the PostgREST layer.

## Why postgrest-js Wins

1. **Resource embedding is native**: `postgrest-js` understands PostgREST's `select=*,companies(*)` syntax. Orval treats it as a generic REST API and loses this.
2. **Type safety from schema**: Types come from `supabase gen types` which produces `database.types.ts` with `Relationships` sections. postgrest-js reads foreign key direction to know when a join returns an object vs array.
3. **No code generation step**: Orval requires a build step to generate client code from OpenAPI spec. postgrest-js works directly.

## Why Orval Was Rejected

Orval generates API client wrappers from OpenAPI specs. For PostgREST, this adds a layer that obscures the underlying query power. Resource embedding (the key PostgREST feature) isn't expressible through standard OpenAPI, so Orval can't generate type-safe embedded queries. Even the Orval advocate conceded: "PostgREST's value IS resource embedding."

## Hono Client Decision

For the 10% of API calls that go to Hono custom endpoints (AI streaming, webhooks, MCP, auth), **hono/client** is recommended over openapi-fetch. hono/client extracts types directly from route definitions — zero-config, no OpenAPI spec needed, built-in.

## Views vs Embedded Queries

Abhishek explored using Postgres views as an alternative to resource embedding. Finding: views work well for **many-to-one** relationships (deal -> company) — create a `deal_with_company` view that joins them, PostgREST exposes it, Orval can generate types from the OpenAPI spec. But views **break down for many-to-many** joins and complex nested relationships where PostgREST's native resource embedding (`select=*,companies(*),contacts(*)`) handles them cleanly. The deeper Abhishek dug (2026-04-10 session, turns exploring views vs embedding), the more the postgrest-js decision was validated — resource embedding is the core value proposition of PostgREST, and postgrest-js is the only client that understands it natively.

## How to Apply
1. Install `@supabase/postgrest-js` for PostgREST API calls
2. Generate types with `supabase gen types` from your Postgres schema
3. Use resource embedding for related data (`select=*,companies(*),contacts(*)`)
4. For Hono endpoints, use `hono/client` with route-level type inference
5. Do not introduce Orval or openapi-fetch for PostgREST — the evaluation is complete

## Evidence
- Abhishek LangSmith traces, 2026-04-10 (group debate with 3 advocate agents)
- Commit 78064b8f (VC-AI-Assoicate, 2026-04-10T11:32)
- Commit 253c55d (VC-AI-Assoicate, 2026-04-10T13:06) — hono/client, factory pattern, Zod mutations added
- docs/research/tech-stack-decisions.md — Decision #44
- Abhishek LangSmith traces 2026-04-10T12:09-12:13 — views vs embedding deep-dive (further validates postgrest-js choice)
