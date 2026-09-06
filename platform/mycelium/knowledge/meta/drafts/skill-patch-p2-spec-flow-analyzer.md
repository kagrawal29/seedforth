# HOLD: spec-to-ship — Replace Phase 1 spec self-review with spec-flow-analyzer agent call

**Status:** HOLD — needs second signal  
**Proposed:** 2026-04-11  
**Source:** skill-feedback-proposals.md, P2  
**Promotion condition:** Second team member (beyond Ankit-S) successfully uses spec-flow-analyzer in a traced session, OR spec-flow-analyzer is defined as a standalone skill/agent in maverick-meta

---

## What

Replace the 7-item manual spec self-review checklist (Phase 1 NO-SKIP) with an automated `spec-flow-analyzer` subagent call that runs a 14-item validation checklist. Preserve the manual checklist as an Option B fallback for repos without the analyzer.

## Evidence

- **Skip rate**: 0/9 invocations showed evidence of running the manual spec self-review checklist (100% skip)
- **Explanation**: The v8 playbook (committed by Ankit-S to VC-AI-Associate repo) replaced the manual checklist with spec-flow-analyzer. Ankit-S trace (2026-04-11T07:55): *"I dispatched a spec-flow-analyzer agent (as the playbook recommends) to run the full 14-item Spec Validation Checklist against the spec. It returned PASS WITH FIXES — no blocking findings, 8 non-blocking findings. I applied all 8 fixes."*
- **Root cause found**: The 100% skip rate for spec_self_review IS EXPLAINED by this — in v8, the manual self-review checklist was replaced by the automated spec-flow-analyzer agent

## Why HOLD (not DISTRIBUTE)

**Adoption (0)**: Only 1 team member (Ankit-S) has used spec-flow-analyzer. Other 8 invocations skipped the manual checklist entirely (not by using the analyzer — just by skipping). MODE 2 rule: GAP proposals require 2+ independent signals before distributing.

**Risk (0)**: Option A introduces an undefined external component. If an agent reads "dispatch a spec-flow-analyzer subagent" in a repo that doesn't have it, the behavior is ambiguous (should it try to create the agent? skip Option A? fail?). Until spec-flow-analyzer is defined as a skill with a known contract, the Option A path creates confusion risk.

**Feedback agent note**: "needs coordination with VC-AI-Associate repo" and "Heimdall may want to spec out the spec-flow-analyzer agent contract before merging this."

## Score: 3/5 (Evidence 1, Unique 1, Actionable 1, Adoption 0, Risk 0) → HOLD

## Proposed Change (for reference when promoting)

```markdown
### Spec Validation [NO-SKIP]

**Option A (if spec-flow-analyzer available or if repo has playbook v5+):**
Dispatch a `spec-flow-analyzer` subagent with the spec. It runs the full validation checklist automatically. Apply all blocking findings before continuing. Non-blocking findings: apply or document why not.

**Option B (if no automated validator):**
- [ ] No placeholders (`[...]`, TBD, TODO)
- [ ] Every user story has Given/When/Then acceptance criteria
- [ ] Every user story is independently testable
- [ ] Every edge case has a named expected behavior
- [ ] Success criteria are measurable, not aspirational
- [ ] Existing patterns referenced (searched codebase for similar components)
- [ ] Boundaries section complete (Always / Never / Ask First)

### Phase 1.5 Exit Gate (if validator was run)
| Gate | Required |
|------|----------|
| Validator completed | Yes |
| Zero blocking findings | Yes |
| All fixes applied to spec | Yes |
| Human approved validated spec | **Human Touchpoint #1** |
```
