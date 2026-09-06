---
id: architecture-fsd-audit-critical-issues
category: architecture
type: knowledge
discovered: 2026-04-07
last-validated: 2026-04-07
confidence: high
source: docs/phase-1/audit/ARCHITECTURE-AUDIT.md in VC-AI-Assoicate (commit 041ba65b, Codex CLI, 2026-04-06T16:55)
tags: [FSD, feature-sliced-design, architecture-audit, shared, widgets, circular-dependency, DealResearchRepo, eslint, state-management, god-components]
relevant-when: working on any FSD layer, adding shared imports, wiring new services, building large components
related: [architecture-configurable-per-fund-pattern, architecture-fixture-first-development]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# FSD Architecture Audit — Critical Issues

## What
The VC-AI-Associate codebase (225K LOC, Next.js/TypeScript with Feature-Sliced Design) has 4 critical architectural issues found in Phase 1 audit. Ankit-S is actively working through these via fix-playbook.md.

## Critical Issues (Priority Order)

### 1. FSD Layer Inversion — shared/ imports from widgets/
`shared/` imports `ChatMessage` types from `widgets/ai-chat` in 6+ production files. This violates FSD's core principle — shared must never depend on higher layers.

**Files affected:**
- `shared/providers/conversation-history-provider.tsx`
- `shared/hooks/use-conversation-history.ts`
- `shared/types/conversation-history.ts`
- `shared/ui/molecules/ChatMessageBubble.tsx`
- `shared/ui/molecules/MessageList.tsx`
- `shared/lib/workflow-utils.ts`

**Fix:** Extract `ChatMessage` type to `shared/types/` or `entities/`. Phase 2 decision (Q17) confirms this is scheduled.

### 2. DealResearchRepo Not Wired
`DealResearchRepo` interface is fully defined with 7 methods and has a mock, but is NOT wired into `ServicesProvider`. This means deal-research features cannot access the repository via the DI pattern.

**Fix:** Add to `Services` type + `services-provider.tsx` + `services/index.ts` + `app-services.ts` + add `useDealResearchRepo()` hook.

### 3. ESLint Boundary Coverage — 25% Only
Only 9 of 14 widgets, 3 of 40 features, 2 of 9 entities have individual boundary rules. The remaining 37 features fall through to permissive fallback rules that allow cross-slice imports without any ESLint error.

**Fix:** Add per-slice ESLint rules for all 37 missing features and 7 missing entities.

### 4. God Components (Files >500 LOC)
15 production files exceed 500 LOC. Top critical:
- `ThenSection.tsx` — 1,233 LOC (workflow action types, needs registry pattern)
- `AIChatPanel.tsx` — 1,146 LOC (needs extracted hooks + sub-components)
- `DealResearchEditor.tsx` — 854 LOC
- `ICPacketTab.tsx` — 809 LOC

**Also critical:** `DealWorkspace.tsx` (567 LOC) imports fixture data in production code — shipping test data to production bundles.

## State Management Note
No Zustand or external state management — all state in React Context + useState. This is clean for now but will not scale to cross-widget coordination. Flag for Phase 2.

## Missing Service Interfaces
Domains needing service interfaces (currently use fixtures directly): EmailRepo, ContactRepo, MeetingRepo, WorkflowRepo, ScheduledTaskRepo, NotificationRepo.

## Evidence
- `docs/phase-1/audit/ARCHITECTURE-AUDIT.md` (VC-AI-Assoicate, commit 041ba65b)
- Ankit-S is actively working through these: LangSmith traces 2026-04-07 show 1.58M token session on ARCHITECTURE-AUDIT.md + fix-playbook.md
