---
id: pattern-claude-code-agent-as-primary-builder
category: patterns
discovered: 2026-04-06
last-validated: 2026-04-06
confidence: high
type: knowledge
source: VC-AI-Assoicate commit history — NBTEAM-25 authored 834/902 commits (92.5%)
distributed-to: []
effectiveness: neutral
metrics:
  surfaced_count: 5
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.00
  last_scored: 2026-04-09
tags: [claude-code, agent, automation, eslint, quality-gates, pre-commit, ci, velocity, architect-role]
relevant-when: setting up a new project for agent-driven development, defining human vs agent roles, establishing quality gates
related: [pattern-design-system-enforcement, architecture-fixture-first-development, patterns-rule-builder-group-logic]
---

# Claude Code Agent as Primary Builder

## What
A Claude Code agent (NBTEAM-25) built 92.5% of the VC-AI-Associate codebase over 142 days. A senior engineer (Sahil Agrawal) made 12 strategic commits — ESLint rules, design system enforcement, barrel exports, legacy cleanup. The agent handled daily implementation; the human handled architectural guardrails.

## Why
This works because:
- The human sets constraints (ESLint rules, FSD boundaries, design tokens) that the agent cannot violate
- The agent executes within those constraints at high velocity (up to 19 commits/day on peak days)
- Quality is enforced by automation (pre-commit hooks, CI), not by human code review
- The human intervenes only for architectural pivots, not line-level reviews

## How to Apply
1. Establish automated quality gates BEFORE letting the agent build (ESLint, type checking, Storybook DoD)
2. Human architects set constraints via config files and rules, not by reviewing every PR
3. Let the agent own daily implementation velocity
4. Human reviews at milestone boundaries (end of phase, before major feature)
5. Document-driven development: PRDs and specs BEFORE agent builds

## Evidence
- 834/902 commits by NBTEAM-25 over 142 days
- Only 1 DnD refactor needed (Dec 19) — minimal rework for 902 commits
- 5-layer quality defense prevented architecture drift without human review overhead
- Sahil's 12 commits were all high-leverage: rules, enforcement, cleanup
