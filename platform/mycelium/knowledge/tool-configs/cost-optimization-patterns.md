---
id: tool-config-cost-optimization
category: tool-configs
discovered: 2026-04-06
last-validated: 2026-04-06
confidence: high
type: knowledge
source: maverick-market-research production runs — 3x cost reduction validated
distributed-to: []
effectiveness: null
tags: [cost, tokens, optimization, pipeline, multi-agent, react, context, input-tokens, output-tokens, budget, opus, sonnet]
relevant-when: building agent pipelines, optimizing LLM costs, seeing high token usage, designing multi-step workflows, comparing model costs
related: [pattern-research-driven-arch-decisions]
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# LLM Cost Optimization for Multi-Agent Pipelines

## What
Replace single long-running ReAct loops with multi-call pipelines that start fresh context per sub-task. Cuts costs 3x with same quality.

## Why
By turn 20, every LLM call replays 200K+ accumulated tokens. Before: 134 calls, 2M input tokens, $0.145/run. After: 179 calls, 692K input tokens, $0.051/run.

## Procedure
1. Identify if your pipeline exceeds 10 tool calls or 200K tokens of context growth -- if yes, split it
2. Break the workflow into discrete sub-tasks, each with a clear input/output contract
3. Implement each sub-task as a separate LLM call with fresh context (only pass in what that task needs)
4. Route inputs by type before processing:
   - Structured data (e.g., fund with portfolio page) --> direct scraping call
   - Unstructured data (e.g., family office) --> broader search call with multiple sources
5. For list-based work, search EACH item individually in its own call (60% of high-quality results come from per-item search)
6. Fetch full source pages for important items (not just search snippets -- captures 50% more data)
7. Track cost metrics for every run: input tokens, output tokens, tool calls, cost per unit of output (e.g., $/investor)
8. Compare against baseline after each change to validate improvement

## Pitfalls
- What breaks: Sub-tasks missing context they need. Detection: lower quality output than single-agent. Fix: pass explicit structured input to each sub-call, not just a prompt.
- What breaks: Not tracking per-run costs. Detection: no way to know if optimization helped. Fix: log input_tokens, output_tokens, total_cost for every call.
- What breaks: Using snippets instead of full fetches for key items. Detection: sparse data (e.g., 2-3 co-investors vs 4.5). Fix: always fetch full source for high-value items.

## Verification
- [ ] Input tokens per run dropped by at least 50% vs single-agent baseline
- [ ] Output quality (measured by data completeness) is equal or better
- [ ] Cost per unit of output is tracked and compared to baseline
- [ ] Each sub-call context is under 200K tokens

## Evidence
- maverick-market-research: 3x cost reduction validated in production
- Multi-call uses MORE tool calls (179 vs 134) but far fewer tokens
