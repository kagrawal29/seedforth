---
id: architecture-security-scanning-stack
category: architecture
type: knowledge
version: 1
discovered: 2026-04-09
last-validated: 2026-04-09
confidence: high
source: Abhishek LangSmith traces 2026-04-09 — turns 07:00-07:27, 1.9M tokens; decisions #17 and #18 explicitly marked DECIDED
tags: [security, infisical, semgrep, trivy, coraza, owasp-zap, sast, dependency-scanning, waf, secrets-management, ci, pre-commit]
relevant-when: setting up CI security gates, choosing secrets management, adding SAST or dependency scanning, implementing WAF, security hardening sprint
related: [architecture-tech-stack-completed]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Security Stack Decisions — Secrets + Scanning (SETTLED)

## What
Two security decisions locked in Abhishek's session on 2026-04-09 after expert panel review (4 specialists: AppSec, DevSecOps, Cloud Security, Backend). Both are DECIDED — do not re-evaluate.

## Decisions

| # | Layer | Tool | Edition | Cadence | Cost |
|---|-------|------|---------|---------|------|
| 17 | **Secrets Management** | Infisical | Self-hosted (MIT) | Always-on; PR block if secrets exposed | $0 |
| 18 | **SAST** | Semgrep | Community Edition (LGPL 2.1) | Every PR via GitHub Actions + pre-commit | $0 |
| 18 | **Dependency CVEs** | Trivy | OSS | Every PR | $0 |
| 18 | **WAF** | Coraza + OWASP Core Rules | OSS | Runtime (always-on) | $0 |
| 18 | **DAST (deferred)** | OWASP ZAP | — | Sprint 3+ (after real endpoints exist) | $0 |

## Why
- All tools chosen for OSS + self-hosted compatibility — same constraint as rest of stack (on-prem enterprise clients)
- Expert panel (4 agents) confirmed all tools fit Maverick's context; no conflicts with existing stack
- Semgrep Community covers OWASP Top 10 + Node/TypeScript-specific rules at zero cost; enterprise tier not needed at current scale
- Trivy is already the standard for container + dependency scanning in self-hosted Docker setups
- Coraza (Go, Apache license) is the only production-grade OSS WAF with active maintenance; OWASP ModSecurity is EOL
- DAST deferred deliberately: running DAST against fixture/mock endpoints produces noise; activate Sprint 3+ when real API exists

## How to Apply
1. **Infisical**: All secrets stored in Infisical; inject via Docker secrets at runtime. Block PRs if hardcoded secrets detected.
2. **Semgrep**: Add to GitHub Actions pre-merge check. Also add as pre-commit hook locally.
3. **Trivy**: Run in CI on every PR targeting `main`. Focus on `CRITICAL` + `HIGH` CVEs initially.
4. **Coraza**: Deploy as middleware in Traefik reverse proxy config. Use OWASP Core Rule Set v3.3+.
5. **DAST**: Schedule for Sprint 3 backlog — not blocking anything now.

## Evidence
- Abhishek LangSmith traces 2026-04-09 (turns 06:20–07:27, ~1.9M tokens)
- Decisions marked DECIDED in batch scorecard (turn 07:07:44)
- 4-agent expert panel review: AppSec Engineer, DevSecOps, Cloud Security, Backend specialist
