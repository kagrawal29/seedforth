---
id: pattern-competitor-research-dataset
category: patterns
type: knowledge
discovered: 2026-04-07
last-validated: 2026-04-11
confidence: high
source: maverick-market-research PR #40, #44, #45 (Saurabh Thapa, 2026-04-07 to 2026-04-10) — competitor brands + employee deep dives + VC thought leaders
tags: [competitor-research, marketing, linkedin, twitter, website, 28-brands, positioning, messaging, differentiation, thought-leaders, content-strategy]
relevant-when: positioning Maverick, building marketing copy, making product differentiation decisions, understanding competitor messaging
related: [architecture-research-to-product-pipeline]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 3
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
  last_scored: 2026-04-12
---

# Competitor Marketing Research Dataset — 28 Brands Completed

## What
Full competitor marketing research sprint completed April 7, 2026. 28 VC-adjacent brands analyzed across Twitter/X, LinkedIn, and website channels. Three cross-competitor synthesis reports produced.

## Dataset Scope

| Channel | Coverage | Data Points |
|---------|----------|-------------|
| LinkedIn | 28 brands, 1,870 posts, 13 employee datasets | Brand posts, comments, senior employees |
| Twitter/X | 18 brands, 2,386 tweets, 5 employee accounts | Brand tweets, employee tweets |
| Website | 28 brands | Positioning, messaging, feature claims |

## Output Artifacts (maverick-market-research repo)
- `Competitor Marketing Research/linkedin_marketing_analysis.md` — cross-competitor LinkedIn synthesis
- `Competitor Marketing Research/twitter_marketing_analysis.md` — cross-competitor Twitter synthesis
- `Competitor Marketing Research/website_marketing_analysis.md` — cross-competitor website positioning synthesis
- `Competitor Marketing Research/tracker/master_list.csv` — 28-brand master tracker
- `Competitor Marketing Research/tracker/product_and_features.csv` — feature comparison matrix

Per-company deep dives:
- Carta: 200 brand posts + 470 comments + 352 employee posts (LinkedIn); 128 brand + 826 employee tweets
- Affinity: 200 posts + 130 comments + 5 employees (LinkedIn); 186 tweets
- Attio: Employee-only analysis (LinkedIn); 152 brand + 35 CTO tweets

## How to Use
- Before writing Maverick's positioning: read `website_marketing_analysis.md` for competitor claims
- Before building a new feature: check `product_and_features.csv` for differentiation gaps
- For VC investor conversations: LinkedIn analysis shows how incumbents communicate to fund managers
- For design partner demos: understand what messaging resonates with their existing tools

## Recent Extensions (April 9, 2026)

### Saurabh — Employee Deep Dives
- LinkedIn employee post deep dive: 773 posts, 26 employees, 7 brands analyzed (PR #44 merged)
- Twitter employee post deep dive: 17 accounts queried, 10 empty, 3 with signal
- This adds an employee-voice dimension to the existing brand-level analysis

### Drushi — Launch Case Studies
- Attio launch case study: 3 sourced research files (product showcases, cross-conversations, Affinity comparison)
- Figma launch case study: 4 sourced research files
- New directory: `Launch Case Studies/{brand}/` in maverick-market-research

## LinkedIn Thought Leader Research (April 10, 2026)

### Saurabh — VC Thought Leader Scrape
- 14 US VC thought leaders identified and scraped
- 706 LinkedIn posts + 1,162 comments collected
- Twitter handles confirmed for cross-platform mapping
- Content strategy discussion document added for Maverick's own LinkedIn strategy
- PR #45 merged (2026-04-10): LinkedIn thought leader scrape branch

This adds a **thought leader dimension** to the existing brand-level competitor analysis. The previous dataset covered competitor brands' official messaging. This new layer captures individual VC voices — the people who shape industry opinion. Useful for: understanding what content resonates with the VC audience Maverick targets, informing Maverick's own content strategy, and identifying influencers for launch amplification.

## Decile Hub — Primary Emerging Manager Competitor (April 11, 2026)

Deep emerging manager segment research identified Decile Hub (by VC Lab / Decile Group) as the most important competitor in the emerging manager segment:
- **Distribution moat**: Free for VC Lab's 800+ alumni. 1,000+ firms on Decile Hub monthly.
- **All-in-one**: LP management, deal flow, fund admin, AI toolkit (12 tools), LP Portal
- **94 NPS score** — highest in category
- **Weaknesses**: Tied to VC Lab ecosystem; AI is operational (thesis generation, pitch decks) NOT investment intelligence; no deal sourcing or due diligence automation; LP intelligence unclear beyond its own network

See `pattern-emerging-manager-solo-gp-segment` for full competitive analysis against Decile Hub.

## Evidence
- PR #40 merged: 2026-04-07T11:58 (171 files, Saurabh Thapa)
- PR #44 merged: 2026-04-09 (Saurabh — employee deep dives)
- PR #45 merged: 2026-04-10 (Saurabh — LinkedIn thought leader scrape: 14 US VC voices, 706 posts + 1162 comments)
- Drushi commits: 2026-04-09 (Attio + Figma launch case studies)
- GitHub issue #39 (open): "YouTube dataset ready (19 brands, 1891 videos) — next steps for product team"
- Emerging manager playbook: signals/artifacts/research-docs/emerging-manager-playbook.md (2026-03-29)
- Research spanning 12+ days (Phase 3 of market research effort, still growing)
