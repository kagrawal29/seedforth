---
id: patterns-rule-builder-group-logic
category: patterns
type: knowledge
version: 1
discovered: 2026-04-09
last-validated: 2026-04-09
confidence: high
source: Pranav LangSmith traces 2026-04-07 — turns 13:56–14:02, repeated corrections, explicit frustration ("you fucked it up by confusing"); 6+ turns of back-and-forth
tags: [rule-builder, automation, triggers, or-logic, and-logic, groups, category-matching, conditions, workflow-automation]
relevant-when: building or explaining rule/automation builders, configuring trigger conditions with multiple categories, implementing equals/not-equals conditions in rule groups
related: []
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Rule Builder Group Logic: Within-Group = OR, Across-Groups = AND

## What
In Maverick's rule/automation builder, conditions within a single group use OR logic. Conditions across separate groups use AND logic. This distinction is critical and easy to confuse — getting it wrong breaks all rules.

## The Logic

| Structure | Operator | Use case |
|-----------|----------|----------|
| Multiple `equals` in ONE group | OR | "Match any of these categories" |
| `equals` conditions in SEPARATE groups | AND | Never do this for single-value fields |
| Multiple `not_equals` in separate groups | AND | "Exclude all of these categories" |

## Why This Matters
A thread always has exactly one category. So:
- `equals(A)` AND `equals(B)` in separate groups = impossible match (no thread can be both A and B simultaneously)
- `equals(A)` OR `equals(B)` within one group = correct: fires if category is A or B

The common mistake is "this rule should match category A and B" → putting them in separate groups → AND logic → zero matches ever. The user's original intent (match any of these) was correct; the confusion came from misapplying AND vs OR.

## How to Apply

### For inclusion rules (match any of several categories)
Put ALL `equals` conditions in ONE group:
```
Group 1 (OR):
  - category equals "Call Request"
  - category equals "Deck Request"
  - category equals "Q&A"
```
→ Fires when category is Call Request OR Deck Request OR Q&A

### For exclusion rules (block specific categories)
Put each `not_equals` in its OWN group:
```
Group 1: category not_equals "Not Interested"
Group 2: category not_equals "Not a Fit"
```
→ Fires when category is NOT "Not Interested" AND NOT "Not a Fit" (correct: both conditions must be true)

### Quick check when debugging a rule
1. Is it an `equals` rule? → All conditions must be in ONE group
2. Is it a `not_equals` rule? → Each exclusion gets its own group
3. Zero matches on a rule? → First suspect is `equals` conditions spread across groups (AND instead of OR)

## Evidence
- Pranav LangSmith traces 2026-04-07 (turns 13:56–14:02)
- 6+ turns of Claude giving wrong advice, then correcting; Pranav's original rules were correct from the start
- Explicit correction: "from the very first place, when I had created all rules, they were correct, and you fucked it up by confusing"
- This is a high-ROI T6 signal: repeated frustration from wrong AI guidance on rule logic
