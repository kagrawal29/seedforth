---
id: pattern-rapid-api-pivot
category: patterns
type: procedure
version: 1
discovered: 2026-04-06
last-validated: 2026-04-06
confidence: high
source: maverick-market-research issues #5, #12, #22, #31 — 4 API pivots in 11 days
distributed-to: []
effectiveness: null
tags: [api, pivot, failure, xpoz, twitter-api, reddit, linkedin, apify, g2, scraping, backup-plan]
relevant-when: an API fails or returns poor results, planning data collection, evaluating new APIs
related: [anti-pattern-keyword-search-noise, pattern-issue-driven-research-tracking]
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Rapid API Pivot on Failure

## What
Structured process for detecting API failures and switching to alternatives within hours, not days.

## Why
4 API failures in 11 days, each resolved same-day. The key: small test first, backup identified in advance, failure documented in issues so future operators never repeat mistakes.

## Procedure
1. Before starting any collection run, test the API with a small query (5-10 items)
2. Evaluate results for noise ratio -- if >50% irrelevant, the API is not viable for this use case
3. Identify a backup API/method BEFORE committing to full scrapes
4. When failure is detected:
   - Stop the current run immediately (don't over-invest in fixing a bad tool)
   - Evaluate the backup: cost-per-result, rate limits, data quality
   - Switch to the alternative and run the same small test
   - Validate the new source meets quality threshold
5. Document the failure and pivot in the GitHub issue:
   - What failed (API name, specific call pattern)
   - Why it failed (noise ratio, rate limit, CAPTCHA, etc.)
   - What replaced it (new API, cost, quality comparison)
6. Close the old issue and open a new one for the replacement approach

## Pitfalls
- What breaks: Committing to full scrape without small test. Detection: thousands of noisy results before noticing. Fix: always test with 5-10 items first.
- What breaks: No backup identified. Detection: team blocked for days after API failure. Fix: require backup API in issue description before starting.
- What breaks: Failure documented only in conversation, not in issue. Detection: next person repeats the same mistake. Fix: always close issue with failure reason.

## Verification
- [ ] Small test query completed before full run (results reviewed for quality)
- [ ] Backup API/method documented in the issue before starting
- [ ] After pivot, new source achieves <50% noise ratio on test query
- [ ] GitHub issue closed with failure reason and replacement noted

## Evidence
- Issue #12: TwitterAPI.io integrated same day Xpoz keyword search abandoned ($0.07/496 tweets)
- Issue #22: 90% noise in old Xpoz data identified and cleaned
- 4 pivots in 11 days, none lost more than 1 day of progress
