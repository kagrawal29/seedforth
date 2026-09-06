# HOLD: architecture-validation — Replace social media guideline with explicit mandatory agent call

**Status:** HOLD — solution untested, cost concern  
**Proposed:** 2026-04-11  
**Source:** skill-feedback-proposals.md, P5  
**Promotion condition:** At least 2 team members successfully run a dedicated adversarial social verification agent and report meaningful findings from it (i.e., practitioner experience that wasn't in official docs). Alternatively: add "skip if low-stakes" caveat before distributing.

---

## What

Replace the current social media verification sub-bullet (inside research agent instructions) with a dedicated mandatory "practitioner verification agent" that has an explicitly adversarial prompt — searching Twitter/X, Reddit, HN, engineering blogs for real production failures and anti-patterns.

## Evidence

**Problem is well-evidenced (3 independent signals):**
- Sahiram (2026-04-10T16:42, 2026-04-11T05:37): deploys research agents without social verification step
- Sahil (2026-04-11T11:27, 11:38): deploys research agents without social verification step  
- Pranav (2026-04-10T17:45): checks existing decisions without social verification step
- **0/5 arch sessions** showed Twitter/Reddit/forum searches for production experience

**Root cause**: "Include social media verification" as a sub-bullet inside research agent instructions gets interpreted as part of the same "answer the question" goal. Official docs answer questions faster. The social step is structurally subordinate and agents drop it.

## Why HOLD (not DISTRIBUTE)

**Adoption (0)**: Nobody has run the proposed dedicated adversarial agent. We have evidence the guideline-as-sub-bullet doesn't work, but no evidence the mandatory-separate-agent approach does. These are different interventions.

**Risk (0)**: Adding a mandatory separate agent per OPEN decision increases cost and time per arch session. The feedback agent flagged: "could increase cost and time for large arch sessions with many open items." No data exists on whether this cost is justified by the quality improvement. Distributing an untested mandatory cost increase could harm team throughput.

**MODE 2 rule**: Solution has 0 independent signals. The PROBLEM has 3 signals; the SOLUTION needs validation.

## Score: 3/5 (Evidence 1, Unique 1, Actionable 1, Adoption 0, Risk 0) → HOLD

## Proposed Change (for reference when promoting)

```markdown
- [ ] **Practitioner verification agent** [NO-SKIP for any OPEN decision]: Deploy a dedicated agent whose sole job is finding real-world production experience. Prompt it explicitly:
  > "Search Twitter/X, Reddit (r/devops, r/aws, relevant subreddits), Hacker News, and engineering blogs for people who have used [technology] in production. What problems did they hit? What were the failure modes? What would they do differently? Ignore official documentation entirely."
  
  This agent is separate from the technology/hosting research agents. Its job is adversarial — find what the docs hide.
  
  _Skip this step only if the decision is explicitly low-stakes (dev tooling, test utilities, local setup)._
```

## What Would Promote This

1. One team member runs the adversarial agent and finds something that changes the recommendation (not in official docs)
2. Report the outcome via `/report` — what did the agent find? Did it change the decision?
3. Second team member does the same
4. If both find value → promote P5 from drafts to the skill
