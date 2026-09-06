---
id: pattern-spec-isolation-principle
category: patterns
type: knowledge
discovered: 2026-04-11
last-validated: 2026-04-11
confidence: high
source: Abhishek LangSmith trace 2026-04-10T15:42 — spec dependency/overlap question; Ankit-S LangSmith traces 2026-04-11 — multi-fund-hierarchy spec built against v8 playbook (independent validation)
tags: [spec-to-ship, specs, isolation, dependency-management, spec-design, cross-spec, feature-slicing]
relevant-when: writing specs when 5+ feature specs exist, managing spec library for a product, reviewing specs for cross-contamination, spec-to-ship phase 1
related: [patterns-spec-reading-guides, pattern-claude-code-agent-as-primary-builder]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Spec Isolation Principle — 10 Specs Co-Exist Without Cross-Contaminating

## What
Each spec is **one independently buildable feature slice**. It doesn't know about, reference, or depend on other specs. Cross-spec coordination happens through shared types and the Out of Scope section — not through spec-to-spec references.

This answers the demand: "When 10 specs exist for a single product, how do they reference shared concepts without cross-contaminating or overwriting each other?"

## Why
The spec is the implementation contract between the human who specifies and the agent who builds. If a spec references another spec ("see spec #7 for the data model"), the agent must load both contexts — which breaks the "independently buildable" guarantee, creates implicit coupling, and makes the spec impossible to implement in isolation during spec-to-ship phase 3.

## How Isolation Works in Practice

### Each spec knows only two things:
1. **What it builds** (its own sections — user stories, data model, API contract, UI spec)
2. **What it does NOT build** (explicit Out of Scope section)

### The Out of Scope section is the coordination mechanism
If feature A is built in spec-1, spec-2's Out of Scope section says:
> "Fund switching context — handled by the FundContext provider implemented in spec-1. This spec assumes that context exists."

The spec doesn't import spec-1. It declares a dependency and trusts the shared type system to provide it.

### Shared types live in a single source of truth
Common concepts (Fund, Organization, Deal) belong in `shared/types/` — not in any individual spec. Specs reference shared types by name; they don't define them. This prevents two specs from defining conflicting Fund interfaces.

### Sequence matters, but specs don't enforce it
If spec-2 assumes spec-1's output exists, the project plan (not the spec) enforces that spec-1 ships first. The spec itself stays clean.

## Warning Signs of Cross-Contamination
- A spec's Data Model section redefines a type already defined in a previous spec
- A spec references another spec by number or name in its implementation sections
- Two specs have overlapping user stories (both claim to build fund switching)
- A spec's API section duplicates endpoints already established by a prior spec

## How to Apply
1. Start every spec by auditing existing shared types — don't redefine them
2. Write Out of Scope before writing the spec body — forces you to think about boundaries first
3. If a concept is referenced in 2+ specs, extract it to `shared/types/` before writing the second spec
4. Review against prior specs for user story overlap before finalizing
