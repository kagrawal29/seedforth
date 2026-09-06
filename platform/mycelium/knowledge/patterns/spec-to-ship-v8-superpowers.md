---
id: patterns-spec-to-ship-v8-superpowers
category: patterns
type: knowledge
discovered: 2026-04-11
last-validated: 2026-04-11
confidence: high
source: Ankit-S LangSmith traces 2026-04-10 (14:03–14:21, commits e57b16d1); spec-to-ship-playbook-v8.md in VC-AI-Assoicate
tags: [spec-to-ship, playbook, superpowers, skills, v8, agent-contract, code-review, execution]
relevant-when: using spec-to-ship playbook, deciding how superpowers skills relate to workflow phases, reviewing agent behavior rules
related: [patterns-spec-reading-guides, pattern-claude-code-agent-as-primary-builder]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Spec-to-Ship v8: Superpowers as Execution Helpers, Not Workflow Replacements

## What
Spec-to-ship playbook v8 adds **2 new Agent Contract rules** and integrates superpowers skills as **execution helpers inside phases** — not as alternatives to the workflow. The v7 backbone is unchanged.

## The 2 New Agent Contract Rules

| Rule | Constraint |
|------|-----------|
| **Rule 17** | No completion claims without evidence — agent must show proof before saying "done" |
| **Rule 18** | Bite-sized tasks with complete code — no partial implementations, no plans-as-deliverables |

## Superpowers Integration Pattern
Superpowers skills sit **inside** spec-to-ship phases as invocable execution helpers:

- `superpowers:using-superpowers` — loaded at session start, tells Claude to invoke skills when 1%+ relevant
- `superpowers:requesting-code-review` + `superpowers:code-reviewer` — dispatched AFTER implementation is complete, fresh-context reviewer agent gets the git diff range

**Key distinction**: Superpowers enhance execution inside phases. They do NOT replace:
- Phase 1 research tasks (9 specific research tracks)
- The 16-topic Frontend Readiness Checklist (gate before writing)
- Phase 1.5 spec validation (14-item checklist)
- Human touchpoints (Phase 2 spec sign-off, Phase 5 final review)

## Why Skills Are Not Phase Replacements
Phase 1 research requires interactive human Q&A and spec writing that is "inherently interactive" — no skill can replace it. Phase 4 build is where parallelism helps, but the playbook already describes it clearly enough that a skill would add surface area without value.

Skills that DO justify invocation: code reviewer (dispatched once at end), using-superpowers (meta-skill for skill selection). Everything else is absorbed into the playbook as rules.

## How to Apply
1. v8 playbook is at `docs/workflow/spec-to-ship-playbook-v8.md`
2. v1-v7 archived at `docs/workflow/spec-to-ship-archive/`
3. Always invoke `superpowers:requesting-code-review` after implementation, before Phase 5 handoff
4. Rule 17 + 18 apply to every agent working inside the playbook
