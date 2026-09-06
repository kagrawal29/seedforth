---
id: architecture-fixture-first-development
category: architecture
discovered: 2026-04-06
last-validated: 2026-04-06
confidence: high
type: knowledge
source: VC-AI-Assoicate — entire 902-commit frontend built on fixture data, no real backend
distributed-to: [VC-AI-Assoicate#5]
effectiveness: null
tags: [fixtures, frontend, mock-data, service-provider, next-js, react, storybook, backend-swap]
relevant-when: connecting frontend to real backend, understanding current data flow, replacing fixtures with API calls
related: [architecture-production-readiness-gap, pattern-claude-code-agent-as-primary-builder, exploration-email-redesign, patterns-spec-reading-guides]
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Fixture-First Development

## What
The entire VC-AI-Associate frontend (902 commits, 1,069+ TSX files, full Storybook coverage) was built using fixture data — no real backend, no database, no live API calls. Mock agent runners simulate AI streams with scripted responses.

## Why
- Decouples frontend velocity from backend availability
- Storybook stories are deterministic (no flaky tests from network)
- Every UI state is explicitly modeled (loading, error, empty, populated)
- Fixtures serve as living documentation of the data contract
- Allows 142-day frontend sprint without waiting for backend team

## How to Apply
1. Define fixture factories in `shared/fixtures/` — typed, composable
2. Create scenario files for complex multi-entity states (deal workspace, email workspace)
3. Mock service layer via dependency injection (DealRepo, AgentRunner, etc.)
4. Storybook DoD requires: Default, Loading, Empty, Error, Mobile, Dark, InteractionHappyPath
5. Use fixture data as the implicit API contract — when backend arrives, match the fixture shape

## Evidence
- Zero real API calls in entire codebase
- CopilotKit integration uses mock agent runner with scripted token streams
- Service provider pattern (React Context) enables easy swap from fixture to real
- All 14 widgets have fixture-backed stories with full DoD profiles

## Risk
This is also the biggest production gap. The transition from fixtures to real backend is the critical path item for production readiness. Database schema, auth, real AI inference — none exist yet.
