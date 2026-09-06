# How VCs Actually Work and Use AI: Ground Truth

**Research Date:** March 29, 2026
**Purpose:** Inform Maverick product strategy and positioning with empirical data on VC workflows and AI adoption

---

## Table of Contents

1. [The "Stealth AI VC" Trend](#1-the-stealth-ai-vc-trend)
2. [Day-in-the-Life: What VCs Actually Do](#2-day-in-the-life-what-vcs-actually-do)
3. [VC Tech Stack: What They Actually Use](#3-vc-tech-stack-what-they-actually-use)
4. [VC Fund Operations Pain](#4-vc-fund-operations-pain)
5. [AI Adoption Rate in VC: Hard Numbers](#5-ai-adoption-rate-in-vc-hard-numbers)
6. [The Vibe-Coding Threat](#6-the-vibe-coding-threat)
7. [VC Hiring Trends for AI Roles](#7-vc-hiring-trends-for-ai-roles)
8. [What VCs Say They Want from AI](#8-what-vcs-say-they-want-from-ai)
9. [Implications for Maverick](#9-implications-for-maverick)

---

## 1. The "Stealth AI VC" Trend

### The Reality: Claude and ChatGPT ARE the VC Tech Stack Now

General-purpose AI assistants (Claude, ChatGPT, Perplexity) have become **core infrastructure** for investment teams, not optional add-ons. They handle:

- **Memo drafting** -- First drafts generated in minutes with structured prompts covering team, product, traction, and risks
- **Financial modeling** -- Claude is popular for its long context windows and accuracy in modeling scenarios
- **Market research** -- Perplexity and Claude used for structured deep dives on TAM, competitive landscape, and market dynamics
- **Deal evaluation** -- AI-generated synthesis reports and polished investment memos

### Real Firm Examples

| Firm | What They Do With AI |
|------|---------------------|
| **Notable Capital** | Two-person BD team manages 500+ introductions/year using AI-powered workflows with Claude + MCP integrations |
| **World Innovation Lab** | Runs Claude locally to power 70+ investor workflows while maintaining compliance; 95%+ accuracy in deal categorization |
| **Founderpath** | Built a 23-page mega-prompt that writes 10-page investing memos and wires in 24 hours without meetings. 500 deals, $201M invested using AI-driven process |
| **Earlybird Ventures** | Partner Andre Retterath advocates "80/20 approach" -- prioritizing off-the-shelf LLMs over custom solutions |

### The Key Insight

Most VCs are NOT buying purpose-built AI tools. They are using **Claude/ChatGPT directly** with custom prompts, occasionally connected via MCP or APIs to their existing data. The "stealth" part is real: firms don't advertise their AI workflows because they see it as competitive advantage.

**Affinity's MCP server** (now in beta) is a signal -- it positions the CRM as a data layer that Claude/ChatGPT can query directly, rather than building its own AI features. This validates the approach that the LLM IS the interface.

---

## 2. Day-in-the-Life: What VCs Actually Do

### By Role

**Analyst (most junior):**
- 50-60 hours/week
- Primarily sourcing: emails, meetups, calls, networking
- Market research: TAM/SAM/SOM sizing, competitor mapping, thematic deep dives
- Preliminary due diligence: customer calls, data-room analysis, financial model sanity checks
- Deal memos: the most visible output, distilling weeks of research into narratives

**Associate:**
- Sourcing: attending events, scanning Slack/Discord communities, maintaining university connections, nurturing angel/scout/accelerator relationships
- Triage: back-of-the-envelope TAM, validating traction metrics, checking competitive white space
- Deep diligence: customer reference calls, churn-cohort pulls, pricing-power analyses
- Portfolio support: collecting KPI data, preparing board materials, sourcing talent for founders

**Principal/VP:**
- Leading deal execution on specific investments
- More active in portfolio company operations than GPs
- Running IC presentation processes
- Managing associate/analyst output

**General Partner:**
- Morning: reviewing overnight emails, LP follow-ups, industry news, pipeline meetings
- Midday: back-to-back 30-min founder pitches with 10-min debriefs
- Afternoon: deep-dive diligence, customer references, financial model iteration, term sheet decisions
- Ongoing: board seats, LP relations, fundraising, conferences, firm marketing
- GPs do NOT cold-call/email -- they rely on network introductions

### Time Allocation Pattern (Early-Stage VC)

| Activity | Approx. Share | AI Automation Potential |
|----------|--------------|----------------------|
| Sourcing & screening | ~35-40% | HIGH -- signal monitoring, company discovery |
| Due diligence | ~20-25% | MEDIUM -- research automation, not judgment calls |
| Deal memos & IC prep | ~10-15% | HIGH -- first draft generation, data synthesis |
| Portfolio support | ~10-15% | MEDIUM -- KPI collection, board prep automation |
| LP relations & reporting | ~10% | HIGH -- data aggregation, report generation |
| Admin & operations | ~5-10% | HIGH -- scheduling, email, compliance |

**Critical observation:** At early-stage firms, associates do MORE sourcing and less deal execution. At later-stage firms, it reverses. The AI opportunity varies by fund stage.

### Team Size Reality

- Rule of thumb: **3 people per $100M** in the fund
- Funds <$20M often have **part-time teams**
- A two-GP pre-seed fund may take all meetings together with zero associates
- Most VC firms have **fewer than 50 employees** -- the median is far smaller

**Wave 4 validation:** A solo GP manages $750M with zero employees using AI agents. Paul Hsu runs '100s of AI agents' for sourcing/diligence. Air Street closed $232M as Europe's largest solo GP. Alexis Ohanian built VC email tools with Claude over a weekend (607 likes). The solo GP + AI segment is not aspirational — it is operational.

---

## 3. VC Tech Stack: What They Actually Use

### Market Size

The VC software market hit **$0.93 billion in 2025**, growing at 11.4% annually, with **600+ tools** competing for budget.

### The Actual Stack by Category (2026)

**Tier 1: Must-Have (Nearly Universal)**

| Category | Dominant Tool | Alternatives | Price Range |
|----------|--------------|-------------|-------------|
| CRM / Deal Flow | Affinity | Attio, 4Degrees | $125-200/user/mo |

**Wave 4 signal from r/private_equity:** 'CRMs will be gone in 5-8 years, replaced by agents.' Not a single PE practitioner expressed positive CRM sentiment in our research. Universal hatred across Affinity, Attio, DealCloud, Salesforce. The CRM category itself may be dying.
| Market Intelligence | PitchBook | Crunchbase, Dealroom | $12K-70K/yr |

**PitchBook's moat is cracking further (Wave 4):** At $31K/seat with 12-18 month stale employee data, practitioners now say 'LinkedIn is the truest, freshest source.' An open-source PitchBook alternative post got 80 upvotes on Reddit. Claude + MCP connectors are commoditizing PitchBook's data at $20/month.
| Cap Table | Carta | Pulley, AngelList | $280-77K/yr |
| E-Signatures | DocuSign | -- | Standard |
| Communication | Superhuman, Slack | Gmail | -- |

**Tier 2: Widely Adopted**

| Category | Leading Tools |
|----------|--------------|
| Meeting Notes | Granola ($1.5B valuation, March 2026), Fireflies |
| Portfolio Monitoring | Standard Metrics, Visible.vc, PortfolioIQ |
| Sourcing Intelligence | Harmonic (30M+ companies), Grata (19M+), Synaptic |
| Data Rooms | Drooms, Ansarada |
| LP Reporting | Juniper Square, Allvue, FundrBird |

**Tier 3: Emerging / AI-Native (2026)**

| Category | Tools |
|----------|-------|
| AI Data Workflows | Rowspace ($50M from Sequoia, Feb 2026) |
| AI Deal Analysis | DeckMatch, Yutori |
| AI Meeting Prep | Granola Spaces |
| AI Research | Perplexity, Claude, ChatGPT |

### VC Tech Stack Survey Data (Blue Future Partners, 137 funds <$200M)

- 74% of funds spend $10K+ on tech; 17% spend >$50K
- 30% employ full-time data/engineering personnel
- CRM: generalist tools (SalesforceIQ, Streak, Pipedrive) still outpace VC-specific -- only 5% build proprietary systems
- 87% don't use LP community platforms
- Majority plan budget increases; 14% targeting 30%+ growth

### The 500+ Tool Problem

PortfolioIQ catalogs **500+ tools across 12 categories**. The fragmentation is extreme. A typical fund might use 10-20 different tools with minimal integration between them. This creates massive context-switching and data silo problems.

---

## 4. VC Fund Operations Pain

### The Core Tension

Emerging managers wear two hats simultaneously:
1. **"Expert Investor"** -- generating alpha through sourcing and selection
2. **"Capable Operator"** -- reconciliation breaks, investor tax questions, NAV errors

Every minute on operations is a minute not sourcing deals. This tension is the #1 structural problem in VC.

### Specific Pain Points

**1. LP Reporting (The Quarterly Nightmare)**
- **95% of GPs still use Excel** to collect portfolio data and prepare LP reports
- Manual reporting becomes unmanageable beyond ~30 portfolio companies
- LPs demand quarterly comprehensive reports + increasingly request monthly updates
- Custom reporting requirements vary by LP -- firms lack dedicated staffing
- Data aggregation across portfolio companies with different financial systems is a core challenge

**2. Capital Calls & Distributions**
- Precise timing required -- calling too early ties up LP cash, too late misses opportunities
- Tax implications vary by investor type (domestic vs. foreign)
- Calculation accuracy is legally critical
- Coordination across multiple LPs with varying commitment levels

**3. Fund Accounting Complexity**
- Capital calls, distribution waterfalls, carried interest calculations, NAV computations
- Increasingly challenging to manage manually as portfolios scale
- Spreadsheet logic lives in emails; each quarter becomes a bespoke project

**4. Regulatory Compliance Burden**
- SEC filed 583 enforcement actions in 2024 with $8.2B in penalties
- AIFMD in Europe, GDPR, state requirements, international standards
- Rising costs strain smaller firms disproportionately
- Continuous monitoring required as regulations evolve

**5. Multi-Entity Complexity**
- Co-investment vehicles, SPVs, parallel funds create tracking nightmares
- Varied regulatory regimes require separate filings per jurisdiction
- Cross-border tax implications demand specialized knowledge

**6. The Spreadsheet Trap**
- One person "owns the spreadsheet" -- logic lives in emails
- Each quarter becomes a bespoke project rather than a repeatable process
- Operating models for single deals rarely scale cleanly to fund-grade structures
- Manual fund management across spreadsheets, email, and board decks is now a liability

### What This Means

The operational burden falls hardest on **emerging managers** (Fund I/II, <$100M). They can't afford dedicated ops teams, fund administrators charge too much relative to fund size, and LPs still expect institutional-grade reporting. This is a massive underserved gap.

---

## 5. AI Adoption Rate in VC: Hard Numbers

### The Data Points

| Metric | Value | Source |
|--------|-------|--------|
| VCs using AI to automate daily tasks | **85%** (up from 76% in 2025, 62% in 2024) | Affinity survey, ~300 dealmakers |
| VCs using AI for deal sourcing research | **82%** (up from 64% in 2025, 55% in 2024) | Affinity survey |
| Organizations with regular AI use (any function) | **88%** (up from 78%) | McKinsey State of AI 2025 |
| Firms reporting NO AI investment | **40%** | McKinsey 2025 |
| VC investment decisions informed by AI/data analytics | **75%+** (projected) | PortfolioIQ estimate |

### Productivity Impact

| Firm | Metric |
|------|--------|
| Bessemer Venture Partners | Reclaimed **234 hours per analyst** after AI integration |
| BlackRock | **5x increase in research throughput** (2-3 companies/day to 10-15) |
| AI-driven VC sourcing firms | Report reviewing **3-5x more qualified opportunities** |
| AI-powered diligence | **40-60% improvement** on initial screening speed |
| AI anomaly detection | Detects financial stress **2.3 months earlier** than traditional board reporting |
| AI red flag detection | Identified problematic provisions in **87% of cases** (vs 63% manual) |

### What "Using AI" Actually Means

The 85% headline is misleading. For most VCs, "using AI" means:
- Pasting pitch decks into ChatGPT for quick summaries
- Using Perplexity for market research instead of Google
- Having Claude draft cold emails or memo sections
- Using Granola or Fireflies for meeting notes

It does NOT typically mean:
- Systematic AI-powered deal sourcing with proprietary models
- Automated portfolio monitoring with real-time alerts
- AI-driven LP reporting and fund administration
- Custom fine-tuned models for investment analysis

**The gap between "uses ChatGPT sometimes" and "AI-native operations" is enormous.** This is where the opportunity lives.

**Social media signal quality:** Vendor-to-practitioner tweet ratio on Twitter is 4:1 -- enormous builder energy but limited buyer adoption signal. Instagram and TikTok confirmed zero signal for VC tools.

---

## 6. The Vibe-Coding Threat

### How Real Is It?

Very real, but nuanced.

**The macro picture:**
- Vibe coding went from meme to **$4.7 billion market** in under 18 months
- **35% of teams have already replaced at least one SaaS tool** with custom-built solutions (Retool 2026 survey)
- **78% plan to build more custom tools** in 2026
- **93% of builders use LLMs** for coding/building/automation
- **$285 billion evaporated from global software stocks** in 48 hours after Claude Cowork/Code launch (Feb 2026)
- **40% of IT budgets** being reallocated from traditional SaaS to agentic platforms and LLM tokens

**SaaS categories under replacement pressure (Retool data):**
- Workflow automations: 35%
- Internal admin tools: 33%
- BI tools: 29%
- **CRMs and form builders: 25%**
- Project management: 23%

### VC Firms Building Their Own Tools

This is the most alarming finding for any VC SaaS vendor:

| Firm | Tool | What It Does |
|------|------|-------------|
| **Alpaca VC** ($78M) | "Gordon" | AI analyst that generates prospect lists with connection routes. Quote: "We want to give everybody their own personal AI analyst." |
| **DVC** ($75M) | AI recommendation system | Identified investments before growth, led by former DoorDash tech lead |
| **Topology Ventures** ($75M) | "Fiber" (internal CRM) | Predicts founder movements and market signals. Quote: "If I incubated it, it could produce venture-scale returns. It's so much alpha we keep it in-house." Hired 24-year-old quant from Citadel. |
| **Thrive Capital** | "Puck" | Processes 10B tokens across thousands of tasks. Actively recruiting more AI engineers. |
| **SignalFire** (~$3B AUM) | "Beacon" | Maps 650M+ individuals, 80M+ organizations. 12+ years of development. Core differentiator for the firm. |

### The Nuance: Why It's Not a Death Sentence for VC SaaS

1. **Only 31% prompt their way to complete applications** -- most vibe-coders build discrete components, not full systems
2. **60% of vibe-coded tools were built outside IT oversight** -- security, maintenance, and reliability are major issues
3. **Only 44% test AI-generated code thoroughly** -- most custom tools are fragile
4. **The firms building custom tools are the outliers** -- they hired dedicated AI engineers from Citadel, DoorDash, etc. Most VCs don't have this capability.

**Bottom line:** The vibe-coding threat is real for simple, modular SaaS tools (CRMs, basic dashboards). It is much less threatening for tools that require persistent data infrastructure, multi-user workflows, integrations, and compliance guarantees.

**The DIY threat is concrete and quantifiable:** The DIY Maverick stack (Claude + PitchBook MCP + Affinity MCP + Standard Metrics MCP + Granola) costs under $500/month and covers 60-70% of associate work. The window to be better than DIY is 6-12 months.

---

## 7. VC Hiring Trends for AI Roles

### The Data

- AI-related job titles among **VC Platform members grew from 1% to 6%** in one year (6x increase)
- AI job postings across all sectors are **up 130%** year-over-year
- VC firms actively recruiting AI engineers: Alpaca VC, DVC, Topology Ventures, Thrive Capital, Union Square Ventures, Scale Venture Partners, SignalFire

### Specific Hiring Moves

| Firm | Action |
|------|--------|
| Thrive Capital | Actively recruiting AI engineers despite already having Puck |
| Union Square Ventures | Hired new AI Lead (October 2025) |
| Topology Ventures | Recruited 24-year-old quant engineer from Citadel |
| Scale Venture Partners | Actively hiring technical talent for AI infrastructure |
| WndrCo | Revised job applications to require AI tool skills |
| DVC | Working with former senior DoorDash technical lead |

### What VCs Are Hiring For

1. **Data engineers** for pipeline development
2. **ML engineers** for model building
3. **Product-minded analysts** bridging tech and investment process
4. **Domain experts** combining data science with sector knowledge

### Cost Reality

Building proprietary AI systems typically requires **$500K-$2M annually** for talent, data licensing, and infrastructure. Initial value from commercial platforms appears in 3-6 months; developing proprietary capabilities requires 6-24 months.

### Interpretation

Only the largest and most tech-forward firms are hiring dedicated AI talent. The vast majority of VC firms (especially sub-$500M) will never hire an AI engineer. They need **productized AI** that works out of the box. This is Maverick's market.

---

## 8. What VCs Say They Want from AI

### From Partner/GP Interviews

**Deal Sourcing & Signal Detection:**
- Surface investment insights from vast datasets: founder track records, market signals, hiring trends
- "Process data at institutional scale while still moving at startup speed"
- Identify companies predicted to raise within 45 days
- Flag hiring patterns and growth signals indicating momentum

**Portfolio Intelligence:**
- Auto-collect financial and operational data (eliminate manual quarterly data chasing)
- Alert investors to risks and opportunities as they emerge
- Detect financial stress 2.3 months before traditional reporting
- Benchmark portfolio companies against peer cohorts

**Operational Efficiency:**
- Memo first drafts in minutes, not days
- Meeting note capture without intrusive bots (hence Granola's $1.5B valuation)
- Automated LP reporting that doesn't require quarterly fire drills
- Integration across the 10-20 tools they already use

**What They DON'T Want:**
- **Black boxes** -- "Investors are used to judgment calls, not probability scores. They don't like to be told what to do by a black box." (Dale Chang, Scale VP)
- **Replacement of human judgment** -- ~1/3 of diligence focuses on founder character and learning disposition, which AI cannot assess
- **Yet another tool** -- the 500+ tool landscape creates fatigue; VCs want consolidation, not more point solutions
- **Cloud-stored sensitive data** -- Granola's privacy-first approach (no stored audio, no third-party model training) resonates specifically because VCs are paranoid about deal information leaking

### The Explainability Requirement

Scale VP discovered that **even more accurate AI models failed adoption** because investors rejected recommendations from black boxes. They pivoted to providing the "why" behind suggestions rather than opaque probability scores. This is critical product design insight.

### The Bifurcation Prediction

Multiple VCs predict the industry will split:
- **Mega-funds** leveraging AI for broad market coverage and institutional data infrastructure
- **Specialized niche players** using AI for deep domain analysis

Both need AI, but in fundamentally different ways.

---

## 9. Implications for Maverick

### Strategic Positioning Insights

**1. The "Stealth AI VC" Trend Validates Maverick's Architecture**

VCs are already using Claude/ChatGPT as their primary AI tool. They don't want another dashboard -- they want their LLM to know their deal context. Maverick should position as the **data and workflow layer that makes Claude/ChatGPT useful for VC work**, not as a competing AI interface.

Key implication: MCP-first architecture is correct. Affinity is already going this direction with their MCP server beta.

**Anthropic's own PE ambitions:** Anthropic is building PE-specific plugins with /source, /ic-memo, /diligence commands and discussing PE consulting JVs with Blackstone/H&F/Permira.

**2. The Fund Ops Gap Is the Beachhead**

95% of GPs use Excel for LP reporting. The quarterly reporting nightmare is universal pain. Emerging managers (<$100M) can't afford Juniper Square or dedicated fund admins. This is an underserved, high-pain market that is NOT easily replaced by vibe coding (it requires persistent data, compliance, multi-party workflows).

Key implication: Portfolio data collection + LP reporting automation could be the wedge feature. It's operationally sticky, touches real money, and is too complex for a vibe-coded solution.

**3. The Vibe-Coding Threat Is Real But Bounded**

25% of teams are replacing CRMs with custom tools. However, only firms with dedicated AI engineers (Topology, Thrive, Alpaca) build serious internal systems. The 95% of VC firms without AI engineers need productized solutions.

Key implication: Maverick must deliver value that's clearly beyond what a GP could vibe-code in a weekend. This means: integrated data pipelines, multi-source enrichment, compliance-grade reporting, and persistent institutional knowledge.

**Vocabulary gap:** 'AI agent' has zero mentions in r/venturecapital comments. This terminology has not penetrated VC practitioner vocabulary. Whoever claims 'AI VC Associate' first owns the category definition.

**4. Explainability Is Non-Negotiable**

Scale VP's experience is a warning: even better AI models fail if they're black boxes. VCs want to understand WHY the AI recommends something. They want to enhance their judgment, not outsource it.

Key implication: Every AI feature should show its reasoning, cite its sources, and present itself as "here's what I found" rather than "here's what you should do."

**5. Privacy Is a Moat**

Granola's $1.5B valuation is substantially driven by its privacy-first approach (no stored audio, no third-party model training). VCs are paranoid about deal data. World Innovation Lab runs Claude locally for compliance.

Key implication: Local/private AI processing, SOC2, zero-training guarantees, and data residency options are competitive advantages, not nice-to-haves.

**6. The Integration Problem Is the Opportunity**

500+ tools, 12 categories, minimal interoperability. VCs live in Affinity + PitchBook + email + Notion + Excel. They don't want tool #501. They want something that connects tools #1-#500.

Key implication: Maverick should be the connective tissue, not another silo. MCP servers, API integrations, and the ability to query across data sources is the differentiator.

**7. The Time Allocation Data Shows Where AI Hits Hardest**

Sourcing/screening (35-40% of time) and memo writing (10-15%) are the highest-AI-automation potential. Portfolio monitoring (10-15%) is medium. But the highest-pain activity is LP reporting/ops (~10% of time but 100% of stress).

Key implication: Build for the pain, not just the time. A feature that eliminates quarterly reporting stress is worth more than one that saves 30 minutes on sourcing.

**8. Pricing Must Match the Market**

- Funds <$20M have part-time teams and minimal budgets
- 74% of sub-$200M funds spend $10K+ on tech; only 17% spend >$50K
- The rule of thumb is 3 people per $100M

Key implication: Pricing needs a free/low tier for emerging managers (fund size <$50M), a growth tier for established funds ($50-500M), and enterprise for mega-funds. The emerging manager tier is the growth engine -- these managers grow into larger funds.

### Competitive Landscape Summary

| Competitor | Strength | Weakness (Maverick's Opening) |
|-----------|----------|------------------------------|
| **Affinity** ($125-200/user/mo) | Dominant CRM, MCP server | NOT an AI platform; AI is bolt-on via MCP to external LLMs |
| **Harmonic** | Deep sourcing database (30M+ cos) | Sourcing only; no diligence, memos, or ops |
| **Standard Metrics** | Portfolio monitoring + AI Analyst | Narrow focus; no sourcing or deal flow |
| **PitchBook** ($12-70K/yr) | Deepest data | Expensive, not AI-native, no workflow automation |
| **Granola** ($1.5B) | Meeting notes + privacy | Single use case; no deal or portfolio context |
| **Rowspace** ($50M from Sequoia) | Enterprise data workflows | Targets mega-funds ($100B+ AUM); not emerging managers |
| **Generic LLMs** (Claude/ChatGPT) | Flexible, powerful, cheap | No persistent deal context, no integrations, no compliance |
| **Hanover Park** | $27M Series A (March 2026), AI-native fund admin, $15B AUA, led by Emergence Capital. Growing from $1B to $15B AUA in 12 months. | New entrant; fund admin only, no sourcing or deal flow |

### The Maverick Differentiation Thesis

**Maverick should be the AI-native operating system for emerging and mid-market VC firms ($20M-$500M AUM) that:**
1. Connects to their existing tools (Affinity, PitchBook, email) via MCP and APIs
2. Provides persistent deal and portfolio context that generic LLMs lack
3. Automates the quarterly reporting nightmare that 95% still do in Excel
4. Delivers AI features with full explainability and privacy guarantees
5. Is priced for the emerging manager market (where Rowspace and Juniper Square won't go)
6. Cannot be replicated by a weekend of vibe coding (because of integrated data pipelines and compliance)

---

## Sources

- [Affinity: 10 AI Tools for VC Firms in 2026](https://www.affinity.co/guides/vc-ai-tools)
- [Affinity MCP Server Beta](https://www.affinity.co/blog/affinity-mcp-server-beta)
- [Affinity: Private Capital Predictions 2026](https://www.affinity.co/report/affinity-predictions-report)
- [HBR: How Generative AI Is Reshaping Venture Capital](https://hbr.org/2025/11/how-generative-ai-is-reshaping-venture-capital)
- [PortfolioIQ: Definitive VC Tech Stack 2026 (500+ Tools)](https://portfolioiq.ai/blog/vc-tech-stack-2026)
- [Standard Metrics: Top AI-Powered VC Tech Stack Tools 2026](https://standardmetrics.io/library/the-top-ai-powered-vc-tech-stack-tools-in-2026/)
- [VNTR: VC Tech Stack 2025](https://www.vntr.vc/blog/the-vc-tech-stack-2025-tools-that-power-modern-venture-capital)
- [Blue Future Partners: VC Tech Stack Survey](https://medium.com/blue-future-partners/whats-your-vc-s-tech-stack-results-from-a-survey-of-early-stage-venture-capital-funds-7ddbeaf987c0)
- [Upstarts Media: VC Firms Build AI Tools](https://www.upstartsmedia.com/p/deep-dive-vc-firms-build-ai)
- [51 Degrees: How VC Firms Use AI and Data Science](https://www.51d.co/how-venture-capital-firms-are-using-ai/)
- [Bloomberg: VC Firms Grab AI Talent](https://www.bloomberg.com/news/newsletters/2026-02-20/vc-firms-grab-ai-talent-to-boost-their-investment-bets)
- [Scale VP: Is AI Coming for VC Jobs?](https://www.scalevp.com/insights/is-ai-coming-for-vc-jobs-we-hope-so/)
- [Alter Domus: VC Operational Challenges](https://alterdomus.com/insight/venture-capital-operational-challenges/)
- [VC Lab: AI for VC](https://govclab.com/2025/04/12/ai-for-vc/)
- [VC Lab: VC Back Office Solutions](https://govclab.com/2025/08/14/vc-back-office-solutions/)
- [Retool: Build vs Buy Report 2026](https://retool.com/blog/ai-build-vs-buy-report-2026)
- [SaaS CFO: The SaaSpocalypse](https://www.thesaascfo.com/the-saaspocalypse-ai-agents-vibe-coding-and-the-changing-economics-of-saas/)
- [Bessemer: State of AI 2025](https://www.bvp.com/atlas/the-state-of-ai-2025)
- [OECD: AI Firms Capture 61% of Global VC in 2025](https://www.oecd.org/en/about/news/announcements/2026/02/ai-firms-capture-61-percent-of-global-venture-capital-in-2025.html)
- [Menlo Ventures: State of Generative AI 2025](https://menlovc.com/perspective/2025-the-state-of-generative-ai-in-the-enterprise/)
- [Fortune: Rowspace Raises $50M Led by Sequoia](https://fortune.com/2026/02/25/rowspace-sequoia-ai-financial-platform-private-equity-investment-venture-capital/)
- [TechCrunch: Granola Raises $125M at $1.5B Valuation](https://techcrunch.com/2026/03/25/granola-raises-125m-hits-1-5b-valuation-as-it-expands-from-meeting-notetaker-to-enterprise-ai-app/)
- [SignalFire: Beacon AI](https://www.signalfire.com/beacon-ai)
- [SignalFire: VC GPT and LLMs](https://www.signalfire.com/blog/signalfire-beacon-ai)
- [SuperScout: VC Associate Guide](https://superscout.co/guide/associate)
- [SuperScout: GP Guide](https://superscout.co/guide/general-partner)
- [Papermark: VC LP Reporting 2026](https://www.papermark.com/blog/venture-capital-lp-reporting)
- [Standard Metrics: VC Fund Management Software 2025](https://standardmetrics.io/vc-fund-management-software-in-2025-the-complete-buyers-guide/)
- [Product Market Fit: 10 Prompts by the AI Agent that Deployed $200M](https://www.productmarketfit.tech/p/is-vc-dead-10-prompts-by-the-ai-agent)
- [TechCrunch: Investors Predict AI Labor Displacement 2026](https://techcrunch.com/2025/12/31/investors-predict-ai-is-coming-for-labor-in-2026/)
- [Bain Capital Ventures: VC Insights 2025 and 2026 Predictions](https://baincapitalventures.com/insight/vc-insights-2025-ai-trends-startup-growth-and-2026-predictions/)
