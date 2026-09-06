---
id: patterns-spec-reading-guides
category: patterns
type: knowledge
discovered: 2026-04-10
last-validated: 2026-04-11
confidence: medium
source: Ankit-S LangSmith traces 2026-04-10 — spec-to-ship v7 update session + pipeline stage editor spec validation + channel preferences feature (2 independent validations, same person); v8 published 2026-04-11 (commit e57b16d1 VC-AI-Assoicate) adding 2 new Agent Contract rules
tags: [spec-to-ship, specs, reading-guide, documentation, code-review, technical-writing, playbook]
relevant-when: writing technical specs, reviewing specs with non-technical stakeholders, updating spec-to-ship playbook, writing interface definitions
related: [architecture-fixture-first-development, pattern-claude-code-agent-as-primary-builder, pattern-spec-isolation-principle, patterns-spec-tech-separation]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 2
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
  last_scored: 2026-04-12
---

# Reading Guides for Technical Specs

## What
Every technical block in a spec (TypeScript interfaces, enums, type definitions, code snippets) should include an inline "Reading Guide" — a plain-language explanation that maps each technical element back to the product concept it represents. Ankit-S added this as a NO-SKIP rule in spec-to-ship playbook v7.

## Why
Technical specs serve two audiences: the AI agent that implements them and the human who reviews them. Without reading guides, a reviewer sees `fitScore: number | null` and has to reverse-engineer what that means in the product. With a reading guide, each line points back to "this is the AI-calculated score shown as the colored badge on the deal card."

This emerged from Ankit-S building the channel preferences feature. The spec's TypeScript interfaces were correct but opaque — a reviewer couldn't verify correctness without deep codebase knowledge. Adding reading guides made the spec self-reviewing.

## How to Apply
1. After every `interface`, `enum`, or `type` block in a spec, add a **Reading Guide** section
2. Each line in the reading guide maps one technical field to its product-level meaning
3. Use the format: "`fieldName` — what this represents in the UI/product"
4. The reading guide is NO-SKIP — it must be present before the spec passes review

Example:
```typescript
interface DealCardViewModel {
  id: string;
  companyName: string;
  fitScore: number | null;
  stage: PipelineStage;
}
```
**Reading Guide:** `id` — internal identifier, never shown. `companyName` — the company name displayed on the card header. `fitScore` — AI-calculated match score shown as the colored badge (null = not yet scored). `stage` — which pipeline column this card appears in.

## Spec-to-Ship v8 — New Agent Contract Rules (2026-04-11)

Ankit-S finalized spec-to-ship v8, adding two new permanent Agent Contract rules drawn from session experience:

- **Rule 17: No completion claims without evidence** — agents cannot report a task as complete without showing proof (test output, screenshot, specific verification). Prevents agents from claiming "done" when partially complete.
- **Rule 18: Bite-sized tasks with complete code** — tasks must be scoped to be implementable with a single focused code block. Prevents partial implementations that leave the codebase in a broken intermediate state.

These join Reading Guides (Rule 16) as NO-SKIP Agent Contract rules in v8. Superpowers skills are also now integrated into specific phases (not standalone — they augment the backbone, not replace it).

## Evidence
- Ankit-S spec-to-ship v7 update, 2026-04-10 (VC-AI-Associate)
- Spec-to-ship playbook v7 created at `docs/workflow/spec-to-ship-playbook-v7.md`
- 3 insertion points added: Agent Contract rule 16, Section 5.5 Reading Guide Rules
- Channel preferences feature was the first test case — Phase 3-4 passed (typecheck 0 errors, lint 0 warnings, storybook built)
- Pipeline stage editor (2026-04-10) was the second test case — spec validated with reading guides, reviewer (Ankit-S) was able to catch "passed" stage ambiguity and terminal vs. active modeling questions because the reading guide made TypeScript interfaces reviewable by non-engineers
- Pipeline stage editor completed full validation: 12-task plan, spec PASS WITH FIXES (3 blocking findings caught and fixed), industry CRM research (Salesforce, Pipedrive) informed terminal stage modeling
- v8 published 2026-04-11, commit e57b16d1 (VC-AI-Assoicate) — 8 versions archived, v8 canonical
- Ankit-S immediately used v8 for multi-fund-hierarchy feature (2026-04-11 traces) — reading guides present, spec validated PASS WITH FIXES (8 non-blocking findings)
- Confidence remains medium: all validation by Ankit-S. Promotion to high requires a second team member independently adopting reading guides in a spec.
