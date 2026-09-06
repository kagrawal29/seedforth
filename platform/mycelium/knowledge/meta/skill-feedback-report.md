# Skill Feedback Report — 2026-04-11

## Summary

- **Traces analyzed**: 105 (from 6 team members, 2026-04-10T13:56 to 2026-04-11T16:55)
- **Explicit skill invocations found**: 2 (`/spec-to-ship` ×2)
- **Strong implicit invocations found**: 9 (spec-to-ship), 0 (fix-workflow), 0 (architecture-validation)
- **Deviation patterns detected**: 8
- **Patches proposed**: 5

---

## Per-Skill Analysis

### /spec-to-ship

**Invocations:** 9 (2 explicit `/spec-to-ship`, 7 strong implicit — multiple phase keywords)
- Sahiram ×2 (2026-04-10T15:11, 2026-04-10T16:42)
- Abhishek ×3 (2026-04-11T13:13, 13:21, 13:33)
- Ankit-S ×3 (2026-04-11T07:46, 07:55, 08:09)
- Kshitiz ×1 (2026-04-11T16:41)

**Completion rate:** 3/9 reached Phase 5 (33%)

**Step skip rates across 9 invocations:**

| Step | Found | Skip Rate | Flag |
|------|-------|-----------|------|
| read_learnings | 0/9 | 100% | ★ ALWAYS SKIPPED |
| spec_self_review | 0/9 | 100% | ★ ALWAYS SKIPPED |
| learning_capture | 0/9 | 100% | ★ ALWAYS SKIPPED |
| completion_gate | 0/9 | 100% | ★ ALWAYS SKIPPED |
| subagents_used | 1/9 | 89% | ⚠ HIGH SKIP |
| phase_0_context_load | 3/9 | 67% | ⚠ HIGH SKIP |
| on_feature_branch | 3/9 | 67% | ⚠ HIGH SKIP |
| human_approval | 3/9 | 67% | ⚠ HIGH SKIP |
| tdd_test_first | 3/9 | 67% | ⚠ HIGH SKIP |
| phase_5_finish | 3/9 | 67% | ⚠ HIGH SKIP |
| spec_compliance | 4/9 | 56% | |
| phase_4_verify | 5/9 | 44% | |
| phase_2_plan | 7/9 | 22% | |
| phase_3_implement | 7/9 | 22% | |
| phase_1_brainstorm | 8/9 | 11% | |

**Key deviations:**

1. **read_learnings — 100% skip**: Not a single invocation read `docs/learnings.md` before starting. Phase 0 itself is skipped 67% of the time, so this gate never fires. Evidence: 0/9 invocations.

2. **spec_self_review — 100% skip**: The 7-item spec self-review checklist (Phase 1 NO-SKIP) is never executed as written. However — see critical finding below.

3. **learning_capture + completion_gate — 100% skip**: Completion gates and learning capture never happen. Phase 5 only reached 3/9 times, and even those didn't fill the gate.

4. **CRITICAL: Playbook version drift — SKILL.md is 6 versions behind reality**
   - Evidence: Ankit-S committed `docs/workflow/spec-to-ship-playbook-v8.md` to the VC-AI-Associate repo
   - The SKILL.md references playbook v2. The team is actively working from v8.
   - v8 adds: **Phase 1.5** (spec validation gate between brainstorm and planning) and a **`spec-flow-analyzer` subagent** that runs a 14-item automated spec validation checklist
   - The spec_self_review 100% skip is EXPLAINED by this — in v8, the manual self-review checklist was replaced by the automated spec-flow-analyzer agent
   - Ankit-S trace (2026-04-11T07:55): *"I dispatched a spec-flow-analyzer agent (as the playbook recommends) to run the full 14-item Spec Validation Checklist against the spec. It returned PASS WITH FIXES — no blocking findings, 8 non-blocking findings. I applied all 8 fixes."*
   - This is the highest-value finding: the team organically evolved a better solution to the spec_self_review NO-SKIP, and it's not reflected in the skill.

5. **TDD — 67% skip**: Test-first discipline is present in fewer than 1/3 of invocations. Difficult to determine what fraction are legitimately skipped (purely structural changes) vs. silently dropped.

**Avg deviation score**: 0.61 (0.0 = perfect adherence, 1.0 = complete deviation)

---

### /fix-workflow

**Explicit invocations:** 0
**Implicit invocations (strong track-selector signals):** 0

**Non-invocation gap analysis:**
10 traces contained 3+ bug/fix keywords (bug, broken, error, fix, issue, regression). On inspection of the actual user messages:

- Most were debugging sessions or investigations *within* spec-to-ship work (not standalone bug fixes)
- Abhishek traces: investigating sync conflict behavior, planning empirical tests
- Sahil traces: wave implementation planning (feature work with error words, not bug fixing)
- None met the fix-workflow trigger condition: "user reports a bug, asks to fix something, or a code review finding needs resolution" as a standalone request

**Assessment**: No confirmed fix-workflow violations in this window. The 0 invocation count likely reflects the team's current focus on spec/build work rather than trigger narrowness.

---

### /architecture-validation

**Explicit invocations:** 0
**Implicit invocations**: 5 traces with clear architecture signals (arch decisions being made)

**Step adherence across 5 traces:**

| Person | Time | Steps Present | Steps Absent |
|--------|------|--------------|-------------|
| Sahiram | 2026-04-11T05:37 | present_status_table | check_existing, research_agents, social_media, walk_one_at_a_time, update_docs, terminology |
| Sahiram | 2026-04-10T16:42 | deploy_research_agents, terminology_pass | check_existing, status_table, social_media, walk_one_at_a_time, update_docs |
| Sahil | 2026-04-11T11:38 | check_existing_decisions | status_table, research_agents, social_media, walk_one_at_a_time, update_docs, terminology |
| Sahil | 2026-04-11T11:27 | deploy_research_agents | check_existing, status_table, social_media, walk_one_at_a_time, update_docs, terminology |
| Pranav | 2026-04-10T17:45 | check_existing_decisions | status_table, research_agents, social_media, walk_one_at_a_time, update_docs, terminology |

**Key deviations:**

1. **Partial execution pattern**: Every team member executes 1-2 steps of the skill in isolation rather than the full workflow. Nobody chains the full sequence.

2. **social_media_verification — 0% adherence**: The practitioner verification step (Twitter/X, Reddit) is never performed. 0/5 traces.

3. **real-time doc updates — 0% adherence**: No traces show decisions being recorded to architecture docs during the session.

4. **Non-invocation**: Arch decisions are being made but without invoking the skill. Users are picking individual steps (deploy a research agent, check knowledge base) without the structured workflow.

**Assessment**: This skill is being used as a loose inspiration rather than an executed workflow. The checklist structure may not be surfacing strongly enough to enforce sequencing.

---

## Patch Proposals

See `skill-feedback-proposals.md` for full proposal text.

| # | Skill | Pattern | Proposal |
|---|-------|---------|----------|
| P1 | spec-to-ship | Playbook v8 drift | Update SKILL.md to reference v8 and add Phase 1.5 |
| P2 | spec-to-ship | spec_self_review 100% skip | Replace manual checklist with spec-flow-analyzer call |
| P3 | spec-to-ship | read_learnings 100% skip | Move learnings read to pre-flight, before Phase 0 context |
| P4 | spec-to-ship | completion_gate 100% skip | Simplify gate — remove repetitive fields, reduce friction |
| P5 | architecture-validation | social_media_verification 0% | Make it an explicit subagent call, not a guideline |

---

## Non-Invocation Gaps

### fix-workflow
No confirmed gaps found in this 2-day window. Team is primarily in spec/build mode, not bug-fix mode. Recommend re-running analysis after next round of bug-fix work lands.

### architecture-validation
5 sessions where arch decisions were made without the skill. Pattern: teams are picking individual steps (research agents, knowledge base check) but not running the full workflow. Root cause likely: the skill's checklist format doesn't enforce sequencing — each item feels independently invokable.

---

## Skill Metrics

```yaml
spec_to_ship:
  invocation_count: 9
  completion_rate: 33%   # reached Phase 5
  step_skip_rates:
    read_learnings: 100%
    spec_self_review: 100%
    learning_capture: 100%
    completion_gate: 100%
    subagents_used: 89%
    phase_0_context_load: 67%
    human_approval: 67%
    tdd_test_first: 67%
    phase_5_finish: 67%
    spec_compliance: 56%
    phase_4_verify: 44%
    phase_2_plan: 22%
    phase_3_implement: 22%
    phase_1_brainstorm: 11%
  reclassification_rate: 0%  # no mid-execution track changes detected
  avg_deviation_score: 0.61
  critical_finding: "SKILL.md references v2, team uses v8. Phase 1.5 + spec-flow-analyzer exist in v8 but not in skill."

fix_workflow:
  invocation_count: 0
  completion_rate: N/A
  avg_deviation_score: N/A
  note: "No confirmed invocations in 2-day window. Team in spec/build phase, not bug-fix mode."

architecture_validation:
  invocation_count: 5  # implicit only, 0 explicit
  completion_rate: 0%  # no invocations completed the full workflow
  step_skip_rates:
    social_media_verification: 100%
    real_time_doc_updates: 100%
    walk_through_one_at_a_time: 100%
    terminology_pass: 80%
    deploy_research_agents: 60%
    check_existing_decisions: 40%
  avg_deviation_score: 0.78
```
