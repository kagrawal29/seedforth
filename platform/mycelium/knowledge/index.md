# Team Knowledge Base

**45 entries** across 5 categories.
When you encounter these situations, search for relevant knowledge below.

## Making architecture or stack decisions?

- [H] [Research-Driven Architecture Decisions](patterns/research-driven-architecture-decisions.md) — Sahiram used a multi-agent research approach to validate architecture decisions: deploy 31 specialized agents to research specific questions (embedding models, graph DB hosting, queue systems), then verify findings via social media (practitioner reports)
- [H] [Architecture Validation via Multi-Agent Research](workflows/architecture-validation-research.md) — Validate architecture decisions by deploying parallel research agents, verifying claims via social media practitioners, then consolidating into a decision table with the human
- [H] [Production Readiness Gap Analysis](architecture/production-readiness-gap.md) — VC-AI-Associate is a feature-complete frontend with zero backend infrastructure
- [H] [MCP Config: Streamable HTTP Transport + Header Auth (SETTLED)](architecture/mcp-streamable-http-auth.md) — The Asgard Graph MCP server connection uses **Streamable HTTP transport** with the auth token passed via `Authorization` header — NOT via URL query parameters and NOT via SSE transport
- [H] [Cypher-Native Pipeline — Intelligence Lives in the Graph (Invariant 6)](architecture/cypher-native-pipeline.md) — The meta-intelligence pipeline is not a Python script
- [H] [Full Tech Stack Decisions — 44 Decisions, 3 Pending](architecture/tech-stack-completed.md) — 44 tech stack decisions are now settled (as of 2026-04-10)
- [H] [Trigger.dev v4 Chosen Over Temporal](architecture/trigger-dev-vs-temporal.md) — Trigger.dev v4 was chosen as the workflow/job queue system after Sahiram's initial decision (Apr 6) and Abhishek's deep comparative evaluation (Apr 7, 3.8M tokens across multiple turns)
- [H] [Memory Layer Architecture Decisions](architecture/memory-layer-decisions.md) — Sahiram finalized the AI memory/retrieval architecture through a massive research session (31 agents, 20M+ tokens)
- [H] [Cross-Channel Continuity Model — Work-Unit + Members (SETTLED)](architecture/cross-channel-continuity-model.md) — The continuity architecture uses a work-unit + scoped-members model, NOT a single-anchor model
- [H] [Agent Harness Decision — Vercel AI SDK + Trigger.dev (SETTLED)](architecture/agent-harness-decision.md) — The AI agent runtime framework is decided: **Vercel AI SDK + Trigger.dev v4 (Option A)**, not Mastra
- [H] [Zep Cloud Production Reliability Issues](anti-patterns/zep-cloud-reliability.md) — Zep Cloud (managed service) has documented production reliability problems: async deadlocks, wrong API endpoints, fake success states
- [M] [Doc-to-Graph LLM Boundary: Parse Structure Deterministically, Use LLM Only for Fuzzy Parts](patterns/doc-to-graph-llm-boundary.md) — Most document-to-graph ingestion does NOT need an LLM

## Building or modifying frontend?

- [H] [Design System Enforcement Prevents Drift](patterns/design-system-enforcement-prevents-drift.md) — VC-AI-Associate implemented a 6-phase design system rollout that moved from manual token usage to automated CI enforcement
- [H] [Claude Code Agent as Primary Builder](patterns/claude-code-agent-as-primary-builder.md) — A Claude Code agent (NBTEAM-25) built 92.5% of the VC-AI-Associate codebase over 142 days
- [H] [LLM Cost Optimization for Multi-Agent Pipelines](tool-configs/cost-optimization-patterns.md) — Replace single long-running ReAct loops with multi-call pipelines that start fresh context per sub-task
- [H] [Production Readiness Gap Analysis](architecture/production-readiness-gap.md) — VC-AI-Associate is a feature-complete frontend with zero backend infrastructure
- [H] [Fixture-First Development](architecture/fixture-first-development.md) — The entire VC-AI-Associate frontend (902 commits, 1,069+ TSX files, full Storybook coverage) was built using fixture data — no real backend, no database, no live API calls
- [H] [FSD Architecture Audit — Critical Issues](architecture/fsd-audit-critical-issues.md) — The VC-AI-Associate codebase (225K LOC, Next.js/TypeScript with Feature-Sliced Design) has 4 critical architectural issues found in Phase 1 audit
- [H] [Agent Harness Decision — Vercel AI SDK + Trigger.dev (SETTLED)](architecture/agent-harness-decision.md) — The AI agent runtime framework is decided: **Vercel AI SDK + Trigger.dev v4 (Option A)**, not Mastra

## Doing data collection or research?

- [H] [Rapid API Pivot on Failure](patterns/rapid-api-pivot-on-failure.md) — Structured process for detecting API failures and switching to alternatives within hours, not days
- [H] [Research-Driven Architecture Decisions](patterns/research-driven-architecture-decisions.md) — Sahiram used a multi-agent research approach to validate architecture decisions: deploy 31 specialized agents to research specific questions (embedding models, graph DB hosting, queue systems), then verify findings via social media (practitioner reports)
- [H] [Issue-Driven Research Tracking](patterns/issue-driven-research-tracking.md) — maverick-market-research used GitHub Issues as a research task ledger
- [H] [Competitor Marketing Research Dataset — 28 Brands Completed](patterns/competitor-research-dataset.md) — Full competitor marketing research sprint completed April 7, 2026
- [H] [Claude Code Hooks for Automatic Data Capture](tool-configs/claude-code-hooks-for-data-capture.md) — PostToolUse hook that auto-saves all MCP tool responses to disk, creating a complete audit trail before any LLM processing
- [H] [Research Tools Catalog](tool-configs/research-tools-catalog.md) — Available tools for research beyond web search, validated from real production use across the maverick market research effort
- [H] [Parallel Workstream Research](workflows/parallel-workstream-research.md) — Run multi-person research by splitting data collection and analysis into parallel workstreams, each tracked independently via GitHub Issues
- [H] [Architecture Validation via Multi-Agent Research](workflows/architecture-validation-research.md) — Validate architecture decisions by deploying parallel research agents, verifying claims via social media practitioners, then consolidating into a decision table with the human
- [H] [Production Readiness Gap Analysis](architecture/production-readiness-gap.md) — VC-AI-Associate is a feature-complete frontend with zero backend infrastructure
- [H] [Research-to-Product Pipeline](architecture/research-to-product-pipeline.md) — Market research findings from maverick-market-research map directly to product architecture decisions in VC-AI-Assoicate
- [H] [Keyword Search on Social Platforms = Noise](anti-patterns/keyword-search-noise.md) — Early data collection used keyword search (Xpoz for Twitter, sort=relevance for Reddit) as the primary method

## Setting up tools or dev environment?

- [H] [Rules-Loaded Telemetry Hook](tool-configs/rules-loaded-telemetry.md) — SessionStart hook that posts a manifest of loaded `.claude/rules/`, `.claude/knowledge/`, `.claude/skills/`, and `.claude/hooks/` to LangSmith as a custom `rules-loaded` run
- [H] [Claude Code Hooks for Automatic Data Capture](tool-configs/claude-code-hooks-for-data-capture.md) — PostToolUse hook that auto-saves all MCP tool responses to disk, creating a complete audit trail before any LLM processing
- [H] [Auto-Sync Hooks for Invisible Git Push/Pull](tool-configs/auto-sync-hooks.md) — Two complementary hooks that keep branches synced without manual intervention:
1
- [H] [Research Tools Catalog](tool-configs/research-tools-catalog.md) — Available tools for research beyond web search, validated from real production use across the maverick market research effort
- [H] [LangSmith Tracing for Claude Code](tool-configs/langsmith-tracing-setup.md) — Full telemetry for every Claude Code session -- messages, tool calls, compaction events, subagent runs
- [H] [MCP Config: Streamable HTTP Transport + Header Auth (SETTLED)](architecture/mcp-streamable-http-auth.md) — The Asgard Graph MCP server connection uses **Streamable HTTP transport** with the auth token passed via `Authorization` header — NOT via URL query parameters and NOT via SSE transport

## Planning work or organizing tasks?

- [H] [Issue-Driven Research Tracking](patterns/issue-driven-research-tracking.md) — maverick-market-research used GitHub Issues as a research task ledger
- [H] [Parallel Workstream Research](workflows/parallel-workstream-research.md) — Run multi-person research by splitting data collection and analysis into parallel workstreams, each tracked independently via GitHub Issues

## Other knowledge

- [H] [Spec vs Plan Separation: "No Tech in Specs" Is Not Universal](patterns/spec-tech-separation.md) — "No technical detail in specs" applies specifically to **Software Requirements Specifications (SRS)** — one document type used in formal regulated engineering
- [H] [Vibe-Coding Threat Assessment — Real But Bounded for Maverick](patterns/vibe-coding-threat-assessment.md) — The "vibe-coding" trend (building custom SaaS replacements with LLM-assisted coding) is a genuine threat to SaaS products but is bounded by technical complexity
- [H] [Spec-to-Ship v8: Superpowers as Execution Helpers, Not Workflow Replacements](patterns/spec-to-ship-v8-superpowers.md) — Spec-to-ship playbook v8 adds **2 new Agent Contract rules** and integrates superpowers skills as **execution helpers inside phases** — not as alternatives to the workflow
- [H] [VC AI Market Ground Truth — What VCs Actually Do With AI](patterns/vc-ai-market-ground-truth.md) — Empirical data on how VCs actually use AI in 2026
- [H] [Rule Builder Group Logic: Within-Group = OR, Across-Groups = AND](patterns/rule-builder-group-logic.md) — In Maverick's rule/automation builder, conditions within a single group use OR logic
- [H] [Expert Panel Validation Before Finalizing Tech Decisions](patterns/expert-panel-validation.md) — Before locking a major technology decision, convene a "panel" of 4 specialist agents who each argue from their domain expertise
- [H] [Spec Isolation Principle — 10 Specs Co-Exist Without Cross-Contaminating](patterns/spec-isolation-principle.md) — Each spec is **one independently buildable feature slice**
- [H] [Emerging Manager / Solo GP Segment — Deep Analysis](patterns/emerging-manager-solo-gp-segment.md) — Emerging managers (Fund I-III, <$100M AUM) and solo GPs represent Maverick's highest-urgency target segment
- [H] [LP Reporting Pain Profile — The #1 VC Operations Problem](patterns/lp-reporting-pain-profile.md) — LP quarterly reporting is the single highest-pain operational task in venture capital
- [H] [PostgREST Client & API Type Safety — postgrest-js Chosen (SETTLED)](architecture/postgrest-client-type-safety.md) — The API client strategy is decided: **postgrest-js** (`@supabase/postgrest-js`) for PostgREST endpoints (90% of API surface), **hono/client** for Hono custom endpoints (10%)
- [H] [Phase 1 Architecture Decisions (Settled)](architecture/phase1-decisions-settled.md) — 22 explicit decisions made during Phase 1 audit of VC-AI-Assoicate
- [H] [Security Stack Decisions — Secrets + Scanning (SETTLED)](architecture/security-scanning-stack.md) — Two security decisions locked in Abhishek's session on 2026-04-09 after expert panel review (4 specialists: AppSec, DevSecOps, Cloud Security, Backend)
- [H] ["Configurable Per Fund" as Core Architectural Pattern](architecture/configurable-per-fund-pattern.md) — Four independent decisions (pipeline stages, deal metrics, round types, scoring dimensions) all resolved to the same answer: configurable per fund
- [M] [Graph-Native Identity — Files Are Bootstrap Pointers, Graph Is the System](patterns/graph-native-identity.md) — The system's identity (who it is), operating rules (invariants), tests (TestCase nodes), and development plan (WorkItem nodes) live in the graph — not in files
- [M] [Reading Guides for Technical Specs](patterns/spec-reading-guides.md) — Every technical block in a spec (TypeScript interfaces, enums, type definitions, code snippets) should include an inline "Reading Guide" — a plain-language explanation that maps each technical element back to the product concept it represents
- [L] [⚡ Active: Email View Redesign](workflows/active-email-redesign.md) — 
- [L] [Active Exploration: API Gateway / Management Layer (Zuplo)](architecture/api-gateway-exploration.md) — Abhishek is evaluating Zuplo as an API management layer for Maverick's customer-facing API

---
*Search with `/team-knowledge <query>` for keyword search across all entries.*
