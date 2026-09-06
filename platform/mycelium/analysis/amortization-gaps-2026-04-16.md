# Mycelium Amortization Model — Gaps Analysis

**Date:** 2026-04-16
**Method:** Semantic graph queries via `./mycelium ask`, code review, memory log analysis
**Scope:** Mapping where the amortization model (author_cost_usd, fire_count, usage_cost, amortization_status) has gaps between design and implementation

## Summary

The Mycelium graph has a well-defined amortization concept but significant gaps between design and implementation. The graph KNOWS the amortization model conceptually but cannot answer concrete questions about which protocols are actually paying for themselves.

## What the Graph Knows

### Concepts (Well-Defined)

1. **concept-amortization** — "Economic lifecycle tracking: author cost, fire count, usage cost, amortization status (dead/un-amortized/amortizing/amortized)"
   - Status: Documented concept, order 40 in ontology
   - Confidence: High (semantic search returns 0.781-0.892 cosine on all amortization queries)

2. **concept-subagent** — "An autonomous LLM-backed agent dispatched to author cypher protocols. Carries model, token counts, cost, duration, and AUTHORED edges to the protocols and atoms it produced"
   - Status: Documented, understood
   - Key insight: "Every subagent invocation is first-class in the graph so mycelium cost can roll up spend by protocol, by model, by session"
   - Critical gap: This is stated as a design goal, NOT implemented

3. **concept-costestimate** — "Rollup node aggregating per-persona spend, run count, and average cost per run from historical subagent executions"
   - Status: Documented concept, order 41 in ontology
   - Implementation: CostEstimate nodes exist for 4 personas (cypher-author, density-auditor, install-scaffolder, narrator)
   - Gap: Cost data may not be flowing through correctly

4. **concept-persona** — "First-class subagent archetype with system prompt, model, cost budget, and wiring to Skills, Commands, TestCases"
   - Status: 4 Persona nodes seeded (cypher-author, density-auditor, install-scaffolder, narrator)
   - Fields defined: cost_budget_usd, usage_count, total_cost_usd, avg_tokens
   - Gap: These counters appear to be initialized to 0 and not being updated

### Data Layer (Partially Implemented)

**Seeded Fields:**
- Protocol nodes: `author_cost_usd`, `fire_count`, `total_usage_cost_usd`, `cost_per_use`, `amortization_status`
- Skill nodes: Same fields as Protocol
- CostEstimate nodes: `total_runs`, `total_cost_usd`, `avg_cost_per_run`, `last_updated`

**Backfill Logic (in persona-amortization-seed.cypher, lines 126-128):**
```cypher
MATCH (s:Subagent)-[e:AUTHORED]->(p:Protocol)
SET p.author_cost_usd = s.cost_usd
```

**Status Computation (lines 237-247):**
```cypher
WHEN p.fire_count = 0 THEN "dead"
WHEN p.fire_count < 10 THEN "un-amortized"
WHEN p.fire_count < 100 THEN "amortizing"
WHEN p.fire_count >= 100 THEN "amortized"
```

## Gaps Discovered (12 Total)

### Gap 1: Fire Count Bridging (CRITICAL)
**What the graph says it does:** Tracks fire_count on both Query nodes (from ask invocations) and Protocol nodes
**What's actually happening:** These are disconnected. Protocol.fire_count never increments.
**Evidence from memory:** "identified an amortization gap: `:Protocol.fire_count` not bridged to `:Query.fire_count`, causing all protocols to show status=dead despite active traces"
**Impact:** ALL 59 of 64 protocols (92%) show status=dead because their fire_count is 0, even though the underlying queries ARE firing
**Needed fix:** Add a periodic rollup that sums Query.fire_count for queries that invoke each protocol, OR wire Query→Protocol→CypherAtom chains directly

### Gap 2: No Protocol Invocation Tracking
**What should exist:** When a protocol runs, it should create an edge to the Protocol node
**What actually exists:** Protocols are invoked via bash/Cypher, no automatic linkage back to the Protocol node
**Design vs. Reality:** The design assumes "every invocation creates a signal that strengthens Protocol.fire_count"
**Missing:** Link from mycelium CLI (ask command, run command) back to Protocol invocation

### Gap 3: Author Cost Not Backfilled from All Sources
**What the model assumes:** `Protocol.author_cost_usd` is populated from `Subagent.cost_usd` via AUTHORED edges
**What's actually happening:** Only works for explicitly AUTHORED relations
**Gap:** Many protocols are not authored via Subagent nodes — they're hand-written or bulk-loaded from .cypher files
**Impact:** author_cost_usd = 0.0 for most protocols, breaking cost_per_use calculations

### Gap 4: Cost Per Use Computation Never Triggers
**Formula (line 254):** `cost_per_use = author_cost_usd / fire_count`
**Problem:** Since fire_count stays at 0 and author_cost_usd is 0, cost_per_use is always 0
**Impact:** Cannot answer "which protocols have paid for themselves" or "which are wasting investment"

### Gap 5: No CostEstimate Updates on Actual Runs
**Design:** CostEstimate rollup nodes compute persona spend from historical subagent executions
**Reality:** Computed once at seed time (lines 134-196), never updated
**Missing:** Periodic job that updates CostEstimate.total_runs, total_cost_usd, avg_cost_per_run
**Cadence needed:** Every heartbeat or every 10 ticks (per proposed polyrhythmic design)

### Gap 6: Total LLM Cost Not Aggregated
**What the model defines:** Costs should roll up by persona, by model, by session
**What exists:** Individual Subagent.cost_usd fields scattered across time
**What's missing:** 
- No sum aggregate of all authoring costs
- No breakdown by model (Haiku vs Sonnet cost curves)
- No "session" concept linking related work
**Impact:** "What is the total LLM cost invested in authoring protocols?" returns a concept definition, not a number

### Gap 7: Dead Protocol Economics Not Modeled
**Design statement:** "what is the cost of a dead protocol that never fires?"
**Graph answer:** Should return "author_cost_usd and nothing else is recouped"
**Problem:** Fire_count=0 but author_cost_usd is also 0 or missing, so the answer is unsatisfying
**Missing:** Explicit cost tracking for protocols that were authored (cost spent) but never invoked

### Gap 8: Amortization Status Thresholds Are Arbitrary
**Current thresholds (lines 240-245):**
- fire_count < 10: un-amortized
- 10-99: amortizing
- >= 100: amortized
**Problem:** These thresholds have no economic justification
**Should be:** `amortization_status = if fire_count * cost_per_use >= author_cost_usd then 'amortized' else ...`
**Impact:** Status is organizational guess, not economic fact

### Gap 9: No Subsystem Cost Aggregation
**Query asked:** "which subsystems have the best amortization ratio?"
**Graph answer:** Returns generic concepts about communities and protocols
**Missing:** 
- Subsystem := group of related Protocol nodes
- cost_amortization_ratio := sum(protocol.cost_per_use) / sum(protocol.author_cost_usd)
- Ranking of subsystems by ROI
**Would require:** New aggregation layer on top of Protocol amortization

### Gap 10: Amortization Status Computation Not Integrated into Heartbeat
**Design:** "how should amortization status be computed end-to-end?"
**Graph answer:** Returns seed protocol with 1-time computation
**Reality:** Amortization status should be recomputed every heartbeat (current proposal: every 100 ticks)
**Missing from heartbeat phases 1-15:** Amortization recount is listed as needed but not yet scheduled

### Gap 11: Query Reuse Amortization Not Measured
**Design statement:** "cached queries amortize to 50x reduction (50M→1M tokens at 1,000 sessions) via query reuse"
**Graph tracking:** Query nodes have fire_count
**Missing:** 
- Link from Query.fire_count to token savings metric
- No measurement of "cache hit reduced tokens from X to Y"
- No rollup of total token amortization across all cached queries
**Impact:** Can't answer "how much have cached queries saved us?"

### Gap 12: Walk-Counter Not Applied to Cost Edges
**Current state:** walk-counter is applied to some edges but not to :AUTHORED or cost-related edges
**Impact:** Can't weight cost propagation by usage patterns
**Design gap:** "no walk-counter on cosine edges" (from memory)

## Test Results: What Couldn't Be Answered

Running the 10 queries via `./mycelium ask`:

| # | Query | Result |
|----|-------|--------|
| 1 | "what is the amortization model and how does it work" | ✓ Answered (concept definition) |
| 2 | "which protocols are amortizing and paying back their cost" | ✗ Returned concept instead of data |
| 3 | "what is the average cost per use across all protocols" | ✗ Returned concept, no aggregation |
| 4 | "which cypher atoms have the highest fire count" | ✗ Returned concept (Query node structure), no rankings |
| 5 | "what nodes are missing author cost tracking" | ✗ Returned healing protocol, not the gap itself |
| 6 | "how do we measure if a protocol has paid for itself" | ✓ Partial (got liveness protocol, could infer approach) |
| 7 | "what is the total LLM cost invested in authoring protocols" | ✗ Returned concept, no sum |
| 8 | "which subsystems have the best amortization ratio" | ✗ Returned concepts, no ratios |
| 9 | "what is the cost of a dead protocol that never fires" | ✓ Partial (got decay protocol, not cost model) |
| 10 | "how should amortization status be computed end to end" | ✓ Partial (returned seed protocol structure) |

**Score: 3/10 fully answered, 3/10 partial answers, 4/10 failures**

## What Works (Self-Knowledge)

The graph DOES know:
- The amortization concept is defined
- Persona nodes exist for 4 key subagent archetypes
- Protocol fields are seeded with cost tracking
- Status thresholds are defined (even if arbitrary)
- Query fire_count IS being incremented (from mycelium ask calls)
- Heartbeat has decay/prune/propagation phases
- The system can detect when protocols are "dead" (fire_count=0)

## The Core Problem

**The amortization model is documented as a design goal but only partially implemented as a data layer.** The graph has vocabulary (concepts) and schema (fields on Protocol/Skill/CostEstimate nodes) but is missing:

1. **Active measurement:** Fire count for protocols never increments because protocol invocations don't create edges
2. **Cost flow:** Author costs don't backfill for bulk-loaded protocols, and runtime costs don't accumulate
3. **Aggregation:** No periodic jobs to roll up costs to persona, subsystem, or system level
4. **Feedback loop:** Amortization status is computed once, never recomputed as usage changes
5. **Economic reality:** Thresholds and cost models don't match actual project economics

## Recommended First Steps (Priority Order)

### Priority 1: Unlock Amortization Measurement
- Wire mycelium CLI invocations back to Protocol nodes (every `ask`, `run`, etc. creates :INVOKES→Protocol edge)
- Add fire_count increment to every protocol execution
- Implement periodic CostEstimate.total_cost_usd update from Subagent nodes

### Priority 2: Fix Cost Visibility
- Backfill author_cost_usd from git history or manual entry for bulk-loaded protocols
- Implement economic amortization_status formula instead of arbitrary thresholds: `if fire_count > 0 and (fire_count * cost_per_use >= author_cost_usd) then 'amortized'`

### Priority 3: Complete the Loop
- Add amortization recount to heartbeat phases (every 100 ticks per polyrhythmic design)
- Implement subsystem-level cost aggregation (Protocol groups → subsystem ROI rankings)
- Measure query reuse token savings (Query.fire_count × model_token_savings)
