---
id: architecture-phase1-decisions-settled
category: architecture
type: knowledge
discovered: 2026-04-07
last-validated: 2026-04-10
confidence: high
source: docs/phase-1/DECISIONS.md in VC-AI-Assoicate (commit 041ba65b, Codex CLI, 2026-04-06T16:55)
tags: [phase-1, decisions, data-model, DealResearchDoc, memo, contact, DD, scoring, MVP-scope, call-detail, co-investors, notifications, knock, papermark, svix, data-rooms, webhooks, multi-channel]
relevant-when: "building any of these features: documents, deals, contacts, DD checklist, scoring, call detail views, co-investor tracking, notifications, data rooms, webhooks"
related: [architecture-configurable-per-fund-pattern, architecture-fixture-first-development, patterns-rule-builder-group-logic, architecture-agent-harness-decision, architecture-tech-stack-completed]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 4
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
  last_scored: 2026-04-12
---

# Phase 1 Architecture Decisions (Settled)

## What
22 explicit decisions made during Phase 1 audit of VC-AI-Assoicate. These are locked — do not re-debate them.

## Settled Decisions

| Area | Decision |
|------|----------|
| **Documents** | Merge Memo + DealResearchDoc into single system. Add `quick-note` type alongside `memo`, `competitor`, `market`. Delete `memos.ts` |
| **Call detail** | List view = summary (title, date, participants). Detail view = full (transcript, metrics, risks, tasks) |
| **Deal-contact** | `deal_contacts` join table with role, isPrimary, addedAt. Use existing `DealContactAssociation` type |
| **Pass/decline** | Structured `PassDecision` — reason category + free text + stage-at-pass + reviewer. Enables fund learning loop |
| **DD** | DD checklist entity — `DDChecklist` type with areas, items, status, assignee, notes, reference calls |
| **ThesisConfig** | Merge two ThesisConfig types into one with structured fields AND free-text overview |
| **User settings** | Split `UserSettingsRepo` into two: `UserSettingsRepo` (profile/prefs/notifications) + `FundSettingsRepo` (fund/team/meeting defaults) |
| **MCP server** | Ship at MVP (Sprint 3-4). 7 read-only tools. `ai.ask` tool is the killer feature |
| **Co-investors** | Add `coInvestors` to Deal: name, firm, isLead, status (confirmed/verbal/interested/passed) |
| **Email** | Both passive background capture AND full email tab for deal-specific threads |
| **MVP scope** | 16 essential features, 13 important, 7 nice-to-have, 3 deferred (role-permissions, team-management, user-menu) |
| **Currency** | ISO 4217 string. UI dropdown for common ones |
| **Fixture timing** | Update all fixtures to 2026 date before demos (~2 hours, 85+ files) |
| **Fixture stages** | Stage-aware factories: Pre-Seed caps at $20K MRR/$10M val; Seed at $100K/$25M; Series A at $500K/$100M |
| **Stage transitions** | Soft enforcement with override — warn on stage skip, partners can override |

## Batch 2 Decisions (April 9-10, 2026 — Abhishek + Ankit-S sessions)

| Area | Decision |
|------|----------|
| **Notifications** | Build direct with domain events + Trigger.dev dispatchers + Resend (email) + @slack/bolt (Slack). Knock eliminated — unnecessary abstraction when the dispatch infrastructure already exists. |
| **Data rooms** | Papermark (self-hosted, MIT license). Runs as separate Next.js app. Cloud pricing starts at ~EUR24/mo but self-hosted = $0. |
| **Outbound webhooks** | Svix (self-hosted, MIT). Embeddable customer portal + event management. |
| **i18n** | Deferred to post-launch. English-only Phase 1. Decide when a non-English design partner signs. Next.js has built-in i18n when needed. |
| **Data retention / offboarding** | Deferred to post-launch. Three scenarios identified (fund offboarding, user offboarding, data retention policy) but implementation deferred until tool is live. |
| **Multi-channel routing** | Per-channel preferences in settings (Slack, WhatsApp, email, in-app). Per-channel quiet hours. All users configure their own. |
| **AI runtime** | Vercel AI SDK + Trigger.dev — see `architecture-agent-harness-decision` entry for full evaluation |

## Still Deferred
- Real-time streaming strategy (SSE vs WebSocket)
- Pagination strategy

## Evidence
- `docs/phase-1/DECISIONS.md` (VC-AI-Assoicate, commit 041ba65b)
- Decision session: Sahil Agrawal + Claude Code, 30 questions from QUESTIONS.md answered interactively
- Batch 2: Abhishek LangSmith traces 2026-04-09/10 (63 turns, 35M tokens) — architecture decisions doc session
- Batch 2: Ankit-S LangSmith traces 2026-04-10 (100 turns, 75M tokens) — multi-channel notification feature build
