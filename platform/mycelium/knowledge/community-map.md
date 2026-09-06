# Community Map — Asgard Knowledge Graph

105 nodes across 10 communities. Use this to find related knowledge when working in a domain.

## How to Use
1. Identify which community matches the user's topic
2. Read the nodes in that community for full context
3. Check 'Open Questions' for unresolved items in the same area

## Memory, Continuity & Workflow Orchestration (23 nodes)

- [Trigger.dev v4](knowledge/architecture/trigger-dev-vs-temporal.md)
- [Temporal (Workflow Orchestration)](knowledge/architecture/trigger-dev-vs-temporal.md)
- [Trigger.dev v4 Chosen Over Temporal — Architecture Decision](knowledge/architecture/trigger-dev-vs-temporal.md)
- [Rationale: No Worker Management Needed (Trigger.dev v4)](knowledge/architecture/trigger-dev-vs-temporal.md)
- [Rationale: Trigger.dev v3 Shutdown Forced Migration](knowledge/architecture/trigger-dev-vs-temporal.md)
- [Cross-Channel Continuity — Work-Unit + Members Model](knowledge/architecture/cross-channel-continuity-model.md)
- [continuity_contexts Table Schema](knowledge/architecture/cross-channel-continuity-model.md)
- [continuity_context_members Table](knowledge/architecture/cross-channel-continuity-model.md)
- [Rationale: Work-Unit + Members Beats Single-Anchor for VC Workflows](knowledge/architecture/cross-channel-continuity-model.md)
- [Graphiti OSS (Self-Hosted Knowledge Graph Engine)](knowledge/architecture/memory-layer-decisions.md)
- [FalkorDB (Graph Database)](knowledge/architecture/memory-layer-decisions.md)
- [pgvector (Semantic Search)](knowledge/architecture/memory-layer-decisions.md)
- [Row-Level Security on fund_id (Tenant Isolation)](knowledge/architecture/memory-layer-decisions.md)
- [Memory Layer Architecture Decisions](knowledge/architecture/memory-layer-decisions.md)
- [Rationale: Zep Cloud Rejected — Async Deadlocks and Fake Success States](knowledge/architecture/memory-layer-decisions.md)
- [Rationale: FalkorDB Over Neo4j — 7x Less Memory, 500x Faster P99](knowledge/architecture/memory-layer-decisions.md)
- [LLM Cost Optimization — Multi-Agent Pipeline Splitting](knowledge/tool-configs/cost-optimization-patterns.md)
- [Rationale: Fresh Context Per Sub-Task Cuts Token Replay Cost 3x](knowledge/tool-configs/cost-optimization-patterns.md)
- [Agent Harness Decision: Vercel AI SDK + Trigger.dev](knowledge/architecture/agent-harness-decisions.md)
- [Vercel AI SDK (Agent Orchestration)](knowledge/architecture/agent-harness-decisions.md)
- [LangGraph (Rejected — Python-first, heavy abstraction)](knowledge/architecture/agent-harness-decisions.md)
- [CrewAI / AutoGen (Rejected — too opinionated)](knowledge/architecture/agent-harness-decisions.md)
- [Rationale: TypeScript-native, built-in streaming, lightweight vs LangGraph](knowledge/architecture/agent-harness-decisions.md)

## Product Architecture & Fund Configuration (18 nodes)

- [Cycle Log — Ingest/Synthesize/Distribute Results Ledger](knowledge/meta/cycle-log.md)
- [Configurable Per Fund — Core Architectural Pattern](knowledge/architecture/configurable-per-fund-pattern.md)
- [JSONB Columns for Extensible Fund Configuration](knowledge/architecture/configurable-per-fund-pattern.md)
- [Rationale: Maverick Learns YOUR Fund — Multi-Tenant Flexibility](knowledge/architecture/configurable-per-fund-pattern.md)
- [Phase 1 Architecture Decisions (Settled — 22 Decisions)](knowledge/architecture/phase1-decisions-settled.md)
- [MCP Server — Ship at MVP Sprint 3-4 with 7 Read-Only Tools](knowledge/architecture/phase1-decisions-settled.md)
- [PassDecision — Structured Pass/Decline with Fund Learning Loop](knowledge/architecture/phase1-decisions-settled.md)
- [Research-to-Product Pipeline](knowledge/architecture/research-to-product-pipeline.md)
- [Maverick Positioning Bridge v2](knowledge/architecture/research-to-product-pipeline.md)
- [FSD Architecture Audit — Critical Issues](knowledge/architecture/fsd-audit-critical-issues.md)
- [FSD Layer Inversion — shared/ Imports from widgets/](knowledge/architecture/fsd-audit-critical-issues.md)
- [DealResearchRepo Not Wired into ServicesProvider](knowledge/architecture/fsd-audit-critical-issues.md)
- [God Components — 15 Files Exceeding 500 LOC](knowledge/architecture/fsd-audit-critical-issues.md)
- [Production Readiness Gap Analysis](knowledge/architecture/production-readiness-gap.md)
- [Fixtures as Current Database — Zero Real API Calls](knowledge/architecture/production-readiness-gap.md)
- [Fixture-First Development Pattern](knowledge/architecture/fixture-first-development.md)
- [Service Provider Pattern (React Context DI for Fixture Swap)](knowledge/architecture/fixture-first-development.md)
- [Rationale: Fixture-First Decouples Frontend Velocity from Backend Availability](knowledge/architecture/fixture-first-development.md)

## Security Stack & Infrastructure (15 nodes)

- [Infisical (Secrets Management, Self-Hosted)](knowledge/architecture/security-scanning-stack.md)
- [Semgrep Community Edition (SAST)](knowledge/architecture/security-scanning-stack.md)
- [Trivy (Dependency CVE Scanning)](knowledge/architecture/security-scanning-stack.md)
- [Coraza + OWASP Core Rules (WAF)](knowledge/architecture/security-scanning-stack.md)
- [OWASP ZAP (DAST, Deferred)](knowledge/architecture/security-scanning-stack.md)
- [Security Stack Decisions — Secrets + Scanning](knowledge/architecture/security-scanning-stack.md)
- [Rationale: OSS + Self-Hosted — On-Prem Enterprise Constraint](knowledge/architecture/security-scanning-stack.md)
- [Full Tech Stack — All 16 Services Settled](knowledge/architecture/tech-stack-completed.md)
- [Docker + Coolify (Deployment)](knowledge/architecture/tech-stack-completed.md)
- [Keycloak (Auth, Self-Hosted)](knowledge/architecture/tech-stack-completed.md)
- [PostgREST (Auto-Generated CRUD API)](knowledge/architecture/tech-stack-completed.md)
- [Drizzle ORM + drizzle-zod](knowledge/architecture/tech-stack-completed.md)
- [Nango Self-Hosted (OAuth Integrations, 250+ Connectors)](knowledge/architecture/tech-stack-completed.md)
- [Rationale: On-Premises Enterprise Deployment Constraint Drives OSS Stack](knowledge/architecture/tech-stack-completed.md)
- [Rationale: PostgREST Replaces tRPC — Universal REST for All Consumers](knowledge/architecture/tech-stack-completed.md)

## Meta Intelligence System (this system) (13 nodes)

- [System Effectiveness Tracking](knowledge/meta/system-effectiveness.md)
- [Smart Context Hook Injection System](knowledge/meta/system-effectiveness.md)
- [Heimdall Evaluation Gate](knowledge/meta/system-effectiveness.md)
- [Research Tools Catalog (Xpoz, TwitterAPI, YouTube, LinkedIn, SearXNG)](knowledge/tool-configs/research-tools-catalog.md)
- [Xpoz MCP — Social Media Research Tool](knowledge/tool-configs/research-tools-catalog.md)
- [TwitterAPI.io — Keyword Search Tool](knowledge/tool-configs/research-tools-catalog.md)
- [Rules-Loaded Telemetry Hook (SessionStart)](knowledge/tool-configs/rules-loaded-telemetry.md)
- [Rationale: Telemetry Hook Closes Distribution Verification Gap](knowledge/tool-configs/rules-loaded-telemetry.md)
- [LangSmith Tracing for Claude Code (Setup Procedure)](knowledge/tool-configs/langsmith-tracing-setup.md)
- [Auto-Sync Hooks — Invisible Git Push/Pull After Commit](knowledge/tool-configs/auto-sync-hooks.md)
- [Rationale: Auto-Sync Reduces Push Friction and Keeps Work Visible](knowledge/tool-configs/auto-sync-hooks.md)
- [Claude Code Hooks for Automatic Data Capture (PostToolUse)](knowledge/tool-configs/claude-code-hooks-for-data-capture.md)
- [Rationale: Decouple Data Collection from Analysis, Prevent Data Loss](knowledge/tool-configs/claude-code-hooks-for-data-capture.md)

## Knowledge Management & Research Patterns (9 nodes)

- [Search Index](knowledge/search-index.md)
- [Team Knowledge Base Index](knowledge/index.md)
- [Rapid API Pivot on Failure](knowledge/patterns/rapid-api-pivot-on-failure.md)
- [Keyword Search on Social Platforms = Noise](knowledge/anti-patterns/keyword-search-noise.md)
- [Active: Email View Redesign](knowledge/workflows/active-email-redesign.md)
- [Parallel Workstream Research](knowledge/workflows/parallel-workstream-research.md)
- [Knowledge Base Lint Report](knowledge/meta/lint-report.md)
- [Practitioner Account-Based Data Collection](knowledge/anti-patterns/keyword-search-noise.md)
- [Skill-Based Workstream Split](knowledge/workflows/parallel-workstream-research.md)

## Rule Builder, Marketing Research & Tracking (6 nodes)

- [Competitor Marketing Research Dataset — 28 Brands Completed](knowledge/patterns/competitor-research-dataset.md)
- [Rule Builder Group Logic: Within-Group = OR, Across-Groups = AND](knowledge/patterns/rule-builder-group-logic.md)
- [Issue-Driven Research Tracking](knowledge/patterns/issue-driven-research-tracking.md)
- [Evaluation Log](knowledge/meta/evaluation-log.md)
- [GitHub Issues as Research Ledger](knowledge/patterns/issue-driven-research-tracking.md)
- [OR Within Group AND Across Groups Logic](knowledge/patterns/rule-builder-group-logic.md)

## Architecture Validation & Research Methodology (5 nodes)

- [Expert Panel Validation Before Finalizing Tech Decisions](knowledge/patterns/expert-panel-validation.md)
- [Research-Driven Architecture Decisions](knowledge/patterns/research-driven-architecture-decisions.md)
- [Architecture Validation via Multi-Agent Research](knowledge/workflows/architecture-validation-research.md)
- [Multi-Agent Parallel Research](knowledge/patterns/research-driven-architecture-decisions.md)
- [Social Media Practitioner Verification](knowledge/patterns/research-driven-architecture-decisions.md)

## Frontend Quality & Design System (4 nodes)

- [Design System Enforcement Prevents Drift](knowledge/patterns/design-system-enforcement-prevents-drift.md)
- [Claude Code Agent as Primary Builder](knowledge/patterns/claude-code-agent-as-primary-builder.md)
- [Automated Quality Gates](knowledge/patterns/claude-code-agent-as-primary-builder.md)
- [ESLint Design Token Enforcement](knowledge/patterns/design-system-enforcement-prevents-drift.md)

## Memory Storage (Zep/Graphiti evaluation) (3 nodes)

- [Zep Cloud Production Reliability Issues](knowledge/anti-patterns/zep-cloud-reliability.md)
- [Graphiti OSS Self-Hosted](knowledge/anti-patterns/zep-cloud-reliability.md)
- [Zep Cloud Managed Service](knowledge/anti-patterns/zep-cloud-reliability.md)

## Open Questions (unresolved) (9 nodes)

- How do rule conditions work? (OR/AND, categories)
- How to test rules against real data without forcing pass?
- What notification system? Custom vs Knock vs Novu?
- Data rooms: Papermark self-hosted or custom?
- Webhooks (Svix) and MCP server integration?
- Memory spec correctness: episodes, tiers, heuristics?
- Continuity spec: routing, reuse contracts, orchestrator boundary?
- How do frontend data structures change for fund-level configurability?
- Which agent framework? Harness evaluation?
