---
id: workflow-parallel-workstream-research
category: workflows
type: procedure
version: 1
discovered: 2026-04-06
last-validated: 2026-04-06
confidence: high
source: maverick-market-research — completed Phase 1-3 across 6 platforms in 7 days with 2 people
distributed-to: [maverick-market-research#39]
effectiveness: null
tags: [parallel, workstream, research, data-collection, analysis, youtube, competitor, market-research, phases]
relevant-when: planning multi-person research, splitting data collection from analysis, organizing phased research
related: [pattern-issue-driven-research-tracking, architecture-research-to-product-pipeline]
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Parallel Workstream Research

## What
Run multi-person research by splitting data collection and analysis into parallel workstreams, each tracked independently via GitHub Issues.

## Why
Data collection and analysis require different skills. Parallel execution cut calendar time ~50%. Async PRs at phase boundaries eliminated incremental review overhead.

## Procedure
1. Split work by skill, not by platform:
   - Workstream A: data infrastructure + collection (API setup, scraping, raw data)
   - Workstream B: analysis + positioning (synthesis, scoring, reports)
2. Create GitHub Issues for each workstream with label prefixes (e.g., "Workstream B: ...")
3. Define deliverables upfront in issue titles with counts (e.g., "287 items, 26 batches")
4. Codify analysis rules (AGENTS.md or equivalent) BEFORE analysis phase begins -- do not retrofit
5. Each person works asynchronously on their workstream
6. Sync via bulk PRs at phase boundaries (not per-task):
   - Data person opens PR when a collection phase is complete
   - Analysis person opens PR when a scoring/synthesis pass is complete
7. Auto-merge PRs if trust-based collaboration is established (no blocking reviews)
8. At each phase boundary, review issue completion rate and adjust scope for next phase

## Pitfalls
- What breaks: Splitting by platform instead of skill. Detection: one person blocked waiting for API access while another idles. Fix: split by data-ops vs analysis.
- What breaks: Analysis rules not codified before analysis starts. Detection: inconsistent scoring criteria, retrofitting in Phase 3. Fix: write AGENTS.md with analysis rules before Phase 2.
- What breaks: Per-task PRs instead of bulk sync. Detection: review bottleneck, many small PRs. Fix: batch PRs at phase boundaries only.

## Verification
- [ ] Workstreams have separate issue labels and each person knows their scope
- [ ] Analysis rules document exists BEFORE analysis phase begins
- [ ] PRs are batched at phase boundaries (not one per task)
- [ ] Issue completion rate tracked at each phase boundary (target: >90%)

## Evidence
- Phase 1-3: 7 days, 2 people, 6 platforms. 38 issues, 37 closed.
- Clean separation: Saurabh 10 commits (data), Sahil 5 commits (analysis)
- Phase 4: 19 brands, 1,891 videos scraped in single day by one person
