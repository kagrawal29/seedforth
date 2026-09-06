## Evaluation — 2026-04-12 (cycle 9: blocker resolution, no new synthesis)

**Mode:** Maintenance-only. Synthesis agent failed (Invalid API key at `2026-04-12T10:08:11Z`). No new knowledge entries exist since last evaluation (788a0aaa). MODE 2 applied: reviewed held drafts for promotion; applied two carry-forward pre-dist blockers.

### New Entries: None

No new synthesis entries to evaluate. Synthesis failure logged in `knowledge/meta/traces/synthesis-latest.log`.

### Held Drafts Re-evaluated

| Draft | Hold Condition | Evidence in 2026-04-12 signals | Decision |
|---|---|---|---|
| P2: spec-flow-analyzer (spec-to-ship) | Second team member uses spec-flow-analyzer in traced session | 2026-04-12 signals: only Ankit-S trace (2026-04-11T07:55) appears — same person, same session as original signal | **REMAINS HOLD** |
| P5: adversarial social agent (arch-validation) | 2+ team members run dedicated adversarial social verification agent | Sahiram trace 2026-04-10T10:41 shows "social media agent" running, but: (a) predates P5 proposal, (b) likely current sub-bullet behavior not new dedicated agent, (c) need 2 independent members | **REMAINS HOLD** |

### Blocker Resolutions Applied

| Blocker | Source | Fix Applied | Carry-forward since |
|---|---|---|---|
| BLOCKER 1: `cypher-native.md` contradicts `meta-learnings.md` | Pre-dist Audit 5–6 | Added `**Scope:**` qualifier to `cypher-native.md` Before Every Read section: rule now explicitly excludes external repo reads, resolving the contradiction | Audit 5 (2026-04-11) |
| BLOCKER 2: `hook-pattern-matching.md` misplaced in `distribution/shared-rules/` as a rule | Pre-dist Audits 3–6 | Moved to `knowledge/tool-configs/hook-pattern-matching.md` — removed from mandatory distribution path | Audit 3 (2026-04-10) |

**Both blockers resolved.** Pre-distribution audit should now clear these two items on next run.

### Scoring Rationale for Held Drafts

#### P2: spec-flow-analyzer — REMAINS HOLD (3/5)
- **Evidence (1):** Ankit-S clearly used spec-flow-analyzer (2026-04-11T07:55) — but this is the SAME signal from cycle 8. No new independent signal from another team member.
- **Hold condition not met:** Need one additional team member beyond Ankit-S. Promotion condition from draft file: "Second team member (beyond Ankit-S) successfully uses spec-flow-analyzer in a traced session, OR spec-flow-analyzer is defined as a standalone skill/agent."
- Checking maverick-meta 2026-04-12 commits: graph CLI NLQuery work only, no spec-flow-analyzer definition committed.

#### P5: adversarial social verification — REMAINS HOLD (3/5)
- **Sahiram trace context:** The "social media agent came back with solid practitioner findings" at 2026-04-10T10:41 (Sahiram section, lines 629–635 of 2026-04-12 LangSmith signals) is from BEFORE P5 was proposed and is likely architecture-validation's existing social sub-bullet working, not a new dedicated adversarial agent. The problem P5 identifies (agents dropping the social step) is that it works sometimes but unreliably — this trace could be one of the "sometimes it works" cases.
- **Hold condition not met:** Need "at least 2 team members successfully run a dedicated adversarial social verification agent." We have 0 confirmed instances of the PROPOSED intervention (dedicated mandatory separate agent with adversarial prompt).
- **Note for promoter:** If the spec-guide-research-synthesis session (Sahiram, 2026-04-10) used a dedicated social agent with an adversarial prompt, that would count as 1 of 2 needed. Look for: does the session explicitly launch a separate social-verification subagent, or does it just mention social media findings inline?

### What Should Run Next Cycle

1. **Synthesis must re-run** — 10+ technical commits in maverick-meta (graph CLI NLQuery, semantic routing, decipher mode) represent significant architectural knowledge that hasn't been synthesized. The synthesis agent needs a valid API key.
2. **Lint orphans**: 4 entries flagged in lint report (spec-to-ship-v8-superpowers, doc-to-graph-llm-boundary, graph-native-identity, vibe-coding-threat-assessment) have no cross-references. These were distributed in cycle `7fbb60e3`. Cross-link them or let the synthesis agent add `related:` pointers on next run.
3. **Pre-dist audit**: Should now clear 2 of 3 previous blockers. Run again to confirm before next distribution cycle.

**Total: 0 new distribute, 0 new hold, 0 discard, 2 blockers resolved**

---

## Evaluation — 2026-04-11 (cycle 8: skill-feedback commit 3a75c0e)

Evaluated 5 skill patch proposals from skill-feedback agent. Source: commit `3a75c0e` ("auto-skill-feedback: 2026-04-11 — 9 invocations analyzed, 5 patches proposed"). Signal basis: 105 LangSmith traces (6 team members, 2026-04-10 to 2026-04-11), 9 spec-to-ship invocations (Sahiram ×2, Abhishek ×3, Ankit-S ×3, Kshitiz ×1), 5 architecture-validation implicit invocations (Sahiram ×2, Sahil ×2, Pranav ×1). All 5 proposals are skill modification patches — MODE 2 (feedback changes), not MODE 1 (new synthesis entries).

### Skill Patch Proposals

| Proposal | Evidence | Unique | Actionable | Adoption | Risk | Total | Decision |
|---|---|---|---|---|---|---|---|
| P1: spec-to-ship version v2→v8 reference | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| P2: spec-to-ship spec-flow-analyzer Phase 1 | 1 | 1 | 1 | 0 | 0 | 3 | HOLD |
| P3: spec-to-ship learnings.md pre-flight | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| P4: spec-to-ship simplify completion gate | 1 | 1 | 1 | 0 | 1 | 4 | DISTRIBUTE |
| P5: architecture-validation social media agent | 1 | 1 | 1 | 0 | 0 | 3 | HOLD |

**Total: 3 distribute, 2 hold, 0 discard**

---

### Scoring Rationale

#### P1: spec-to-ship version reference v2→v8 — 5/5 DISTRIBUTE

- **Evidence (1):** Ankit-S committed `docs/workflow/spec-to-ship-playbook-v8.md` to VC-AI-Associate repo (2026-04-11). Ankit-S trace (2026-04-11T07:55): Claude proactively dispatched spec-flow-analyzer "as the playbook recommends." The SKILL.md reference to `spec-to-ship-playbook-v2.md` is a factual error — the team is 6 versions ahead.
- **Uniqueness (1):** Corrects a stale pointer. The v8 playbook adds Phase 1.5 + spec-flow-analyzer — substantively different from v2.
- **Actionability (1):** Direct behavior change — Claude will now read the correct (evolved) playbook before starting. "Or the highest-numbered version present" future-proofs against v9, v10, etc.
- **Adoption (1):** Ankit-S has already organically adopted v8. This patch aligns the skill with reality.
- **Risk (1):** The "if available" clause (now "if available in the current repo") makes it contingent. Repos without any playbook file: skill's built-in phases apply. Repos with v8: get v8. Low risk.
- **Applied:** Updated frontmatter description (removed "v2"), updated body subtitle, combined with P3 into single "Before Starting [MANDATORY]" block.

#### P2: spec-to-ship spec-flow-analyzer Phase 1 replacement — 3/5 HOLD

- **Evidence (1):** 0/9 invocations ran the manual spec self-review. Explanation is clear: v8 replaced it with spec-flow-analyzer. Ankit-S trace provides the concrete v8 flow with outputs ("PASS WITH FIXES — 8 non-blocking findings applied").
- **Uniqueness (1):** Fundamentally changes Phase 1 behavior from 7-item manual checklist to automated agent call.
- **Actionability (1):** Would change how spec validation executes. Option A (automated) vs Option B (manual fallback) structure is clean.
- **Adoption (0):** Only 1 team member (Ankit-S) has used spec-flow-analyzer. Other 8 invocations skipped the checklist entirely (not because they used the analyzer — because Phase 1 itself was partially skipped). MODE 2 rule: solution requires 2+ independent signals.
- **Risk (0):** Option A introduces `spec-flow-analyzer` as an invocable component that isn't defined as a standalone skill/agent in maverick-meta. If Claude reads "dispatch a spec-flow-analyzer subagent" in a repo without it, behavior is ambiguous. The feedback agent itself flagged "needs coordination with VC-AI-Associate repo."
- **Hold file:** `knowledge/meta/drafts/skill-patch-p2-spec-flow-analyzer.md`
- **Promotion condition:** Second team member successfully uses spec-flow-analyzer in a traced session, OR spec-flow-analyzer is defined as a standalone skill.

#### P3: spec-to-ship learnings.md pre-flight — 5/5 DISTRIBUTE

- **Evidence (1):** 0/9 invocations read `docs/learnings.md`. Root cause identified: Phase 0 is skipped 67% of the time, and the learnings read lives inside Phase 0's required reads list. When Phase 0 is skipped, the read never fires. Structural problem, structural fix.
- **Uniqueness (1):** Moving the learnings read ABOVE Phase 0 (into "Before Starting") ensures it fires regardless of Phase 0 execution. Different placement = different behavior.
- **Actionability (1):** Clear mechanism — "Before Starting [MANDATORY — runs even if Phase 0 is skipped]" is an unambiguous hook. Claude will read learnings.md before any phase executes.
- **Adoption (1):** 4 team members used spec-to-ship in this window. All Phase 0 reads are already prescribed; this moves one read earlier. Low friction adoption.
- **Risk (1):** "If the file doesn't exist, skip this step" clause eliminates breakage in repos without `docs/learnings.md`. Purely additive — no existing behavior removed.
- **Applied:** Combined with P1 into single rewritten "Before Starting" block; learnings read is step 1, playbook read is step 2.

#### P4: spec-to-ship simplify completion gate — 4/5 DISTRIBUTE

- **Evidence (1):** 0/9 invocations filled the completion gate. Phase 5 reached only 3/9 times — and even those 3 didn't fill the gate. 100% skip across 4 different team members (Sahiram, Abhishek, Ankit-S, Kshitiz). This is multi-person evidence the current gate is too burdensome.
- **Uniqueness (1):** Compresses 9 fields to 5+1 optional. Removes EVIDENCE BASIS (moved to optional via RESIDUAL RISK) and collapses AGENT REVIEW into the VERIFICATION line.
- **Actionability (1):** Shorter gate = lower friction = higher completion rate. Current state is 0% completion. Any improvement is measurable.
- **Adoption (0):** No team member has completed the gate in either the current or simplified form. We don't know if simplification will actually drive completion, but the hypothesis is sound and the risk of being wrong is low (if teams still skip, we've lost nothing vs. current state).
- **Risk (1):** The condensed version retains all 5 critical verification areas: spec reference, plan reference, files changed, verification status, after-state. The removed fields (EVIDENCE BASIS, separate AGENT REVIEW path) were redundant with the review doc that Phase 4 already creates. RESIDUAL RISK promoted to optional (was required). Feedback agent noted EVIDENCE BASIS has value for high-risk features — addressed by keeping RESIDUAL RISK as the catch-all optional field.
- **Applied:** Simplified gate block in Phase 5.

#### P5: architecture-validation social media verification agent — 3/5 HOLD

- **Evidence (1):** 0/5 arch sessions performed practitioner verification. Three independent team members (Sahiram, Sahil, Pranav) all deployed research agents without the social media step. Root cause: social verification is a sub-bullet inside research agent instructions — it gets interpreted as part of the same "answer the question" goal and official docs win.
- **Uniqueness (1):** Converting from guideline-as-sub-bullet to mandatory-separate-agent with adversarial prompt is structurally distinct.
- **Actionability (1):** Explicit agent call with concrete adversarial prompt is more actionable than "include social media verification" as a guideline.
- **Adoption (0):** Nobody has run the proposed dedicated adversarial social verification agent. Problem has 3 signals; proposed solution has 0 signals. We know the old approach fails; we don't know the new approach works.
- **Risk (0):** Adding a mandatory separate agent per OPEN decision increases cost per arch session. For large arch sessions with many open items, this could be significant. No data on cost/quality tradeoff. Feedback agent explicitly flagged "could increase cost and time."
- **Hold file:** `knowledge/meta/drafts/skill-patch-p5-arch-validation-social-agent.md`
- **Promotion condition:** 2 team members run dedicated adversarial social verification agent and report findings via `/report`. If practitioners surface issues not in official docs → promote. Also consider adding "skip if low-stakes" caveat before distributing.

---

## Evaluation — 2026-04-11 (cycle 7: post-commit cdcd3d9)

Evaluated 1 new rule from commit `cdcd3d9` ("Rule: don't read, ingest, think in graph" — kagrawal29 + Claude Opus 4.6). Signal sources: LangSmith 2026-04-11 (Kshitiz 100-turn session — Turn 6 09:19:24 caught himself about to define pipeline in Python), GitHub (Issue #44 closed "Refactor: reduce Python to I/O glue"), commits a4ad833 + e41da3d3 (Cypher-native pipeline + Invariant 6). No new knowledge/ entries — only the rule artifact.

### New Rules

| Entry | Evidence | Unique | Actionable | Adoption | Risk | Total | Decision |
|---|---|---|---|---|---|---|---|
| .claude/rules/cypher-native.md | 1 | 1 | 1 | 1 | 0 | 4 | DISTRIBUTE (with scope note) |

**Total: 1 distribute, 0 hold, 0 discard**

---

### Scoring Rationale

#### .claude/rules/cypher-native.md — 4/5 DISTRIBUTE

**Special rule check (2+ independent people):** YES — Kshitiz (Turn 6, 2026-04-11T09:19:24): "You're right. A Python file defining the pipeline is the same bypass we just identified — the pipeline structure itself should be graph topology." That's one live correction turn from Kshitiz. Pranav independently authored Issue #44 "Refactor: reduce Python to I/O glue — intelligence lives in graph" (closed, commit-backed). Two distinct people, same session window, same discovery. Threshold met.

- **Evidence (1):** Two independent people (Kshitiz live session Turn 6 + Pranav Issue #44) independently identified the pattern "don't bypass the graph." The pattern was operationalized as Invariant 6 and a 19-node PipelineStage topology. Specific commit SHA: e41da3d3 "Close 5 self-healing gaps + add Invariant 6 (Cypher-native)."

- **Uniqueness (1):** `asgard-graph.md` says "query the graph first" but doesn't prescribe the ingest workflow or give the `python3 scripts/ingest.py` command. `operating-model.md` describes the ingest pipeline but doesn't provide a behavioral hook for file reads. The 4-step "Before Every Read" protocol and the Cypher query substitution examples are new. ~70% net-new content vs existing rules.

- **Actionability (1):** The rule provides a specific command (`python3 scripts/ingest.py --type Document --label "..." --content "..."`) and 4 concrete Cypher queries that substitute for file reads. When injected, it would cause Claude to run graph queries before reaching for Read tool. Behavioral change is observable.

- **Adoption (1):** No effectiveness data yet (first rule of this behavioral class). Benefit of doubt: rules category has 100% distribute rate in this system.

- **Risk (0):** The "before reading ANY file" scope is too broad and creates a tension with `meta-learnings.md` which says "go read their actual repo, their actual code, their actual outputs" as an active directive for the meta agent. The two rules loaded together generate contradictory guidance:
  - meta-learnings: "go read code, commits, PRs — don't mistake trace mining for intelligence synthesis"
  - cypher-native: "don't read — ingest instead"
  
  This is high risk for confusion in synthesis sessions where meta-learnings is the intended guide. The rule is correct for SYSTEM STATE reads (config, pipeline stages, knowledge flat files when graph is available) but overclaims for EXTERNAL CONTENT reads (team repos, commits, research). A scope qualifier would eliminate the conflict.

  **Recommended future refinement:** Scope the rule to "Before reading files that describe system state (config, pipeline definitions, work items, flat-file knowledge)..." and exclude external repos/code from the ingest prescription.

  Rule is distributed as-is (total ≥ 3, 2-person threshold met) with this conflict flagged for the next refinement cycle.

---

## Evaluation — 2026-04-11 (cycle 6: post-synthesis)

Evaluated 11 new entries + 3 duplicate candidates from synthesis commit `00821ae` ("auto-synthesis: 2026-04-11 — 7 new entries, 3 updated, 1 rule"). Signal sources: LangSmith traces 2026-04-11 (Kshitiz 100 turns — Cypher-native pipeline build 09:16-09:31; Sahil 26 turns — competitive graph from research data; Ankit-S 82 turns — multi-fund hierarchy spec + v8 playbook; Sahiram 100 turns — enrichment pipeline + spec format debate; Abhishek 1 turn — spec isolation question). GitHub signals: commits aa9d42df + e69e2888 + 25590586 (MCP Streamable HTTP auth fix across 3 repos), commits 4186bc15 + fc7bc74a + d73296af (Cypher-native pipeline), issues #9 + #15 closed (MCP schema validation bug), issue #44 closed, commit 0101de17 (CLAUDE.md thin pointer). Research artifact signals: signals/artifacts/research-docs/ (March 29, 2026 deep research — vc-ground-truth.md + emerging-manager-playbook.md + post-investment-pain.md).

3 duplicate candidates (mcp-transport-streamable-http.md, claude-md-thin-pointer.md, spec-multi-spec-dependency.md) were identified but never committed by the synthesis agent — they were untracked at time of evaluation. No file operations required.

### New Knowledge Entries

| Entry | Evidence | Unique | Actionable | Adoption | Risk | Total | Decision |
|---|---|---|---|---|---|---|---|
| architecture/mcp-streamable-http-auth.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| architecture/cypher-native-pipeline.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| patterns/spec-tech-separation.md | 1 | 1 | 1 | 0 | 1 | 4 | DISTRIBUTE |
| patterns/lp-reporting-pain-profile.md | 1 | 1 | 1 | 0 | 1 | 4 | DISTRIBUTE |
| patterns/spec-isolation-principle.md | 1 | 1 | 1 | 0 | 1 | 4 | DISTRIBUTE |
| patterns/spec-to-ship-v8-superpowers.md | 1 | 1 | 1 | 0 | 1 | 4 | DISTRIBUTE |
| patterns/doc-to-graph-llm-boundary.md | 1 | 1 | 1 | 0 | 1 | 4 | DISTRIBUTE |
| patterns/graph-native-identity.md | 1 | 1 | 1 | 0 | 1 | 4 | DISTRIBUTE |
| patterns/vc-ai-market-ground-truth.md | 0 | 1 | 1 | 0 | 1 | 3 | DISTRIBUTE |
| patterns/emerging-manager-solo-gp-segment.md | 0 | 1 | 1 | 0 | 1 | 3 | DISTRIBUTE |
| patterns/vibe-coding-threat-assessment.md | 0 | 1 | 1 | 0 | 1 | 3 | DISTRIBUTE |

**Total: 11 distribute, 0 hold, 0 discard (3 duplicates were never committed)**

---

### Scoring Rationale

#### architecture/mcp-streamable-http-auth.md — 5/5 DISTRIBUTE (NEW)
- **Evidence**: Three commits across three repos (aa9d42df in maverick-meta, e69e2888 in VC-AI-Assoicate, 25590586 in maverick-market-research) all on 2026-04-11. Issues #9 (techqubit-pranav) and #15 (Ankitqubit) closed — two independent team members each hit the same MCP schema validation bug. The two-bug sequence (SSE + headers rejected → fix to Streamable HTTP; then token-in-URL → fix to Authorization header) is precisely documented with commit SHAs.
- **Uniqueness**: No existing entry covers MCP transport configuration, Streamable HTTP vs SSE distinction, or header-vs-URL authentication for Claude Code MCP servers.
- **Actionability**: Direct behavior change — without this, team members configuring `.mcp.json` would use SSE transport and hit schema validation failure, then expose token in URL. Both mistakes documented as explicit "Do NOT use" anti-patterns.
- **Adoption**: Architecture category 100% distribute rate. Two independent team members already hit and fixed this.
- **Risk**: Committed to all three repos, both issues closed. Security hygiene with no ambiguity. Low risk.

#### architecture/cypher-native-pipeline.md — 5/5 DISTRIBUTE (NEW)
- **Evidence**: Kshitiz LangSmith traces 2026-04-11 09:16-09:31 (100-turn session), commits 4186bc15 + fc7bc74a + d73296af, issue #44 closed. Turn 6 (09:19:24): "You're right. A Python file defining the pipeline is the same bypass we just identified." Turn 10 (09:16:26): "The pipeline has to run at zero LLM cost, otherwise it's not a nervous system, it's a billing event." Active demand signal answered: "How do we make the intelligence pipeline itself a graph structure — PipelineStage nodes holding Cypher queries as properties, with FLOWS_TO edges defining execution order?"
- **Uniqueness**: PipelineStage topology, Cypher-as-execution-logic pattern, and the Python-bypass anti-pattern are all new. Invariant 6 formally codified here.
- **Actionability**: Prevents the natural mistake of adding new pipeline stages in Python. Shows the correct graph-topology approach.
- **Adoption**: Single-person session, issue closed. Architecture category 100% distribute.
- **Risk**: Session-built, commit-backed, Invariant 6 formally adopted. Low risk.

#### patterns/spec-tech-separation.md — 4/5 DISTRIBUTE (NEW)
- **Evidence**: Sahiram LangSmith traces 2026-04-11 (turns 2, 5, 8-10) + 2026-04-10 (turns 8-10) — two independent sessions on the same debate. Research agent deployed against IEEE 29148, Karl Wiegers "Software Requirements", spec-kit. Active demand signal answered: "Is 'no technical detail in specs' a universal industry standard, or does it apply only to SRS documents?"
- **Uniqueness**: spec-reading-guides covers HOW to make tech readable; this covers WHETHER tech belongs in specs at all. Different question, different answer.
- **Actionability**: "Direct teammates to spec-kit and IEEE 29148 — the rule they're citing applies to SRS documents, not product feature specs." Resolves a recurring team debate with citable sources.
- **Adoption**: 0. No effectiveness data yet.
- **Risk**: Research-validated against primary sources. Two sessions, same conclusion. Low risk.

#### patterns/lp-reporting-pain-profile.md — 4/5 DISTRIBUTE (NEW)
- **Evidence**: Source: signals/artifacts/research-docs/lp-reporting-workflow.md + post-investment-pain.md (March 29 deep research). Quantified survey data: 70% GPs cite LP reporting as top challenge, 95% use Excel, 20-40 hours per quarter. Active GitHub issues #13 (LP transparency dashboard) and #10 (LP Narrative Letter Writing) both open in VC-AI-Assoicate. Evidence scored 1 for practitioner-level quantified data from named sources (Standard Metrics survey, ILPA). Adoption scored 0.
- **Uniqueness**: `lp-reporting-pain-map.md` (not committed — was a parallel synthesis artifact) had Twitter-specific practitioner vocabulary evidence. This entry has survey quantification and GP/LP demand contrast. Different evidence base. Note: both were synthesized simultaneously; only this one was committed. ~95% net-new vs research-to-product-pipeline.md.
- **Actionability**: "Quarter-end to LP update in <1 week" as killer stat. GP wants AI-drafted narrative; LP wants brevity and honesty — these are different problems requiring different features. "Maverick V2 highest-ROI feature" is a direct prioritization recommendation.
- **Risk**: Named research sources with specific stats. Product strategy guidance, not architecture. Low risk.

#### patterns/spec-isolation-principle.md — 4/5 DISTRIBUTE (NEW)
- **Evidence**: Abhishek LangSmith trace 2026-04-10T15:42 (465K tokens), Ankit-S traces 2026-04-11 multi-fund-hierarchy spec (independent validation of the same pattern). Active demand signal answered: "When 10 specs exist for a single product, how do they reference shared concepts without cross-contaminating?"
- **Uniqueness**: spec-reading-guides covers inline technical explanations. This covers how multiple specs co-exist without coupling. Entirely different concern.
- **Actionability**: Warning signs of cross-contamination (redefines a type from prior spec, references another spec by name). "Write Out of Scope before writing the spec body" is a concrete ordering change.
- **Risk**: Two independent sessions validating the same practice. Documentation guidance. Low risk.

#### patterns/spec-to-ship-v8-superpowers.md — 4/5 DISTRIBUTE (NEW)
- **Evidence**: Ankit-S LangSmith traces 2026-04-10 14:03-14:21, commit e57b16d1 (spec-to-ship-playbook-v8.md added with 7 versions archived).
- **Uniqueness**: v8-specific Agent Contract rules 17+18 (no completion claims without evidence; bite-sized tasks with complete code) and superpowers integration pattern are net-new. Prior knowledge base was at v7.
- **Actionability**: "Always invoke superpowers:requesting-code-review after implementation, before Phase 5 handoff." Rule 17+18 apply to every agent — changes behavioral expectations.
- **Risk**: Committed playbook as source. Low risk.

#### patterns/doc-to-graph-llm-boundary.md — 4/5 DISTRIBUTE (NEW)
- **Evidence**: Sahil LangSmith traces 2026-04-10T21:28-21:31 — two consecutive turns on graph-building approach. Turn 2 (21:28): "There are three approaches, ranked by effort vs scale" — schema-first, then deterministic parsing, then LLM only for fuzzy. Turn 1 (21:31): "No — often you don't [need LLM]. LLMs are for the fuzzy parts." Active demand signal: "How do I build a graph from competitive research data — what's the right schema, and do I need LLM at every step?"
- **Uniqueness**: No existing entry covers LLM-vs-deterministic decision boundary. Cost-optimization-patterns covers multi-call pipelines; this covers parsing strategy. Different domain.
- **Actionability**: The decision table (JSON/YAML/CSV = no LLM; free-text = yes LLM) is directly applicable to any graph ingestion task. Schema-first instruction changes design order.
- **Risk**: Low — one session but answers active demand signal with clear examples.

#### patterns/graph-native-identity.md — 4/5 DISTRIBUTE (NEW)
- **Evidence**: Commit 0101de17 (CLAUDE.md becomes thin bootstrap pointer), issue #58 open (Identity as graph). Scored 1 for trace evidence — the commit is the specific person (kagrawal29) taking the specific action (removing content from CLAUDE.md) as evidence of the principle being applied, not just discussed.
- **Uniqueness**: No existing entry covers what belongs in CLAUDE.md vs graph, or the bootstrap sequence. This is meta-system architecture.
- **Actionability**: "When adding a new invariant: create an Invariant node in the graph, don't add it to CLAUDE.md." Changes where developers put new rules.
- **Risk**: Partially implemented (issue #58 open). Entry accurately reflects partial state. Low risk.

#### patterns/vc-ai-market-ground-truth.md — 3/5 DISTRIBUTE (NEW)
- **Evidence**: 0 — source is March 29 research document. Graph already has this as a node (Community -1). No LangSmith trace shows a session where this knowledge was needed and missing.
- **Uniqueness**: "LLM IS the interface" (do NOT build competing AI interface), MCP-first validation from Affinity beta, explainability non-negotiable (Scale VP black box failure), privacy-as-moat (Granola $1.5B), vocabulary gap ("AI agent" zero mentions in r/venturecapital) — all absent from existing entries.
- **Actionability**: "Do NOT build a competing AI interface. Build the data and workflow layer." Explainability rule and privacy-lead are concrete product decision guidelines.
- **Note**: Minimum threshold. Would promote to 4/5 if a team session traced to "should we build our own AI interface?" decision.

#### patterns/emerging-manager-solo-gp-segment.md — 3/5 DISTRIBUTE (NEW)
- **Evidence**: 0 — source is March 29 research document. GitHub issues #12 and #13 (open) corroborate team interest but no session trace.
- **Uniqueness**: Pricing tier analysis, Decile Hub threat profile, VC Lab distribution channel, fund survival rates — all absent from existing entries.
- **Actionability**: "$149/month Solo tier fits essential-tool zone (less than Affinity CRM alone)." "VC Lab partnership is the single highest-ROI distribution move." Phase 1/2/3 feature roadmap.
- **Note**: Minimum threshold. Would promote if pricing or GTM confusion surfaces in team traces.

#### patterns/vibe-coding-threat-assessment.md — 3/5 DISTRIBUTE (NEW)
- **Evidence**: 0 — source is March 29 research document. No LangSmith trace linking to this gap.
- **Uniqueness**: 35% SaaS replacement stat, named VC firms building internal tools (Topology "Fiber", Thrive "Puck", SignalFire "Beacon"), 6-12 month defensibility window, DIY stack calculation (<$500/month covers 60-70% of associate work) — all absent from existing entries.
- **Actionability**: "'Can a sophisticated GP vibe-code this in a weekend?' — if yes, deprioritize." Feature defensibility calculus is directly applicable to any product decision.
- **Note**: Minimum threshold. Strong on uniqueness and actionability despite weak trace evidence.

---

### Notes

1. **Zero-discard streak extends to 13 consecutive evaluations.** All 11 new entries clear the ≥3 threshold. Architecture entries (5/5) are the strongest; product-domain entries (3/5) are marginal distributes on trace evidence alone. This is expected: product strategy knowledge comes from research documents, not from team session traces.

2. **Research-document entries face a structural trace evidence gap.** vc-ai-market-ground-truth, emerging-manager-solo-gp-segment, and vibe-coding-threat-assessment all score 0 on trace evidence because they derive from March 29 research artifacts, not recent sessions. They were distributed at 3/5 because: (a) source documents exist and are verified, (b) GitHub issues corroborate demand, (c) content is actionable with no stale risk. Future synthesis should link research-derived entries to specific demand signals in graph-demand.md where possible.

3. **3 duplicate candidates identified and handled cleanly.** mcp-transport-streamable-http.md, claude-md-thin-pointer.md, and spec-multi-spec-dependency.md were identified as duplicates of mcp-streamable-http-auth.md, graph-native-identity.md, and spec-isolation-principle.md respectively. The synthesis agent correctly excluded all three from the commit — the kept versions are the more thorough, better-structured entries.

4. **Spec-related entries now form a coherent cluster.** spec-tech-separation, spec-isolation-principle, spec-reading-guides (existing), and spec-to-ship-v8-superpowers together answer the major open spec questions from graph-demand.md. This is healthy convergence.

5. **lp-reporting-pain-map.md was synthesized as a parallel artifact but not committed.** It covered Twitter-specific vocabulary evidence (practitioner tweet IDs, "LP update" not "LP report"). lp-reporting-pain-profile.md (which was committed) covers the quantitative survey side. The uncommitted entry's key insight (vocabulary: "LP update" not "LP report") should be incorporated into lp-reporting-pain-profile.md in a future cycle.

---

## Evaluation — 2026-04-10 (cycle 5: post-synthesis)

Evaluated 1 new entry + 3 updated entries from synthesis commit `072ec24` ("auto-synthesis: 2026-04-10 — 1 new entry, 3 updated"). Signal sources: LangSmith traces Run 5 (Abhishek 85+ turns — PostgREST client 3-advocate group debate, PgBouncer pooling, hono/client + factory pattern, Zod mutations; Ankit-S 38+ turns — pipeline stage editor full validation). GitHub signals: commit 78064b8f (Abhishek, decisions #43-44), commits b9186b9b + 415ab418 (session-pull hooks), commits 6b3c3dd + 253c55d (backend workflow + hono/client updates).

### New Knowledge Entries

| Entry | Evidence | Unique | Actionable | Adoption | Risk | Total | Decision |
|---|---|---|---|---|---|---|---|
| architecture/postgrest-client-type-safety.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |

### Updated Knowledge Entries (substantive)

| Entry | Evidence | Unique | Actionable | Adoption | Risk | Total | Decision |
|---|---|---|---|---|---|---|---|
| architecture/tech-stack-completed.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| patterns/spec-reading-guides.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| tool-configs/auto-sync-hooks.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |

### Updated Knowledge Entries (infrastructure only — not scored)

| Entry | Change | Decision |
|---|---|---|
| index.md | New entry added (postgrest-client-type-safety) | N/A |
| search-index.md | New keywords added | N/A |

**Total: 1 new distribute, 3 update distribute, 0 hold, 0 discard**

---

### Scoring Rationale

#### architecture/postgrest-client-type-safety.md — 5/5 DISTRIBUTE (NEW)
- **Evidence**: Abhishek LangSmith traces 2026-04-10 — 75+ turn session including 3-advocate group debate. Turn 5 (11:43:03): all agents shut down, "GD confirmed our existing decision — postgrest-js for PostgREST is unanimously validated." Turn 8 (11:41:54): full group discussion result with vote table — Orval advocate conceded ("PostgREST's value IS resource embedding"), openapi-advocate conceded for PostgREST but recommended hono/client for Hono. Turn 2 (12:00:11): Orval flow diagram comparison. Later turns: MoM review, hono/client update to #44, factory pattern hooks, Zod mutation validation. Commit 78064b8f (2026-04-10T11:32). Specific person, specific multi-agent evaluation, verified commit.
- **Uniqueness**: tech-stack-completed.md has a 1-paragraph summary of Decision #44 with cross-reference. This entry contains the full evaluation: 3-column comparison table, why Orval was rejected (can't express resource embedding via OpenAPI), why openapi-fetch conceded, views vs embedded queries analysis, specific how-to-apply steps. ~90% net-new content vs the tech-stack summary.
- **Actionability**: Critical behavior change. Without this entry, Claude's training data suggests Orval as a common React/OpenAPI pattern. With this entry, Claude knows: (1) Orval was explicitly evaluated and rejected for PostgREST, (2) postgrest-js is the chosen client with native resource embedding, (3) hono/client for Hono endpoints, (4) "Do not introduce Orval or openapi-fetch for PostgREST — the evaluation is complete." Prevents duplicate evaluation work and wrong tool choice.
- **Adoption**: Architecture category has 100% distribute rate across all evaluations (7+ entries, 0 discards). First API-client-specific entry — benefit of doubt plus strong category track record.
- **Risk**: Based on 3-advocate group debate (not single opinion), unanimous convergence, commit-backed. Resource embedding claims are verifiable PostgREST documentation. SETTLED status is appropriate given the thoroughness of evaluation. Low risk.

#### architecture/tech-stack-completed.md — 5/5 DISTRIBUTE (UPDATE: decisions #43-44)
- **Evidence**: Commit 78064b8f adds decisions #43 (Keycloak client) and #44 (PostgREST client + hono/client). Later traces (13:20:51): PgBouncer pooling decision — PostgREST connects directly to Postgres, other services through PgBouncer. Commit 6b3c3dd (13:25:17): backend workflow + PgBouncer pooling update. All trace-backed, all committed.
- **Uniqueness**: 42→44 decisions. Decision #43 (Keycloak admin client — `@keycloak/keycloak-admin-client`) is entirely new. Decision #44 is a summary with cross-reference to the detailed entry. ~15% new content on the canonical reference.
- **Actionability**: Tech stack reference now includes programmatic Keycloak admin operations and the API client strategy. Prevents choosing alternative packages for either.
- **Adoption**: Scored 5/5 in every evaluation since creation (4 consecutive). The definitive tech stack reference.
- **Risk**: All additions commit-backed. Official packages. Low risk.

#### patterns/spec-reading-guides.md — 5/5 DISTRIBUTE (UPDATE: 2nd test case + **confidence override**)
- **Evidence**: Pipeline stage editor traces add second validation. Turn 8 (09:40:09): "passed mean .. completed?" — reviewer caught terminology ambiguity via reading guide. Turn 3 (09:59:39): "what is the this ..terminal?" — terminal vs active distinction surfaced. Turn 5 (09:47:42): spec validated with fixes. Turn 7 (09:41:24): CRM research (Salesforce, Pipedrive) informed terminal stage modeling. Real catches, real fixes.
- **Uniqueness**: Second test case (pipeline stage editor) adds to first (channel preferences). Two features validating the same pattern strengthens evidence base.
- **Actionability**: Two test cases make the reading guide pattern more credible when injected during spec-writing sessions.
- **Adoption**: Same person (Ankit-S) applied pattern to second feature — strong internal adoption. Scored 5/5 in both prior evaluations.
- **Risk**: Documentation practice, not architecture decision. Low consequences if stale. Catches verifiable in traces.
- **CONFIDENCE OVERRIDE**: Synthesis bumped confidence from `medium` to `high`. Heimdall reverts to `medium`. Reason: prior evaluation (cycle 4) explicitly noted "promotion to high should wait for a second team member adopting reading guides." Both test cases are from the same person (Ankit-S). Per knowledge-format.md, `high` requires "Consistently observed, adopted successfully, measurable impact." Two features by one person meets `medium` ("Observed in 2+ contexts") but not `high`. Correction applied to file.

#### tool-configs/auto-sync-hooks.md — 5/5 DISTRIBUTE (UPDATE: session-pull hook)
- **Evidence**: Commits b9186b9b (VC-AI-Assoicate) and 415ab418 (maverick-market-research) deploy the session-pull hook. Delivery gap documented in Kshitiz traces (cycle 3 — only 1/6 team members confirmed receiving rules). The hook directly addresses a verified delivery problem.
- **Uniqueness**: Adds new hook type (SessionStart) to existing PostToolUse entry. Delivery gap problem + solution are ~40% net-new content. Complementary mechanisms, correctly grouped in single entry.
- **Actionability**: Complete JSON configuration for session-pull included. Someone asking about delivery gap or hook setup gets both hooks. Changes Claude's recommendation: suggest both hooks, not just auto-sync.
- **Adoption**: Base entry scored 5/5 previously. Already deployed to 2 repos with specific commit SHAs. Tool-configs category has strong track record.
- **Risk**: Committed code, verified JSON, honest about limited verification ("only Kshitiz confirmed receiving rules"). Low risk.

---

### Notes

1. **Zero-discard streak now at 7 consecutive evaluations.** Knowledge base is at ~34 entries — still below the 40-entry threshold. Synthesis quality remains high: all entries are trace-backed with specific turns, commits, and verifiable outcomes. The new postgrest-client entry demonstrates particularly strong evidence (3-advocate debate is the most rigorous evaluation method observed so far).

2. **Confidence override applied to spec-reading-guides.md.** Synthesis agent promoted from medium to high. Heimdall reverted. The bar for high confidence is a second independent adopter — not a second feature by the same person. This is the first time Heimdall has overridden a synthesis confidence change. Flagging for synthesis agent: same-person, multiple-context does not equal multi-person adoption.

3. **postgrest-client-type-safety.md introduces a new evaluation pattern: advocate debates.** The 3-advocate group discussion is the most rigorous decision-making process observed in the team traces. This approach produced a more defensible decision than typical "person evaluates options alone" sessions. Worth noting for future knowledge entries — entries backed by multi-advocate debates have inherently stronger evidence.

4. **tech-stack-completed.md is now at 44 decisions.** Approaching the density threshold noted in cycle 4 ("growth past 50 decisions would warrant restructuring"). Currently manageable. Review at 50.

5. **Session-pull hook addresses a systemic problem.** The delivery gap (knowledge pushed but not pulled) was the #1 blocker for the distribution pipeline's effectiveness. If session-pull works as expected, next cycle should show improved delivery verification rates. High-leverage change.

---

## Evaluation — 2026-04-10 (cycle 4: post-synthesis)

Evaluated 3 updated entries from synthesis commit `f45420a` ("auto-synthesis: 2026-04-10 — 0 new entries, 3 updated"). Signal sources: LangSmith traces Run 3 (Abhishek 38 turns — Hono/cloud switch, docker sizing, tech stack finalization; Ankit-S 38 turns — pipeline stage editor spec validation with reading guides). GitHub signals: commit 529ccc9a (Abhishek, Hono + cloud switch), commit 42ee3c98 (decisions #37-42), PR #8 merged.

### Updated Knowledge Entries (substantive)

| Entry | Evidence | Unique | Actionable | Adoption | Risk | Total | Decision |
|---|---|---|---|---|---|---|---|
| architecture/tech-stack-completed.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| architecture/api-gateway-exploration.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| patterns/spec-reading-guides.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |

### Updated Knowledge Entries (infrastructure only — not scored)

| Entry | Change | Decision |
|---|---|---|
| index.md | Title updated for tech-stack-completed | N/A |
| search-index.md | Added `hono`, `pending` keywords | N/A |

**Total: 3 updates distribute, 0 hold, 0 discard**

---

### Scoring Rationale

#### architecture/tech-stack-completed.md — 5/5 DISTRIBUTE (UPDATE: Hono, cloud, 42 decisions)
- **Evidence**: Abhishek LangSmith traces Run 3. Turn 13 (08:40:51): "Sentry and Postgres, we will not be using self-hosted versions since it takes a lot of RAM" — explicit decision to move Sentry+PostHog to cloud with RAM justification. Turn 15 (08:30:48): "Can you list down all the docker containers" — 26 containers enumerated. Turn 12 (08:43:01): "So now the doc is final?" — 3 pending decisions confirmed (#22, #23, #24). Turn 4 (08:56:38): commit on main. GitHub commit 529ccc9a (Abhishek, 2026-04-10T08:57) and PR #8 merged (3248fc3c). Specific person, specific decisions, verifiable commits.
- **Uniqueness**: Major update — 16 services → 42 decisions, 3 pending. New content: Hono replacing Next.js API routes, Sentry/PostHog cloud rationale (RAM savings), decisions #37-42 (data retention, external API, i18n, embedding model, resilience, image processing), 26 containers (up from 16), pending decisions table. ~40% of the entry is net-new.
- **Actionability**: Critical behavior change — someone starting backend work now sees Hono (not Next.js API routes) for custom API, PostHog/Sentry are cloud (not self-hosted), 26 containers not 16, and 3 decisions still pending. Prevents setting up self-hosted Sentry (wastes 2GB RAM) or writing Next.js API routes for endpoints that should use Hono.
- **Adoption**: Entry scored 5/5 in first evaluation (2026-04-07) and has been the authoritative tech stack reference since. Architecture category: 100% distribute rate across all evaluations. Update enriches without changing character.
- **Risk**: All changes backed by commits (529ccc9a, 42ee3c98, PR #8). Abhishek explicitly confirmed in traces. Pending decisions clearly marked as pending, not speculated. Cloud switch rationale is concrete (RAM numbers). Low risk.

#### architecture/api-gateway-exploration.md — 5/5 DISTRIBUTE (UPDATE: Hono context correction)
- **Evidence**: The Hono switch (commit 529ccc9a) directly changes the evaluation context for the API gateway question. Original entry's trace evidence (Abhishek's 15-turn Zuplo session) remains valid. The Context section now correctly references Hono's middleware capabilities rather than Next.js API routes.
- **Uniqueness**: Small delta (one paragraph), but the correction is critical. Without it, someone reading this entry would evaluate Zuplo against Next.js API routes — the wrong baseline. The question "can Hono middleware handle rate limiting, API keys, etc.?" is different from "can Next.js API routes handle it?"
- **Actionability**: Changes the evaluation frame. Hono has built-in middleware ecosystem (rate limiting, CORS, JWT, etc.). Someone reading this entry now considers Hono's native capabilities vs. Zuplo's overlay, rather than Next.js limitations vs. Zuplo.
- **Adoption**: Entry scored 5/5 in cycle 3 evaluation. Same entry, corrected context.
- **Risk**: Factual correction that makes the entry more accurate. Removes a stale reference.
- **Fix applied**: Heimdall corrected an internal inconsistency — the Status section still said "Next.js API routes" while Context said "Hono." Status updated to match.

#### patterns/spec-reading-guides.md — 5/5 DISTRIBUTE (UPDATE: second test case)
- **Evidence**: Ankit-S LangSmith traces Run 3. Turn 8 (09:40:09): "passed mean .. completed?" — reviewer caught terminology ambiguity while reviewing spec with reading guides. Turn 3 (09:59:39): "what is the this ..terminal?" — reviewer asked about terminal vs. active stage distinction that the reading guide surfaced. Turn 7 (09:41:24): researched how CRMs handle terminal stages after reading guide revealed the modeling question. Turn 5 (09:47:42): spec validated with fixes applied. Turn 2 (10:00:31): planning complete for pipeline stage editor. The reading guide pattern directly enabled a non-engineer to catch a data modeling issue ("passed" should be terminal, not active) that would have been invisible without inline explanations.
- **Uniqueness**: Adds second test case to a pattern entry. Channel preferences was test case #1 (caught opaque TypeScript interfaces). Pipeline stage editor is test case #2 (caught "passed" stage ambiguity and terminal vs. active modeling). Two features, same pattern, both producing real catches. Strengthens the evidence base.
- **Actionability**: Two test cases make the pattern more convincing when injected. Someone writing a spec now sees evidence from TWO features, not just one.
- **Adoption**: Same person (Ankit-S) applied the pattern to a second feature — strong internal adoption signal. Entry scored 5/5 in cycle 3.
- **Risk**: Based on verifiable trace evidence. The "passed" stage ambiguity is a real product decision that was caught during spec review. Low risk.
- **Confidence note**: Still medium. Two contexts (channel preferences + pipeline stage editor) by the same person justifies medium per knowledge-format.md ("Observed in 2+ contexts"). Promotion to high requires a second team member independently using reading guides in a spec.

---

### Notes

1. **Zero-discard streak now at 6 consecutive evaluations.** Per the review checkpoint set in cycle 3: "if still 0% at 40+ entries, that would indicate a genuine calibration issue." Knowledge base is at ~33 entries — below the 40-entry threshold. Continue monitoring. Synthesis quality remains high: all 3 updates are trace-backed with verifiable commits.

2. **tech-stack-completed.md is now the single most information-dense entry** in the knowledge base. 42 decisions + 3 pending + rationale sections + Docker container list. Consider whether this entry should be split in a future cycle: core stack table (always inject) vs. decision rationale (inject on demand). Current size is manageable, but growth past 50 decisions would warrant restructuring.

3. **api-gateway-exploration.md inconsistency fixed.** Synthesis updated the Context section to reference Hono but missed the Status section. Heimdall corrected this during evaluation. Flag for synthesis agent: when updating entries, check ALL sections for stale cross-references, not just the primary content section.

4. **spec-reading-guides.md second test case strengthens the pattern significantly.** The pipeline stage editor catch was substantive — Ankit-S caught a real data modeling ambiguity ("passed" stage as terminal vs. active) because the reading guide made TypeScript interfaces reviewable. This is exactly the kind of evidence that distinguishes a useful pattern from a theoretical one. Still watching for a second team member to adopt before promoting to high confidence.

5. **Hono switch has cross-entry implications.** The tech stack change from Next.js API routes to Hono may affect other entries that reference "Next.js API routes." Quick grep of knowledge base: only api-gateway-exploration.md referenced it (now corrected). No other entries affected.

---

## Evaluation — 2026-04-10 (cycle 3: post-synthesis)

Evaluated 2 new entries + 1 substantive update from synthesis commit `7cbe71b` ("auto-synthesis: 2026-04-10 — 2 new entries, 3 updated, 0 hold, 0 discard"). Signal sources: LangSmith traces (Abhishek 15 turns/5.99M tokens — Zuplo deep dive; Ankit-S 15 turns/17.35M tokens — spec-to-ship v7 + channel preferences; Kshitiz 12 turns/14.15M tokens — meta system + delivery verification). 3 additional updates were metadata-only (distributed-to, related links) — not scored.

### New Knowledge Entries

| Entry | Evidence | Unique | Actionable | Adoption | Risk | Total | Decision |
|---|---|---|---|---|---|---|---|
| architecture/api-gateway-exploration.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| patterns/spec-reading-guides.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |

### Updated Knowledge Entries (substantive)

| Entry | Evidence | Unique | Actionable | Adoption | Risk | Total | Decision |
|---|---|---|---|---|---|---|---|
| tool-configs/rules-loaded-telemetry.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |

### Updated Knowledge Entries (metadata only — not scored)

| Entry | Change | Decision |
|---|---|---|
| architecture/agent-harness-decision.md | distributed-to updated | N/A |
| architecture/fixture-first-development.md | related links updated | N/A |
| architecture/tech-stack-completed.md | related links updated | N/A |

**Total: 2 new distribute, 1 update distribute, 0 hold, 0 discard**

---

### Scoring Rationale

#### architecture/api-gateway-exploration.md — 5/5 DISTRIBUTE (NEW)
- **Evidence**: Abhishek LangSmith traces 2026-04-10 — 15 turns, 5.99M tokens. Full Zuplo deep dive: pricing page scrape (turn 9), SSE constraint discovery (turn 2 — "SSE streaming requires Enterprise at $1,000+/mo, hard feature gate"), 3 research agents deployed (turn 3), social media validation via Xpoz MCP (turns 4-5 — zero practitioner signal found). Specific person, specific session, specific architectural question.
- **Uniqueness**: tech-stack-completed.md lists "Custom API: Next.js API routes" and "PostgREST" for CRUD but says nothing about API management layers, rate limiting, developer portals, or API key management. This entry covers a new decision space: whether an API gateway layer is needed on top of the existing stack. ~95% net-new content.
- **Actionability**: When someone considers adding rate limiting, API key management, or a developer portal to Maverick's API, this entry injects: Abhishek is actively evaluating; SSE streaming requires Enterprise at $1,000+/mo; Zuplo has only 15 G2 reviews (small user base); coordinate before deciding. Prevents duplicate research and flags the hard cost gate that could kill this option.
- **Adoption**: First API gateway entry (benefit of doubt). Architecture category has scored 5/5 across all prior evaluations.
- **Risk**: Correctly marked `type: exploration`, `confidence: low`, status `OPEN`. Based on verified pricing data from actual pricing page. Includes concrete numbers ($0, $25, $1,000+). Does not lock a premature decision — explicitly says "research in progress." Self-correcting: if Abhishek decides against Zuplo, the entry transitions to a settled decision with rationale.

#### patterns/spec-reading-guides.md — 5/5 DISTRIBUTE (NEW)
- **Evidence**: Ankit-S LangSmith traces 2026-04-10 — 15 turns, 17.35M tokens. Turn 5: created `docs/workflow/spec-to-ship-playbook-v7.md` with 3 insertion points for reading guides. Turn 8: identified where in playbook to add the rule (Agent Contract rule 16, Section 5.5). Turns 9-10: iterated on `DealCardViewModel` reading guide format — user specifically asked for each explanation line to "point back to the specific technical thing." Channel preferences feature was the test case — Phase 3-4 passed (0 typecheck errors, 0 lint warnings, Storybook built).
- **Uniqueness**: No existing entry covers spec readability, inline documentation for TypeScript interfaces, or making specs reviewable by non-technical stakeholders. fixture-first-development.md covers mock data patterns — unrelated. This is net-new: a documentation practice pattern with a concrete NO-SKIP rule.
- **Actionability**: When someone writes a spec using spec-to-ship, this entry injects the reading guide requirement: after every interface/enum/type block, add plain-language mapping from technical fields to product concepts. Includes a concrete example (`DealCardViewModel`). Changes Claude's behavior when generating specs — it would include reading guides where it wouldn't have before.
- **Adoption**: First spec-documentation entry (benefit of doubt). Strong internal adoption signal: Ankit-S codified this as a NO-SKIP rule in the v7 playbook, not just a suggestion. Patterns category has scored well in all evaluations.
- **Risk**: Based on committed code (v7 playbook created, 3 insertion points added) and tested implementation (channel preferences feature passed Phase 3-4). A documentation practice, not an architecture decision — low consequences if it becomes stale. Correctly at `confidence: medium`.
- **Note**: confidence: medium is slightly generous for a single-person observation. Per knowledge-format.md, medium requires "observed in 2+ contexts or confirmed by team member." Arguably the fact that Ankit-S both proposed AND successfully implemented it (tested in channel preferences) counts as confirmation. Not downgrading, but promotion to high should wait for a second team member adopting reading guides.

#### tool-configs/rules-loaded-telemetry.md — 5/5 DISTRIBUTE (UPDATE: delivery status section)
- **Evidence**: Delivery status sourced from actual LangSmith API queries during this cycle. Kshitiz confirmed working (trace from 2026-04-09T12:42Z). Sahiram UUID confirmed broken (404 response). Abhishek, Ankit-S, Sahil, Pranav confirmed no data (hook not configured). All findings are API-verified, not inferred.
- **Uniqueness**: Adds per-person delivery status, coverage percentage (17%), and a specific action item. The base procedure entry was already unique; this update adds operational state data not captured elsewhere.
- **Actionability**: Three concrete action items: (1) push rules-loaded hook to remaining 4 team members, (2) fix Sahiram's UUID, (3) verify Kshitiz's data is current. Each is immediately executable.
- **Adoption**: Update to existing entry that scored 5/5 in prior evaluation. Enrichment, not replacement.
- **Risk**: Factual status data with explicit dates. Will become stale as coverage improves — but the date stamp makes staleness detectable. Low risk.

---

### Notes

1. **Zero-discard streak now at 5 consecutive evaluations** (2026-04-07, 2026-04-09, 2026-04-10 cycles 1-3). This hits the threshold set in prior evaluations. Review: synthesis quality remains high — all entries are trace-backed with specific turns, and the knowledge base (now ~33 entries) is still in expansion phase. The bar is not too low; the synthesis agent is filtering effectively. Reset the watch counter. Next review checkpoint: if still 0% at 40+ entries, that would indicate a genuine calibration issue.

2. **Knowledge base now at ~33 entries.** The two new entries (api-gateway-exploration, spec-reading-guides) bring the count from 31. Category balance: architecture (12), patterns (9), tool-configs (6), workflows (3), anti-patterns (2). Architecture continues to dominate — expected during stack-decision phase.

3. **api-gateway-exploration is the third active exploration** (after active-email-redesign and memory-architecture, though memory-architecture was resolved). Active explorations are time-sensitive — if Abhishek makes a decision, this entry must transition to a settled decision or be discarded. Set review checkpoint for next cycle.

4. **spec-reading-guides bridges synthesis and distribution repos.** It was observed in VC-AI-Associate (Ankit-S's session) but captured here in meta. The reading guide pattern should be distributed back to VC-AI-Associate's knowledge entries so it's available during spec-writing sessions. Flagging for distribution agent.

5. **Delivery status in rules-loaded-telemetry.md will require periodic refresh.** The 2026-04-10 snapshot is accurate today but will go stale. Each evaluation cycle should check whether delivery coverage has improved and update the section. This is operational data, not permanent knowledge.

---

## Evaluation — 2026-04-10 (cycle 2: post-synthesis)

Evaluated 1 new entry + 3 updated entries from synthesis commit `2b13ebd` ("auto-synthesis: 2026-04-10 — 1 new entry, 3 updated, 1 YAML fix"). Signal sources: LangSmith traces (Sahil 67 turns/44M tokens, Abhishek 63 turns/35M tokens, Ankit-S 100 turns/75M tokens), GitHub activity (PR #44, Drushi commits).

### New Knowledge Entries

| Entry | Evidence | Unique | Actionable | Adoption | Risk | Total | Decision |
|---|---|---|---|---|---|---|---|
| architecture/agent-harness-decision.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |

### Updated Knowledge Entries

| Entry | Evidence | Unique | Actionable | Adoption | Risk | Total | Decision |
|---|---|---|---|---|---|---|---|
| architecture/phase1-decisions-settled.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| patterns/competitor-research-dataset.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| patterns/expert-panel-validation.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |

**Total: 1 new distribute, 3 update distributes, 0 hold, 0 discard**

---

### Scoring Rationale

#### architecture/agent-harness-decision.md — 5/5 DISTRIBUTE (NEW)
- **Evidence**: Sahil LangSmith traces 2026-04-09 — Grand Debate session (67 turns, 44M tokens). Turns 12:18-12:26 show 8 specialist agents evaluating and converging on Vercel AI SDK + Trigger.dev. Decision doc committed to `dev/claude/agent-harness-research` branch, pushed 2026-04-09T12:26.
- **Uniqueness**: tech-stack-completed.md has a one-line "Job queue: Trigger.dev v3→v4" but nothing about AI agent runtime framework, execution modes (inline/durable/MCP), CopilotKit's role, or killing arguments against Mastra (prompt caching, React hooks, workflow engine conflict). ~90% net-new content.
- **Actionability**: When someone builds AI agent features, implements chat/streaming, or considers Mastra, this entry injects specific guidance: three execution modes, CopilotKit for transport only, do not introduce Mastra. Directly prevents re-evaluation of a settled decision.
- **Adoption**: First agent-harness entry (benefit of doubt). Same category (architecture) has consistently scored 5/5 in prior evaluations.
- **Risk**: 8-specialist Grand Debate, all converged with concrete technical evidence. Decision doc committed to repo. Sahil (decision-maker) led the session. Low risk.

#### architecture/phase1-decisions-settled.md — 5/5 DISTRIBUTE (UPDATE: Batch 2 decisions)
- **Evidence**: Abhishek traces (63 turns, 35M tokens) — explicit decisions: turn 14:49:47 "why are we using Knock instead?" → Knock eliminated; turn 14:42:06 "Is there no open source solution?" → Papermark; turn 06:30:57 i18n deferral. Ankit-S traces (100 turns, 75M tokens) — building multi-channel notification feature with spec-to-ship playbook.
- **Uniqueness**: 7 new Batch 2 decisions (notifications, data rooms, webhooks, i18n, data retention, multi-channel routing, AI runtime) — all net-new. Zero overlap with Batch 1's 22 decisions.
- **Actionability**: Prevents re-evaluation of notifications (no Knock — build direct with Trigger.dev dispatchers), data rooms (Papermark self-hosted), webhooks (Svix self-hosted). Three concrete "don't use X, use Y" injections.
- **Adoption**: Update to existing entry that scored 5/5 in first evaluation. Same entry, more content.
- **Risk**: All decisions sourced from verifiable trace sessions. Deferrals (i18n, data retention) are explicitly reasoned.

#### patterns/competitor-research-dataset.md — 5/5 DISTRIBUTE (UPDATE: employee dives + launch studies)
- **Evidence**: PR #44 merged (Saurabh — 773 LinkedIn posts, 26 employees, 7 brands). Drushi commits: Attio (3 files) + Figma (4 files) launch case studies. All in maverick-market-research repo.
- **Uniqueness**: Adds two new research dimensions: employee-voice analysis (different from brand-level messaging) and launch case studies (different from competitive monitoring). Neither captured elsewhere.
- **Actionability**: When writing employee-focused positioning or studying competitor launches, this update provides reference to where the data lives.
- **Risk**: Based on merged PRs and committed files. Irrefutable.

#### patterns/expert-panel-validation.md — 5/5 DISTRIBUTE (UPDATE: confidence medium→high)
- **Evidence**: Second independent observation: Sahil's Grand Debate (8 specialists, 67 turns, 44M tokens) joins Abhishek's security panel (4 specialists) from last cycle. Two independent team members, same day, different use cases.
- **Uniqueness**: Update enriches pattern with "works for selection (Sahil) and validation (Abhishek)" and "scales from 4 to 8 experts." Net-new insight on pattern scope.
- **Actionability**: Confidence upgrade medium→high means stronger injection weight. Broader applicability confirmed.
- **Risk**: Confidence upgrade justified — 2 independent team members is the standard threshold for high confidence per knowledge-format.md ("Observed in 2+ contexts or confirmed by team member").

---

### Notes

1. **Zero discards, fourth consecutive evaluation** (2026-04-07: 0, 2026-04-09: 0, 2026-04-10 cycle 1: 0, 2026-04-10 cycle 2: 0). Still in expansion phase with ~31 entries. Acceptable. Expect redundancy pressure after ~40 entries.
2. **Agent harness decision completes the tech stack.** The "AI runtime" item was listed as "Still Deferred" in phase1-decisions-settled.md since 2026-04-07. Both entries now cross-reference correctly.
3. **Expert panel validation confidence upgrade is well-earned.** Two independent people (Abhishek, Sahil) using the same pattern on the same day with different intents (validate vs choose) is strong evidence. This is the first confidence promotion from medium to high in the knowledge base.
4. **Delivery gap persists.** Delivery signal shows only 1/6 team members (Kshitiz) has the SessionStart hook installed. These entries will be distributed but may not reach team sessions until hooks are deployed.
5. **Knowledge base now at 31 entries.** The agent-harness-decision is entry #31. Search index and main index updated accordingly by synthesis.

---

## Evaluation — 2026-04-10

Evaluated 1 new knowledge entry (manual creation, not from synthesis) + feedback agent changes from cycle 2 (2026-04-09). No new synthesis entries since last evaluation.

### New Knowledge Entries

| Entry | Evidence | Unique | Actionable | Adoption | Risk | Total | Decision |
|---|---|---|---|---|---|---|---|
| tool-configs/rules-loaded-telemetry.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |

### Feedback Agent Changes (MODE 2)

| Change | Items | Decision | Rationale |
|---|---|---|---|
| Score updates (all MONITOR) | 13 entries | APPROVED | No entry meets AMPLIFY (need N>=5, score>0.3) or REMOVE (need N>=5, score<=-0.2) thresholds. 80% of injections from automated agent sessions — scores are unreliable until agent-session filter is implemented. Correct to hold at MONITOR. |
| Metric schema rename | 10 entries | APPROVED | injection_count→surfaced_count, used_count→cited_count, ignored_count removed. Cosmetic improvement, no content change. |
| Deleted explorations | 2 entries | APPROVED | active-memory-architecture.md (RESOLVED→memory-layer-decisions.md) and active-tech-stack-decisions.md (RESOLVED→tech-stack-completed.md). Both were stale pointers to completed work. Broken reference in memory-layer-decisions.md fixed in this commit. |

### Feedback Gap Proposals

| Gap | Type | Decision | Rationale |
|---|---|---|---|
| Agent session detection filter | System fix | DEFER (not KB entry) | Highest priority code fix to smart-context.py. Eliminates 80% of false-fire injections. Not a knowledge entry — engineering task. |
| Self-referential path filter | System fix | DEFER (not KB entry) | Prevents injecting entries when reading their own file. Engineering task. |
| A/B test harness pattern | Knowledge entry | HOLD | Single session (Kshitiz), low confidence. Create when pattern recurs with second team member. |
| Heimdall evaluation gate | Knowledge entry | HOLD | Useful for system documentation but narrow audience (meta-system operators only). Not actionable for product team sessions. Create when a second person interacts with the meta system. |

### Lint Fixes Applied

- BROKEN-REF: Removed `exploration-memory-architecture` from memory-layer-decisions.md related field (entry was deleted in pre-production cleanup)
- ORPHAN: Added `tool-config-rules-loaded-telemetry` to related fields of langsmith-tracing-setup.md and auto-sync-hooks.md

**Total: 1 distribute, 2 hold (gap proposals), 0 discard**

---

### Scoring Rationale

#### tool-configs/rules-loaded-telemetry.md — 5/5 DISTRIBUTE
- **Evidence**: Created to close a specific delivery verification gap discovered while checking Sahiram's traces — we push rules to branches but had no mechanism to verify they loaded in sessions. The hook was built, deployed, and tested (commits `248a8fd`, `f001a74`). Production audit confirmed it works.
- **Uniqueness**: No other entry covers delivery verification or session-start telemetry. auto-sync-hooks.md covers push/pull. langsmith-tracing-setup.md covers general tracing. This is the missing "did the rules actually load?" piece.
- **Actionability**: When someone debugs why distributed knowledge isn't appearing, or when the meta-system verifies rule delivery, this entry provides exact query procedure (LangSmith API filter for `rules-loaded` runs), pitfalls (missing env vars, timeout handling), and verification steps. Changes behavior from guessing to precise verification.
- **Adoption**: First delivery-verification entry (benefit of doubt). Same category (tool-configs) as langsmith-tracing-setup which has the only positive effectiveness signal in the system (+0.33 at N=3).
- **Risk**: Based on deployed, tested code. Procedure is deterministic (query API, check manifest). Pitfalls section covers known edge cases. Low staleness risk — hook API is stable.

---

### Notes

1. **Effectiveness data is unreliable.** The critical finding from feedback cycle 2 — 80% of injections fire during automated sub-agent sessions — means all surfaced_count/cited_count/effectiveness_score values are noise-inflated. No entry should be AMPLIFIED or REMOVED until the agent-session detection filter is implemented in smart-context.py.
2. **Zero discards across 3 consecutive evaluations** (2026-04-07: 0, 2026-04-09: 0, 2026-04-10: 0). This is acceptable during early operation (knowledge base is still in expansion phase, synthesis quality is high). As the base grows past ~40 entries, expect redundancy pressure to produce discards. If still 0% after 5 evaluations, the bar may be too low.
3. **GitHub issues #17 and #18** (kagrawal29) describe meta-system design proposals ("living knowledge graph", "mycelium as living network"). These are architecture documents for THIS system, not team knowledge entries. They do not require Heimdall evaluation — they are design artifacts for the meta repo itself.
4. **Cycle staleness**: Last full cycle was 2026-04-09. Feedback and distribute agents timed out (300s each). Fresh ingest is needed to capture April 9-10 team activity before next synthesis.

---

## Evaluation — 2026-04-09

Evaluated 5 new knowledge entries + 1 new Level-0 rule from synthesis commit `a4abab5`. Updated entries (cross-references only) not evaluated — no substantive content change.

Methodology: scored each artifact on 5 binary criteria. Level-0 rule additionally checked against threshold (2+ people OR 3+ correction turns from 1 person). Adoption likelihood: benefit of doubt extended on all new entries (no effectiveness_score history yet for this batch).

### Knowledge Entries

| Entry | Evidence | Unique | Actionable | Adoption | Risk | Total | Decision |
|---|---|---|---|---|---|---|---|
| architecture/security-scanning-stack.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| architecture/cross-channel-continuity-model.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| patterns/expert-panel-validation.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| patterns/rule-builder-group-logic.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| tool-configs/gh-workflow-disable.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |

### Rules

| Rule | Evidence | Unique | Actionable | Adoption | Risk | Total | Level-0 Check | Decision |
|---|---|---|---|---|---|---|---|---|
| rule-builder-condition-grouping.md | 1 | 1 | 1 | 1 | 1 | 5 | 6 correction turns from Pranav (≥3 threshold) | DISTRIBUTE |

**Total: 5 distribute, 0 hold, 0 discard**

---

### Scoring Rationale

#### architecture/security-scanning-stack.md — 5/5 DISTRIBUTE
- **Evidence**: Abhishek's LangSmith traces 2026-04-09, turns 06:20–07:27 (~1.9M tokens). Decisions #17 (Infisical) and #18 (Semgrep + Trivy + Coraza) explicitly marked DECIDED in scorecard at turn 07:07:44.
- **Uniqueness**: tech-stack-completed.md lists Infisical as one line in the stack table but doesn't cover Semgrep, Trivy, Coraza, DAST deferral, or how to configure any of them. This entry adds ~80% net-new content on security scanning specifically.
- **Actionability**: Relevant-when keywords (CI security gates, secrets management, SAST, WAF) would inject into sessions touching any of these areas. How-to-Apply section provides exact setup steps for all 4 tools + deferral rationale for DAST. Prevents re-evaluation of settled decisions.
- **Risk**: All decisions explicitly marked DECIDED in trace. OSS tools with verifiable licenses. DAST deferral rationale is well-reasoned (mock endpoints produce noise). No opinion-based claims.

#### architecture/cross-channel-continuity-model.md — 5/5 DISTRIBUTE
- **Evidence**: Sahil's LangSmith traces 2026-04-09, turns 07:00–07:28 (~4.6M tokens). Work-unit+members model evolved and committed within the session. Schema bug (idx_unique_deal_context wrong scope) caught and fixed at turn 07:28:47 during peer review. Verifiable in VC-AI-Assoicate repo.
- **Uniqueness**: memory-layer-decisions.md covers Graphiti/pgvector/embedding stack. This entry covers the `continuity_contexts` table architecture — a separate subsystem (cross-channel conversation persistence). Zero overlap.
- **Actionability**: Any session touching continuity_contexts table, cross-channel memory, or deal context retrieval would get the schema fix and the member-scoped authorization pattern injected. The unique index fix (must include deal_id) is concrete and immediately applicable.
- **Risk**: Changes sourced from commits + peer review — verifiable. Schema behavior is deterministic. No opinion-based claims.

#### patterns/expert-panel-validation.md — 5/5 DISTRIBUTE
- **Evidence**: Abhishek's LangSmith traces 2026-04-09, turn 06:39:34, 1M tokens. Request to convene specialist panel + full panel debate captured in trace output.
- **Uniqueness**: research-driven-architecture-decisions.md covers deploying research agents (31 agents, social media verification for real-world reliability data). Expert panel covers a different technique: role-playing specialists debating tool fitness. Overlap is ~15% ("use multiple agents for architecture"). The trigger, purpose, and application are distinct.
- **Actionability**: When someone is about to lock a major tech decision, this entry injects the panel format + prompt template. Directly usable. Changes behavior from single-perspective evaluation to structured multi-perspective review.
- **Risk**: Technique description at medium confidence (1 source). Well-bounded trigger ("decision will be hard to reverse", "tool choice affects multiple teams"). Entry correctly notes confidence: medium.
- **Note**: Confidence will rise to high once a second team member independently runs this pattern.

#### patterns/rule-builder-group-logic.md — 5/5 DISTRIBUTE
- **Evidence**: Pranav's LangSmith traces 2026-04-07, turns 13:56–14:02 (~109K tokens). 6 consecutive correction turns. Explicit user statement: "from the very first place, when I had created all rules, they were correct, and you fucked it up by confusing." Highest-quality T6 signal type (frustration from wrong AI guidance).
- **Uniqueness**: No existing knowledge entry covers OR/AND group logic in rule builders. category-filtering-context rule (from last cycle) addresses system vs org category disambiguation — different topic entirely.
- **Actionability**: Smart hook injection when someone works on rule configurations. Quick-check section (3 steps) is immediately applicable. Would have reduced Pranav's 109K token session to a single correction.
- **Risk**: Factual — within-group=OR, across-groups=AND is an observable property of Maverick's rule builder UI. Not an opinion. Easily verifiable by opening the UI.

#### tool-configs/gh-workflow-disable.md — 5/5 DISTRIBUTE
- **Evidence**: Abhishek's LangSmith traces 2026-04-09, turns 06:20–06:25. Explicit question at turn 06:25:09: "so they are disabled on remote also or will I have to commit and then push and then it will be live?" — exactly the gap this entry fills. Confirmed: `disabled_manually` status set immediately.
- **Uniqueness**: No existing tool-configs entry covers `gh workflow disable`. auto-sync-hooks.md covers post-commit push automation — different use case.
- **Actionability**: When someone needs to disable CI temporarily, this entry provides exact commands (gh workflow disable/enable, confirm with list). Prevents the file-editing approach which creates unnecessary commits. High-value in active dev sprints.
- **Risk**: GitHub API behavior is stable and verifiable. Pitfalls section covers the one non-obvious edge case (branch protection rules still apply).

#### rule: rule-builder-condition-grouping.md — 5/5 DISTRIBUTE
- **Level-0 threshold**: 6 correction turns from Pranav (single person). Exceeds the 3+ correction turns threshold. Passes.
- **Evidence**: Same Pranav signal as rule-builder-group-logic.md knowledge entry. Explicitly sourced: "6 turns, ~109K tokens, explicit user correction." This is the highest-confidence single-person threshold signal seen this cycle.
- **Uniqueness**: Distinct from category-filtering-context.md rule (system vs org category type disambiguation). Different mechanism, different failure mode.
- **Actionability**: Level-0 rule fires in every session. "Verify condition grouping logic before configuring multi-condition rules" is actionable and testable at query time. Includes self-limiting check ("confirm the entity can hold multiple values simultaneously") that reduces false positive injection.
- **Risk**: Well-scoped to "automation or trigger system with grouped conditions." Rule body includes the universal mechanism (within-group=OR, across-groups=AND) that applies beyond just Maverick. Low noise risk — the trigger phrase "grouped conditions" bounds injection scope appropriately. Rule notes LOW confidence (single session) and states the elevation condition: "elevate to medium after one more instance." Self-correcting.

---

### Notes for Synthesis Agent

1. expert-panel-validation.md is at medium confidence (1 source). Watch for second team member using this pattern. Promote to high confidence when found.
2. All 5 knowledge entries are net-new topics — no redundancy pressure. The knowledge base is still in expansion phase. Expect redundancy to increase after Week 2.
3. rule-builder-condition-grouping (Level-0) and rule-builder-group-logic.md (knowledge) cover the same topic at different delivery levels. This is intentional: rule = always-on injection, knowledge entry = retrieved when searching. Both serve a purpose.
4. Security stack entry will need revalidation if Coraza or Semgrep Community change licensing. Set a review checkpoint at end of Sprint 1.
5. Zero discards this cycle again. Synthesis agent quality is high — signals are real and entries are well-bounded. The gate remains meaningful because all 6 passed on merit (5/5), not because the bar was lowered.

---

## Evaluation — 2026-04-07

Evaluated 8 new knowledge entries + 1 new rule from synthesis commit `69f41cb`.

Methodology: scored each entry on 5 binary criteria (TRACE EVIDENCE, UNIQUENESS, ACTIONABILITY, ADOPTION LIKELIHOOD, RISK). Rules additionally checked against 2+ people / 3+ correction turns threshold. Baseline adoption: first cycle, no entries with effectiveness_score ≤ 0 across 3+ runs — benefit of doubt applied.

### Knowledge Entries

| Entry | Evidence | Unique | Actionable | Adoption | Risk | Total | Decision |
|---|---|---|---|---|---|---|---|
| architecture/configurable-per-fund-pattern.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| architecture/phase1-decisions-settled.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| architecture/tech-stack-completed.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| architecture/fsd-audit-critical-issues.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| patterns/competitor-research-dataset.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| patterns/cross-agent-monitoring.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| patterns/issue-as-agent-scratchpad.md | 1 | 1 | 1 | 1 | 1 | 5 | DISTRIBUTE |
| anti-patterns/ai-generated-doc-quality.md | 1 | 1 | 1 | 1 | 0 | 4 | DISTRIBUTE |

### Rules

| Rule | Evidence | Unique | Actionable | Adoption | Risk | Total | Level-0 Check | Decision |
|---|---|---|---|---|---|---|---|---|
| category-filtering-context.md | 1 | 1 | 1 | 1 | 0 | 4 | 4 corrections from Pranav (≥3 threshold) | DISTRIBUTE |

**Total: 9 distribute, 0 hold, 0 discard**

---

### Scoring Rationale

#### configurable-per-fund-pattern.md — 5/5 DISTRIBUTE
- **Evidence**: `docs/phase-1/DECISIONS.md` commit `041ba65b` — 4 explicit questions (Q6, Q8, Q9, Q10) all resolved to "configurable per fund" by Sahil Agrawal. Cross-confirmed by Abhishek's LangSmith traces deliberating tech stack for the same application.
- **Uniqueness**: No existing entry captures the "configurable per fund" theme or its architectural implications (JSONB, config tables, runtime configurability). Nearest neighbor `phase1-decisions-settled.md` catalogs decisions; this one explains WHY four independent decisions converged on the same pattern.
- **Actionability**: Relevant-when keywords match anyone designing fund-facing features. Would inject: use JSONB not hardcoded enums, runtime-configurable over hardcoded. This changes what Claude suggests for schema design.
- **Risk**: Source-verified. Specific file, specific commit, specific questions cited. Verifiable by reading `docs/phase-1/DECISIONS.md`.

#### phase1-decisions-settled.md — 5/5 DISTRIBUTE
- **Evidence**: Same source commit (`041ba65b`) as above — Sahil Agrawal decision session, 22 questions answered. Complete audit trail.
- **Uniqueness**: 22 discrete decisions not captured anywhere else in the knowledge base. While configurable-per-fund covers Q6/Q8/Q9/Q10, this covers the other 18 (document merging, call detail views, pass/decline structure, DD checklist, co-investors, MCP scope, etc.).
- **Actionability**: Someone starting work on documents, DD checklist, contacts, or scoring would have these injected — preventing re-debate or wrong defaults. Concrete: "Don't create separate Memo and DealResearchDoc — they're merged."

#### tech-stack-completed.md — 5/5 DISTRIBUTE
- **Evidence**: Commit `103ddd5a` (Abhishek + Claude Code, 2026-04-07T05:19). Corroborated by Abhishek's LangSmith traces showing active tech stack deliberations same day (Nango, integrations, compliance discussions).
- **Uniqueness**: Supersedes `active-tech-stack-decisions.md` (now RESOLVED/pointer). This is the authoritative final reference with rationale for every service choice.
- **Actionability**: Highest-value entry for new team members or anyone starting backend work. Would prevent wrong service choices (Vercel instead of Coolify, Prisma instead of Drizzle, tRPC instead of PostgREST).

#### fsd-audit-critical-issues.md — 5/5 DISTRIBUTE
- **Evidence**: Ankit-S LangSmith traces 2026-04-07 show 1.58M token session on ARCHITECTURE-AUDIT.md + fix-playbook.md. Source commit `041ba65b`. Ankit-S actively running through fix-playbook confirms these issues are real and being worked.
- **Uniqueness**: No existing entry documents FSD layer violations, specific violating files, or the DealResearchRepo wiring gap.
- **Actionability**: Would inject into any session touching FSD layers or shared/. Prevents recreating the exact violation: "Before adding shared imports from widgets/, check — this is the #1 critical issue."
- **Note for synthesis agent**: The 4 critical issues will be resolved by Ankit-S over coming days. This entry should be updated or archived once fix-playbook.md is complete.

#### patterns/competitor-research-dataset.md — 5/5 DISTRIBUTE
- **Evidence**: PR #40 merged with 171 files (da982b71, Saurabh Thapa). Irrefutable.
- **Uniqueness**: No entry captures the competitor research dataset existence or how to use it.
- **Actionability**: When someone writes Maverick marketing copy, positioning docs, or feature comparisons, this entry injects the dataset reference — preventing work from scratch when 11 days of research already exists.

#### patterns/cross-agent-monitoring.md — 5/5 DISTRIBUTE
- **Evidence**: Ankit-S traces runs #8, #9 (13:02-13:08 UTC): explicit requests to "Check every 60 seconds what it is doing" and "Do I have to ask you every 120 seconds? Or will you do by yourself". Pattern is real and deliberate.
- **Uniqueness**: No existing entry covers JSONL file watching for cross-agent monitoring.
- **Actionability**: When someone sets up a multi-agent autonomous task, this entry injects the file path pattern, interval guidance, and pitfalls. Changes behavior from "you'll need to poll manually" to "set up Agent A to monitor Agent B's JSONL."
- **Note for synthesis agent**: Confidence is LOW (one person, one session). Promote to MEDIUM once a second team member independently discovers this pattern.

#### patterns/issue-as-agent-scratchpad.md — 5/5 DISTRIBUTE
- **Evidence**: Two explicit turns from Kshitiz (run #10: "yes. and in your journey keep using issues as writing pad"; run #2: "yes let's test everything thoroughly, keep using issues as writing pad"). User-initiated and repeated.
- **Uniqueness**: Distinct from `issue-driven-research-tracking.md`. That pattern is about task ledgering (one issue = one research task, close = done). This pattern is about in-session memory (comments as agent working memory). Different purpose, different application.
- **Actionability**: Would inject into agent orchestration sessions: "write intermediate state to GitHub Issues as comments to survive compaction."

#### anti-patterns/ai-generated-doc-quality.md — 4/5 DISTRIBUTE
- **Evidence**: 1 — Sahil trace run #5 (13:11 UTC): "All the documentation...whether it be regarding frontend/gaps/audit, most of it is just done by AI." Single turn, clear signal.
- **Risk**: 0 — Single person's opinion about document quality. Sahil may be right, but it's not verifiable from this alone. Marking AI audit docs as unreliable on one person's observation carries risk of over-correction (undermining legitimate audit work done by Ankit-S).
- **Decision**: DISTRIBUTE at 4/5. The advice is directionally correct and properly caveated as LOW confidence in the entry itself.
- **Promotion condition**: A second team member (Abhishek, Pranav, Ankit-S) independently flags quality issues with AI-generated docs. At that point, raise confidence to MEDIUM.

#### rule: category-filtering-context.md — 4/5 DISTRIBUTE
- **Level-0 check**: 4 correction turns from Pranav (runs 7-10, 12:29-12:34 UTC). Meets the 3+ correction turn threshold for single-person evidence.
- **Evidence**: 1 — explicit trace evidence. ~112K tokens wasted on 4 successive corrections about system vs org category filtering in copilot rules system.
- **Risk**: 0 — rule addresses a specific domain context (copilot rules system with system/org category distinction). As a universally-loaded rule, it could inject unnecessary "are you sure which category type?" prompts into unrelated contexts. Rule header appropriately flags this: "needs corroboration before treating as universal rule."
- **Decision**: DISTRIBUTE at 4/5. Meets threshold. The rule is well-bounded ("when multiple category types coexist") and includes a self-limiting condition. Risk is accepted given the threshold was met.
- **Promotion condition**: Second team member encounters system vs org (or analogous multi-type) category confusion. At that point, remove the LOW confidence caveat and treat as general rule.

---

### Notes for Synthesis Agent

1. `fsd-audit-critical-issues.md` is time-sensitive — will be resolved by Ankit-S. Set a review checkpoint for next cycle.
2. `ai-generated-doc-quality.md` and `cross-agent-monitoring.md` are both LOW confidence (single observation). Prioritize finding second signals for these in next ingest cycle.
3. No discards this cycle. This is expected for a system in early operation — signal quality from the team is high. Watch for this to change as the knowledge base grows and redundancy increases.
4. Rule creation threshold was met (4 corrections ≥ 3). However, no rules were promoted from HOLD this cycle because none were held. First draft of this rule goes straight to distribution — monitor for overcautious injection in unrelated contexts.
