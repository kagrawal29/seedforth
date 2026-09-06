---
id: anti-pattern-keyword-search-noise
category: anti-patterns
discovered: 2026-04-06
last-validated: 2026-04-06
confidence: high
type: knowledge
source: maverick-market-research issues #5, #12, #22 — 90-97% noise from keyword search
distributed-to: []
effectiveness: null
tags: [keyword-search, noise, xpoz, twitter, reddit, social-media, brand-names, practitioner-accounts, filtering]
relevant-when: doing social media research, scraping Twitter or Reddit, searching for brand mentions, planning data collection
related: [pattern-rapid-api-pivot, workflow-parallel-workstream-research, tool-config-research-tools]
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Keyword Search on Social Platforms = Noise

## What
Early data collection used keyword search (Xpoz for Twitter, sort=relevance for Reddit) as the primary method. Result: 90-97% noise. Common words in brand names (Carta, Affinity, Visible, Cap) matched thousands of irrelevant posts.

## Why
Brand names in the VC tools space are often common English words. "Carta" matches immigration posts, "Affinity" matches dating/psychology, "Visible" matches anything. Even with qualifiers ("Carta VC"), noise remains high because the signal volume is low (VCs are a small community).

## How to Apply
1. Never use keyword search as primary method for brands with common names
2. Start with practitioner accounts and company pages — 10x cleaner signal
3. Use keyword search only for: unique brand names (PitchBook, AngelList) or highly specific phrases ("vc deal flow tool")
4. Budget for 97% waste when using keyword search — plan LLM filtering costs accordingly
5. Document which brands are "safe" (unique names), "ambiguous" (need qualifiers), and "hopeless" (aliases only)

## Evidence
- Xpoz keyword search for common terms: 100K+ noise (issue #5)
- Reddit sort=relevance Phase 1: 97% noise eliminated by LLM filter (issue #22)
- TwitterAPI.io with qualified phrases: much better signal ($0.07/496 tweets vs hours of noise)
- Brand tier system (safe/ambiguous/hopeless) codified in AGENTS.md after this lesson
