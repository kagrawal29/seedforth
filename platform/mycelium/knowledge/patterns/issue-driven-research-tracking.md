---
id: pattern-issue-driven-research-tracking
category: patterns
discovered: 2026-04-06
last-validated: 2026-04-06
confidence: high
type: knowledge
source: maverick-market-research — 38 issues as research ledger, 37/38 closed in 11 days
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 4
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.00
  last_scored: 2026-04-09
tags: [github-issues, research, tracking, methodology, deliverables, completion-signal]
relevant-when: planning research tasks, tracking data collection progress, organizing multi-phase research
related: [workflow-parallel-workstream-research, pattern-rapid-api-pivot, pattern-competitor-research-dataset]
---

# Issue-Driven Research Tracking

## What
maverick-market-research used GitHub Issues as a research task ledger. Each issue = one research workstream (e.g., "Twitter practitioner scraping: 20 accounts, ~4K posts"). 38 issues created, 37 closed in 11 days. Near-perfect completion rate with visible progress.

## Why
- Issues provide structured context: what was planned, what was collected, what the numbers are
- Closing an issue = definitive completion signal (vs. vague "done" in Slack)
- Issue history shows research evolution (methodology pivots, API failures, tool switches)
- Acts as institutional memory: anyone can trace the research journey from issue #1 to #38

## How to Apply
1. One issue per discrete research task (not mega-issues covering entire phases)
2. Include quantitative deliverables in the title ("287 items, 26 batches")
3. Close with summary of actual output vs. planned output
4. Use issue numbers as references in reports and knowledge entries
5. Keep issues factual — what was collected, how many, what tool, what gaps remain

## Evidence
- 38 issues spanning 4 phases, 6 platforms, 28 brands
- 3.5 issues created per day, 3.3 closed per day
- Issue bodies contain exact counts, API details, file paths
- Phase 3 issues reference Phase 2 issues, showing learning chain
