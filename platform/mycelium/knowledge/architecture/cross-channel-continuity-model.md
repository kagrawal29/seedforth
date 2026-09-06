---
id: architecture-cross-channel-continuity-model
category: architecture
type: knowledge
version: 1
discovered: 2026-04-09
last-validated: 2026-04-09
confidence: high
source: Sahil LangSmith traces 2026-04-09 — turns 07:00–07:28, 4.6M+ tokens; docs/product/memory/cross-channel-continuity-rules.md
tags: [memory, continuity, deal-context, cross-channel, continuity-contexts, work-unit, members, multi-deal, fund-membership, authorization, rls, schema]
relevant-when: designing memory persistence, building deal context across channels, implementing continuity_contexts table, multi-deal or multi-fund scenarios, cross-channel session design
related: [architecture-memory-layer-decisions, architecture-configurable-per-fund-pattern]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Cross-Channel Continuity Model — Work-Unit + Members (SETTLED)

## What
The continuity architecture uses a work-unit + scoped-members model, NOT a single-anchor model. This enables conversations spanning multiple deals, people, or funds within a single context — which is how real VC workflows actually run.

## The Core Problem With Single-Anchor
The initial model assumed one `(anchor_type, anchor_id)` per continuity context. This breaks for:
- Cross-deal comparison: "Compare Acme and DataFlow on team strength" → two deal_ids, one conversation
- Multi-fund discussion: partner covers two funds, discusses both in one session
- Team diligence: 3 team members each contribute to the same DD context

## The Work-Unit + Members Model

### Schema
- `continuity_contexts` table: `context_type` column (e.g., "deal_dd", "portfolio_review") defines the work unit
- `continuity_context_members` table: each member is a `(context_id, member_type, member_id)` row — deals, people, funds all represented as members
- No single anchor; N members per context

### Authorization
- Per-member `fund_membership` checks on insert, retrieval, and context reuse
- Authorization boundary lives on members, not contexts
- Inaccessible members filtered silently during context assembly (not hard errors)
- Cross-fund leakage prevented: `fund_id = NULL` only allowed for org-scoped contexts with explicit `org_id` scope check

### Key Fixes Applied (2026-04-09)
1. Index `idx_unique_deal_context` fixed: was incorrectly scoped to `(fund_id, context_type, status)` → only one active context per fund, not per deal. Fixed to `(fund_id, deal_id, context_type, status)`.
2. Round-trip authorization: retrieval validates membership, not just insert
3. Context reuse path also validates membership
4. Cross-fund member authorization: per-member fund_membership checks (not just context-level org_id)

## Why Work-Unit + Members Beats Single-Anchor
| Aspect | Single-Anchor | Work-Unit + Members |
|--------|--------------|---------------------|
| Multi-deal conversations | Broken | Native |
| Multi-fund scenarios | Broken | Supported via member scoping |
| Authorization boundary | Context level | Member level (more precise) |
| Schema complexity | Simpler | Slightly more (worth it) |
| VC workflow coverage | ~60% | ~95% |

## How to Apply
1. Use `context_type` to classify the work being done (not the entity being discussed)
2. Add entities to `continuity_context_members`, not as a single anchor field
3. Every retrieval path must check per-member fund_membership — don't trust context-level authorization alone
4. Unique index must include both `fund_id` AND `deal_id` (or equivalent entity) — not just `fund_id`
5. Inaccessible members: filter silently, don't error — partial assembly is valid

## Evidence
- Sahil LangSmith traces 2026-04-09 (turns 07:00–07:28, ~4.6M+ tokens)
- `docs/product/memory/cross-channel-continuity-rules.md` in VC-AI-Assoicate
- Multiple rounds of teammate review + fix iteration in same session
- Bug in idx_unique_deal_context found and fixed during peer review (turn 07:28:47)
