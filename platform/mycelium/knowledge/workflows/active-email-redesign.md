---
id: exploration-email-redesign
category: workflows
type: exploration
discovered: 2026-04-07
last-validated: 2026-04-07
confidence: low
source: Ankit-S LangSmith traces 2026-04-07 — email timeline to inbox redesign
who: Ankit-S
topic: Email view redesign from timeline to inbox layout in deal workspace
tags: [email, timeline, inbox, redesign, ui, deal-workspace, active]
relevant-when: working on email features, modifying EmailThreadItem or EmailThreadList components, changing deal workspace layout
related: [architecture-fixture-first-development]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# ⚡ Active: Email View Redesign

Ankit-S is redesigning the email tab in the deal workspace from a timeline view to an inbox-style list with expandable rows.

Design is in progress. If you need to touch EmailThreadItem.tsx, EmailThreadList.tsx, or the email section of the deal workspace — coordinate with Ankit first.

## Approach (from traces)
- Restyle EmailThreadList + EmailThreadItem (not rebuild from scratch)
- Remove timeline icons + connector lines
- Replace with initials avatar + inbox row layout
- Click to expand inline (not navigate away)
- Keep time-period grouping ("Today", "This Week"), lose timeline visual treatment
