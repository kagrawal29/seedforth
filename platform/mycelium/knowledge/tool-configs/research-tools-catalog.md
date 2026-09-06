---
id: tool-config-research-tools
category: tool-configs
discovered: 2026-04-06
last-validated: 2026-04-06
confidence: high
type: knowledge
source: maverick-market-research — validated across 6 platforms, 28 brands, 11 days
distributed-to: []
effectiveness: null
tags: [research, xpoz, twitter-api, youtube, linkedin, rapidapi, searxng, mcp, social-media, scraping, data-collection, competitor-analysis]
relevant-when: doing research, scraping social media, collecting competitor data, setting up research tools, choosing data collection APIs
related: [anti-pattern-keyword-search-noise, pattern-rapid-api-pivot, workflow-parallel-workstream-research]
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Research Tools Catalog

## What
Available tools for research beyond web search, validated from real production use across the maverick market research effort.

## Why
Different platforms need different tools. Using the wrong tool wastes time and money (see: keyword-search-noise anti-pattern). This catalog maps tools to use cases.

## How to Apply

### Xpoz MCP — Social Media Research
- Fetches posts, profiles, replies from Twitter/X, Reddit, Instagram, TikTok
- **Works well:** specific account posts, thread analysis, CSV export for bulk data, quoted phrase search
- **Does NOT work:** broad keyword search for common words (90%+ noise)
- **Pattern:** practitioner accounts first → company pages → keyword search only for unique brand names
- Config: `.claude/.mcp.json` in maverick-market-research

### TwitterAPI.io — Keyword Search
- Better than Xpoz for boolean queries, date-range filtering, volume estimation
- Cost: ~$0.15 per 1,000 tweets
- Config: `config/twitterapi_io.json` in maverick-market-research

### YouTube Data API — Video Research
- Free tier, no cost for basic searches
- Good for: competitor demo videos, practitioner reviews, conference talks
- 19 brands scraped, 1,891 videos collected in maverick-market-research

### RapidAPI LinkedIn — Professional Data
- Company pages, practitioner profiles, post collection
- Rate limited — use exponential backoff

### SearXNG — Self-Hosted Search
- Private aggregate search across multiple engines, no API keys needed
- Requires Docker
- Good for broad research without rate limits

### Research Methodology
1. Start with highest-signal sources: practitioner accounts > company pages > keyword search
2. Test new APIs with small queries before full collection runs
3. Always have a backup API identified before starting
4. Document failures and pivots
5. Track cost-per-result and optimize

## Evidence
- 6 platforms, 28 brands, 11 days of validated research
- 4 API pivots documented (Xpoz → TwitterAPI.io, Reddit API fix, Apify workaround, G2 manual)
- Issue #5, #12, #22, #31 in maverick-market-research document each pivot
