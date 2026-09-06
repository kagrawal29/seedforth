---
id: architecture-configurable-per-fund-pattern
category: architecture
type: knowledge
discovered: 2026-04-07
last-validated: 2026-04-07
confidence: high
source: docs/phase-1/DECISIONS.md in VC-AI-Assoicate (commit 041ba65b, Codex CLI, 2026-04-06)
tags: [fund-config, multi-tenant, per-fund, thesis, stages, scoring, metrics, schema, JSONB, onboarding]
relevant-when: designing any feature that touches pipeline stages, scoring, round types, deal metrics, or fund-level settings
related: [architecture-fixture-first-development, architecture-production-readiness-gap]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 2
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
  last_scored: 2026-04-12
---

# "Configurable Per Fund" as Core Architectural Pattern

## What
Four independent decisions (pipeline stages, deal metrics, round types, scoring dimensions) all resolved to the same answer: configurable per fund. This is an explicit architectural theme, not a coincidence. Every fund-facing data structure must be runtime-configurable, not hardcoded.

## Why
Maverick's positioning is "learns YOUR fund." Different VC funds have fundamentally different stage taxonomies (Seed/Series A vs Pre-seed/Seed/Series A/Growth), scoring frameworks (market size vs team vs traction vs moat), and metrics they care about ($MRR, $ARR, headcount, NPS). Hardcoded enums or configs will force every fund to work in Maverick's model, not theirs.

Decided during Phase 1 audit (Q6, Q8, Q9, Q10 from QUESTIONS.md, Sahil Agrawal):
- **Q6**: DD/IC pipeline ordering → configurable stages per fund
- **Q8**: Deal.metrics schema → configurable per fund (needs design session)
- **Q9**: Round types → configurable per fund
- **Q10**: Scoring dimensions → configurable per fund (6-8 defaults, fund can add/remove)

## Architectural Implications (derived from DECISIONS.md)
1. **Fund-level configuration table** in Sprint 0 — needed before any fund-facing features
2. **Thesis setup during onboarding is critical UX** — where all fund-specific config is captured
3. **Default configurations must work standalone** — a fund that skips customization still gets full value
4. **Backend must use JSONB or config tables** — not hardcoded enums
5. **Frontend design tokens** (pipeline.ts etc.) must be replaced with runtime configuration from API

## How to Apply
- Before adding any new fund-facing field, ask: "should this be fund-configurable?"
- Default to yes — it's easier to remove configurability than to add it later
- Onboarding screen is where fund config is collected — all decisions flow through there
- Schema: use JSONB columns for extensible metrics, lookup tables for stages/scoring

## Evidence
- `docs/phase-1/DECISIONS.md` — Q6, Q8, Q9, Q10 all explicitly resolve to "configurable per fund"
- Note from DECISIONS.md: "This 'configurable per fund' pattern is consistent with the positioning: 'Maverick learns YOUR fund.'"
- Source commit: 041ba65b (2026-04-06T16:55, Codex CLI)
