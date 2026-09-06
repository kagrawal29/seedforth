---
id: patterns-spec-tech-separation
category: patterns
type: knowledge
discovered: 2026-04-11
last-validated: 2026-04-11
confidence: high
source: Sahiram LangSmith traces 2026-04-11 (turns 2, 5, 8-10) + 2026-04-10 (turns 8-10); research validated against spec-kit, IEEE 29148, Karl Wiegers "Software Requirements", SWEBOK, ISO 25010; two independent sessions confirm same conclusion
tags: [spec-to-ship, specs, technical-detail, srs, requirements, plan, what-vs-how, spec-kit]
relevant-when: writing specs, deciding whether to include TypeScript types or schema definitions in a spec, reviewing spec-to-ship playbook, resolving disagreements about spec format
related: [patterns-spec-reading-guides, architecture-fixture-first-development]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Spec vs Plan Separation: "No Tech in Specs" Is Not Universal

## What
"No technical detail in specs" applies specifically to **Software Requirements Specifications (SRS)** — one document type used in formal regulated engineering. It is **not** a universal software development rule. For product specs in the spec-to-ship workflow, controlled technical detail belongs where it aids clarity.

## Why — The Evidence

Sahiram researched this directly against primary sources (Wiegers, IEEE 29148, spec-kit):

**spec-kit's answer** (the closest external reference to our workflow):
| | Spec (spec.md) | Plan (plan.md) |
|---|---|---|
| Focus | WHAT users need and WHY | HOW to build it |
| Content | User stories, acceptance criteria | TypeScript types, file structure, migrations |
| Technical detail | ❌ No | ✅ Yes |

**The principle**: Tech detail in plan is fine. Tech detail replacing user requirements in a spec is the problem. Our Reading Guides (inline plain-language explanations of TypeScript blocks) solve this — they make technical content human-readable without removing it.

## How to Apply

1. **Spec (spec.md)**: User stories, acceptance criteria, plain-language data contracts. TypeScript interfaces are allowed IF they are accompanied by Reading Guides (see `patterns-spec-reading-guides`).
2. **Plan (plan.md)**: All implementation detail — file structure, migrations, database schemas, API contracts, TypeScript types.
3. **"No tech in specs" teammates**: Direct them to spec-kit and IEEE 29148. The rule they're citing applies to SRS documents specifically, not to product feature specs.
4. **Data contracts in specs**: Use plain language first. TypeScript types may follow if they have Reading Guides.

## Cross-Person Note
This was an active debate between Sahiram and a teammate. Sahiram was correct. The research confirmed it. Reference this entry when the debate surfaces with other team members.
