---
paths:
  - "**/*"
---

# Context for Pranav — 2026-04-10

## Decisions that affect your current work

- **Rule builder group logic is settled and documented**: Within-group = OR, across-groups = AND. A thread has exactly one category — putting `equals(A)` and `equals(B)` in separate groups = AND logic = zero matches ever. This is in `knowledge/patterns/rule-builder-group-logic.md`. Your original rules were correct; the confusion came from misapplied AND/OR. If you're building new rules, check that entry first.

- **Security stack is settled**: Infisical, Semgrep, Trivy, Coraza + OWASP CRS. Abhishek validated this via expert panel Apr 9. Do not re-open without a specific failure.

- **LangSmith tracing setup**: Your Apr 6 difficulty (API key belongs to different account than logged-in email, no org visibility) is documented in `knowledge/tool-configs/langsmith-tracing-setup.md`. If traces aren't flowing, check API key account alignment first.

## Cross-team connections

- You and Ankit-S are both updating the spec-to-ship playbook. Ankit-S pushed v7 on Apr 10 with reading guides as a NO-SKIP rule — every TypeScript interface now requires plain-language field mapping for non-technical reviewers. If you're updating the playbook for copilot rule-creation quality, v7 is the current baseline.

- You and Abhishek are both managing CI behavior — you want reliable CI gates for staging deploys, Abhishek temporarily disabled tests to unblock work. Neither approach is documented as a team protocol. A clean CI management decision (when to gate, when to bypass, how to re-enable) would help both of you.

## Expanding your questions

- The copilot rule-creation infrastructure (how it generates rules from user chat, quality gates, how to debug via staging DB logs) has no knowledge entry. Your Apr 7 investigation into copilot quality via staging logs is undocumented. This is a significant gap — if you resolved what you found, filing a report would prevent others from debugging the same production behavior from scratch.

- Your staging-deploy workflow (fresh branch from staging + CI gates + PR merge + GitHub Actions trigger) is also undocumented. A procedure entry here would be the team's canonical staging-deploy reference. The `architecture-production-readiness-gap` entry flags CI/CD as a gap area but has no concrete workflow.
