---
paths:
  - "**/*"
---

# Context for Abhishek — 2026-04-10

## Decisions that affect your current work

- **Memory stack is settled**: Graphiti OSS + FalkorDB + Trigger.dev v4 — settled by Sahiram on Apr 6 (20M token research session, 31 agents). Relevant because the SSE streaming constraint you found in Zuplo directly affects how agent responses reach users — agent streaming runs through Next.js API routes, not PostgREST. Any API gateway must handle SSE at the transport layer.

- **Agent harness is settled**: Vercel AI SDK + Trigger.dev v4 — settled by Sahil on Apr 9 (Grand Debate, 8 specialist agents, 44M tokens). Mastra is rejected. Three execution modes: inline (<100ms), durable Trigger.dev tasks (long-running), MCP proxy via Nango. Relevant because Zuplo sits in front of this stack — any rate limiting or API key gating must account for durable task response times.

- **Security stack is settled**: Infisical (secrets), Semgrep (SAST), Trivy (CVE), Coraza + OWASP CRS (WAF) — settled Apr 9. Decision was validated via expert panel. Do not re-open unless a specific technical failure is found.

## Cross-team connections

- Your Zuplo evaluation (SSE requires Enterprise at $1k+/mo) is being watched by Kshitiz's meta-system — this is an active architectural decision with no settled knowledge entry yet. If you reach a conclusion (adopt/reject), file a report so it gets captured before others stumble into the same research.

- You and Pranav are both managing CI behavior — you temporarily disabled tests to unblock work, Pranav is building a staging-deploy workflow dependent on CI gates. No team-wide CI management protocol exists. If you establish a re-enable pattern, it's worth documenting.

## Expanding your questions

- You've been asking about Nango (Salesforce/HubSpot connectors, contacts API, NILAs compliance). The tech stack lists Nango Self-Hosted (250+ connectors) as settled, but depth on connector coverage and API call patterns is not in any knowledge entry — this is a documented gap. Your evaluation findings would be the primary evidence for a new entry.

- Your Zuplo research found zero practitioner signal on social media (15 G2 reviews, no Reddit/Twitter discussions). This matches the `keyword-search-noise` anti-pattern. Consider whether Zuplo's thin community is itself a risk signal before committing.
