# System Effectiveness

Tracking how well the meta-intelligence system is performing.

## Metrics
- **Adoption rate**: 2/5 rules show clear adoption (git-workflow strong, maverick-residency moderate)
- **Signal-to-insight ratio**: 940 signals -> 22 knowledge entries (2.3%) — improved after Phase 3
- **Cross-pollination hits**: 0 — biggest failure. Sahiram's findings not reaching Abhishek.
- **Time-to-distribution**: Rules: ~2h from synthesis to all branches. Knowledge entries: NOT YET DISTRIBUTED.

## Retro 1 — 2026-04-06 (Day 0, ~2h post-distribution)

### What works
- **Observable-action rules get adopted.** Git-workflow prescribes specific actions (branch, commit, push) that are easy to verify and follow. 3/5 active contributors showing adoption.
- **Push-to-all-branches delivery works.** Rules land on every branch without requiring manual pulls.
- **Trace monitoring works.** We can see who's active, what they're working on, and whether they're pushing.

### What doesn't work
- **Behavioral/tone rules are unverifiable.** "Be articulate about failures" is indistinguishable from Claude's default behavior. We can't measure adoption.
- **Knowledge entries aren't reaching people.** 11 entries synthesized, 0 distributed. The most valuable insights are stuck in this repo.
- **No cross-pollination.** Sahiram found critical tech stack intel (Trigger.dev dead, Zep unreliable, Voyage AI ownership). Abhishek is choosing tech stack independently. We haven't connected them.
- **Cost-optimization and research-tools rules show no adoption signal.** Too early or not relevant to current work.

### System changes needed
1. **Prioritize capability rules over behavioral rules.** Observable > aspirational.
2. **Distribute knowledge entries as GitHub issues.** Rules are generic guidance; issues are specific, actionable, and visible in the repo where people work.
3. **Cross-pollinate actively via issues.** When person A discovers something person B needs, create an issue in person B's repo immediately.
4. **Add a "who needs this" field to knowledge entries.** Route insights to specific people, not broadcast.
5. **Track adoption with commit-level evidence, not trace analysis.** Commits are the ground truth.

---

## Feedback Cycle 1 — 2026-04-07 (Smart-Context Hook, First 3 Injections)

### What was scored
Hook deployed 2026-04-07. First day of operation. 3 injection events recorded, covering 5 unique entry/injection pairs.

| Entry | Injections | Outcome | Score | Band |
|-------|-----------|---------|-------|------|
| architecture/memory-layer-decisions.md | 2 | IGNORED ×2 | 0.00 | MONITOR |
| anti-patterns/zep-cloud-reliability.md | 1 | IGNORED ×1 | 0.00 | MONITOR |
| tool-configs/auto-sync-hooks.md | 1 | NEUTRAL ×1 | 0.00 | MONITOR |
| tool-configs/langsmith-tracing-setup.md | 1 | HELPED ×1 | 1.00 | AMPLIFY* |
| patterns/claude-code-agent-as-primary-builder.md | 1 | IGNORED ×1 | 0.00 | MONITOR |

*AMPLIFY is tentative — N=1 injection is not statistically meaningful. Re-score after 5+ injections.

### Correlation methodology
- Injection timestamps matched against nearest LangSmith root traces (Kshitiz project: ce70362b)
- All 3 injection events are from Kshitiz's session (other team members don't have the hook deployed yet)
- "pending" traces (0 tokens) are sub-agents or in-flight turns — not assessable for outcome
- Outcome classification based on whether injected content was relevant to the tool call context

### Key finding: Relevance mismatch in injection 3
Injection 3 (13:32:13): Glob `knowledge/meta/**` triggered `zep-cloud-reliability` and `memory-layer-decisions`.
The glob was browsing meta system files (cycle-log.md, system-effectiveness.md), NOT making memory/database decisions.
Root cause: the word "knowledge" in the path matched entry tags, not the intent of the tool call.
**Recommendation**: Tighten `relevant-when` clauses on database/architecture entries to exclude path-navigation contexts. Or add a path-context filter to the smart-context hook.

### Key finding: Multi-entry injection dilution
Injection 2 (13:21:54): 3 entries injected when reading settings.local.json. Only 1 (langsmith-tracing-setup) was directly relevant. The other 2 (auto-sync-hooks, claude-code-agent-as-primary-builder) added noise. When 3 entries are injected simultaneously, only the most relevant tends to get used — the others are ignored.
**Recommendation**: Cap injection at 2 entries per event; prefer the single most relevant entry over a broad match.

### No hurt signals detected
Zero injections caused corrections or errors. System is not actively harming sessions — failure mode is irrelevance (ignored), not misdirection (hurt).

---

## Detected Gaps — 2026-04-07

Signals from team traces suggesting missing knowledge entries:

### Gap 1: Copilot category filtering (Pranav, medium confidence)
Pranav made 4+ correction turns on the same category filtering error in `RuleEditor.tsx`. No existing entry covers this workflow. Observed pattern: agent adds unsolicited features (e.g., setting executionMode defaults without being asked).
- Proposed entry: `patterns/prompt-constraint-driven-ui-development.md` — how to write prompts that scope agent work to exactly what's requested, preventing scope creep in UI feature work.

### Gap 2: Browser/mock ESLint boundary (Ankit-S, low confidence)
Ankit-S: "Browser service files can't import from mocks (ESLint rule) — use inline implementations instead." This is a VC-AI-Associate–specific constraint that other contributors working on that codebase will hit.
- Proposed entry: `anti-patterns/browser-service-mock-imports.md` — codebase-specific ESLint boundary that prevents direct mock imports in browser service files.

### Gap 3: Nango CRM integration specifics (Abhishek, low confidence)
Abhishek deep in Nango research: DealCloud not in pre-built catalog, requires custom integration. We have an exploration entry for Nango but no settled procedure or anti-pattern.
- Proposed entry: update `exploration-nango-integration.md` with finding: DealCloud = custom integration, not catalog. Zeplin/standard VC CRMs = catalog. Mark as medium confidence when Abhishek commits integration code.

### Gap 4: Market research repo architecture (Sahil, low confidence)
Sahil doing architecture strategy discussions for the market research repo ("not a great fit" for agent patterns). No knowledge entry exists for market-research–specific patterns.
- Proposed entry: `architecture/market-research-repo-patterns.md` — defer until Sahil commits architectural decisions.

### Gap 5: Injection path-context filter (system gap)
Not a team knowledge gap — a system improvement. The smart-context hook should not trigger database/architecture entries when the tool call is a file-path navigation (Glob/Read of paths containing "knowledge", "meta", "config"). These path strings are structural, not semantic.
- Proposed fix: add path-context filter to `.claude/hooks/smart-context.py` — skip injection when query is a file path and path doesn't match the entry's domain keywords.

---

## Overall System Health — 2026-04-07

**Status: EARLY / COLLECTING DATA**

- Hook deployed and firing correctly ✓
- Zero hurt signals ✓
- Relevance quality: 2/5 injections were well-matched (40%) — needs improvement
- Injection volume: too low (3 events) for statistical conclusions
- Other team members: hook not yet deployed to them — all 3 events are Kshitiz-only
- Next action: deploy hook to 2-3 other team members; re-score after 20+ injection events

---

## Feedback Cycle 2 — 2026-04-09 (Full day 2026-04-07, 25 injection events)

### What was scored

25 injection events, 13 unique entries across 6 categories. All events from Kshitiz's session (other members don't have hook deployed).

| Entry | Total Inj | Helped | Ignored | Score | Band |
|-------|-----------|--------|---------|-------|------|
| architecture/memory-layer-decisions.md | 18 | 0 | 18 | 0.00 | MONITOR |
| anti-patterns/zep-cloud-reliability.md | 15 | 0 | 15 | 0.00 | MONITOR |
| tool-configs/auto-sync-hooks.md | 8 | 0 | 8 | 0.00 | MONITOR |
| tool-configs/claude-code-hooks-for-data-capture.md | 6 | 0 | 6 | 0.00 | MONITOR |
| patterns/claude-code-agent-as-primary-builder.md | 5 | 0 | 5 | 0.00 | MONITOR |
| patterns/issue-driven-research-tracking.md | 4 | 0 | 4 | 0.00 | MONITOR |
| tool-configs/langsmith-tracing-setup.md | 3 | 1 | 2 | +0.33 | MONITOR (trending up) |
| patterns/research-driven-architecture-decisions.md | 3 | 0 | 3 | 0.00 | MONITOR |
| architecture/research-to-product-pipeline.md | 2 | 0 | 2 | 0.00 | MONITOR |
| architecture/active-tech-stack-decisions.md | 1 | 0 | 1 | 0.00 | MONITOR |
| architecture/trigger-dev-vs-temporal.md | 1 | 0 | 1 | 0.00 | MONITOR |
| patterns/competitor-research-dataset.md | 1 | 0 | 1 | 0.00 | MONITOR |
| anti-patterns/keyword-search-noise.md | 1 | 0 | 1 | 0.00 | MONITOR |

**Thresholds:** 0 entries to AMPLIFY, 0 to REVIEW, 0 to REMOVE. All MONITOR.

### Critical finding: 80% of injections are from automated agent sessions

Of the 25 injection events, **20 occurred during the feedback agent's own execution** (13:32–13:39). The hook fires on every tool call including sub-agent invocations. Automated agents reading knowledge files trigger injections for entries that have zero relevance to their task.

**Breakdown:**
- 20 events (80%): feedback agent running its own file reads
- 3 events (12%): human session (real work)
- 2 events (8%): CLAUDE.md reads during self-assessment

**Human-session-only effectiveness:** 1 helped / 5 injections = 20%

This inflates injection counts while suppressing effectiveness scores toward 0. The scores are misleading — they mix "hook didn't help an agent doing meta work" with "hook didn't help a human doing product work."

### Critical finding: In-session confirmation of hook noise

The trace at 2026-04-07T14:23:59 (Kshitiz's A/B test session) contains a direct result: **"19 injections, all noise, zero useful. The hook fires on every tool call..."** This is the clearest possible signal — the user ran an explicit test and confirmed the hook was noisy.

Root cause confirmed: the hook triggers on path-navigation tool calls (Glob/Read of knowledge files) and sub-agent sessions that aren't making the kind of decisions the injected knowledge addresses.

### Finding: langsmith-tracing-setup is the only entry with positive signal

1/3 injections helped (33%) at N=3. The HELP case: reading settings.local.json while setting up LangSmith ingestion — the entry was directly applicable. Still N=3 (not statistically meaningful). Keep as MONITOR, watch for 5+ injections in human-only sessions.

### No hurt signals (second consecutive cycle)

Zero cases where an injection caused Claude to give wrong information or led to a user correction. The failure mode remains irrelevance (ignored), not misdirection (hurt). Safe to keep running.

---

## Detected Gaps — 2026-04-09

### Gap 1: Agent session detection (system gap — HIGH priority)
The hook has no mechanism to distinguish human sessions from automated sub-agent sessions. Sub-agent prompts start with "You are the [role] agent..." or contain `<task-notification>` tags. Injecting architecture facts to a feedback agent reading its own data files is pure noise.
- Proposed fix: add agent-session filter to `.claude/hooks/smart-context.py` — if the most recent user message starts with "You are the" or "You are continuing work" (Agent SDK invocations), skip injection entirely.

### Gap 2: Self-referential injection (system gap — MEDIUM priority)
When reading `knowledge/architecture/memory-layer-decisions.md`, the hook injects `memory-layer-decisions.md`. Claude already has the content it's about to read. The injection is redundant. Same pattern for most injections 10-22.
- Proposed fix: if the tool query path contains the entry's filename, skip that entry.

### Gap 3: A/B test harness pattern (positive finding)
Kshitiz built an Agent SDK–based A/B test harness to evaluate hook effectiveness (traces 14:14-14:46). Two agents ran with and without context injection on the same codebase. This is a reusable pattern for evaluating any system change.
- Proposed entry: `patterns/agent-sdk-ab-test-harness.md` — how to structure A/B tests for Claude Code system changes using Agent SDK. Low confidence (1 session), defer creation until pattern recurs.

### Gap 4: Heimdall evaluation agent (positive finding)
The trace at 13:53:02 shows the design and deployment of "Heimdall" — an evaluation agent that gates knowledge entries between synthesis and distribution. This is now in production but no knowledge entry describes its role, criteria, or failure modes.
- Proposed entry: `patterns/heimdall-evaluation-gate.md` — quality gate between synthesis and distribution. Already deployed, medium confidence.

---

## Systemic Recommendations — 2026-04-09

1. **Add agent session detection to smart-context.py** — highest impact fix, eliminates 80% of false-fire injections
2. **Add self-referential path filter** — prevents injecting entries when the tool is reading that file itself
3. **Deploy hook to Pranav or Abhishek** — all current data is Kshitiz-only. Need other members to get meaningful cross-session effectiveness data
4. **Do not amplify any entry yet** — no entry has N>=5 human-session injections. Not enough data.
5. **langsmith-tracing-setup.md is the closest to useful** — watch this one specifically; if it reaches 5+ human-session injections with >30% helped rate, AMPLIFY

## Overall System Health — 2026-04-09

**Status: NOISE PROBLEM IDENTIFIED, FIX IN PROGRESS**

- Hook firing correctly ✓
- Zero hurt signals (2 consecutive cycles) ✓
- Noise identified and root-caused: agent sessions + self-referential reads ✓
- Relevance quality: 1/5 human injections helped (20%) — low but not alarming given N=5
- In-session A/B test confirms noise problem ✓
- No entries meeting REMOVE threshold ✓
- Critical action: implement agent-session filter before next cycle

---

## Feedback Cycle 3 — 2026-04-12 (Traces 2026-04-10 to 2026-04-12)

### Data coverage
- **Members with rules-loaded hook:** Sahiram, Ankit-S, Sahil (37 entries each)
- **Members without rules-loaded hook:** Abhishek, Kshitiz, Pranav — ZERO delivery
- **Traces analyzed:** ~64 substantive turns across 5 active members (Pranav minimal)
- **Scoring method:** Keyword surfacing in sessions where entry was confirmed loaded

### Entry scores this cycle

| Entry | Sessions | Surfaced | Cited | Correction | Score | Band |
|-------|---------|----------|-------|-----------|-------|------|
| competitor-research-dataset.md | Sahil ×3 | 3 | 0 | 0 | 0.00 | MONITOR |
| spec-reading-guides.md | Sahiram ×1, Ankit-S ×1 | 2 | 0 | 0 | 0.00 | MONITOR |
| phase1-decisions-settled.md | Sahiram ×2, Ankit-S ×2 | 4 | 0 | 0 | 0.00 | MONITOR |
| tech-stack-completed.md | Sahiram ×3 | 3 | 0 | 0 | 0.00 | MONITOR |
| configurable-per-fund-pattern.md | Ankit-S ×1, Sahil ×1 | 2 | 0 | 0 | 0.00 | MONITOR |
| langsmith-tracing-setup.md | Sahil ×1 | +1 (total 4) | 0 (total 1) | 0 | 0.25 | MONITOR |
| trigger-dev-vs-temporal.md | Kshitiz ×1 (not loaded!) | — | — | — | DELIVERY GAP |
| memory-layer-decisions.md | Sahiram ×1 | 1 | 0 | 0 | 0.00 | MONITOR |

**Thresholds:** 0 entries to AMPLIFY, 0 to REVIEW, 0 to REMOVE. All MONITOR.

### Critical finding 1: Delivery collapse for 3 members

Abhishek, Kshitiz, and Pranav have ZERO rules-loaded traces. All knowledge entries are invisible to them. These are among the most active contributors:
- **Abhishek:** Heavy speckit/spec-to-ship work. 8+ entries directly applicable. Zero delivery.
- **Kshitiz:** Graph topology and user journey work. 5+ entries applicable. Zero delivery.
- **Pranav:** Lighter usage but onboarding context would help.

**This is the highest-impact failure in the system.** All surfacing data from Cycles 1-3 is Sahiram/Ankit-S/Sahil/Kshitiz-weighted.

### Critical finding 2: 11 entries missing from manifest (23% of knowledge base invisible)

The rules-loaded manifest contains 37 entries. The knowledge base has 48 entries. 11 newer entries are never delivered:

| Entry | Most relevant to | Why it matters |
|-------|-----------------|----------------|
| spec-tech-separation.md | Sahiram (active spec debate) | Directly answered a question; wasn't loaded |
| lp-reporting-pain-profile.md | Sahil (LP = #1 pain cluster) | Independently validated by Sahil's research |
| mcp-streamable-http-auth.md | Ankit-S (implemented independently) | Ankit-S updated MCP config without entry context |
| spec-to-ship-v8-superpowers.md | Ankit-S, Sahiram | v8 published; entry should reinforce patterns |
| spec-isolation-principle.md | Ankit-S, Sahiram | Active workflow |
| cypher-native-pipeline.md | Kshitiz | Active work |
| graph-native-identity.md | Kshitiz | Active work |
| emerging-manager-solo-gp-segment.md | Kshitiz | Solo GP found to have 0 product coverage |
| vc-ai-market-ground-truth.md | Sahil | Market research context |
| vibe-coding-threat-assessment.md | All | Risk awareness |
| doc-to-graph-llm-boundary.md | Kshitiz | Graph work |

### Critical finding 3: Rules volume causing measurable latency

Abhishek's direct complaint (2026-04-11T13:10:31): _"Why are you taking so much time to generate an output? Is it because too many rules are there?"_
Claude confirmed: yes. With 37 entries loaded, response latency is noticeable to users.

**Implication:** The system is growing its knowledge base while delivery capacity is degrading performance. Net harm possible if not addressed.

### Positive finding: LP Reporting independently validated

Sahil's market research knowledge graph (2026-04-11) ranks LP Reporting as the **#1 pain density cluster** with 6 pain mentions — independently confirming `lp-reporting-pain-profile.md`. Two independent data sources converging on the same conclusion: high confidence that this entry is accurate. Once delivered, expect AMPLIFY.

### Positive finding: Spec-tech-separation correct even without delivery

Sahiram asked about "no tech in specs" rule (2026-04-11). Despite `spec-tech-separation.md` NOT being loaded, Claude gave the correct answer (aligned with entry). The entry's factual content is Claude-native knowledge; its distinct value is the Cross-Person Note ("Sahiram researched this, cite their work when the debate resurfaces with others").

### Positive finding: Spec-to-ship v8 published

Ankit-S committed spec-to-ship v8 (e57b16d1) with rules 16/17/18 added (reading guides, completion evidence, bite-sized tasks). This is direct evidence that `spec-reading-guides.md` is being adopted in practice — even if we can't confirm Claude cited the entry.

### New gaps proposed (in feedback-proposals.md)
1. **Solo GP product coverage gap** (HIGH) — Kshitiz found Solo GP reaches 0 screens. Immediate strategic implication.
2. **Rules volume latency anti-pattern** (HIGH) — Abhishek's direct complaint. System is degrading its own performance.
3. **Speckit sync-conflicts merge process** (MEDIUM) — Abhishek's multi-agent merge process.
4. **Multi-provider LLM routing** (MEDIUM) — Sahil exploring AI SDK multi-provider.
5. **Graph breathe/crystallization pattern** (LOW) — Kshitiz experimental graph work.

---

## Overall System Health — 2026-04-12

**Status: DELIVERY CRISIS — 3 MEMBERS UNHOOKED, 23% OF ENTRIES UNDELIVERED**

- Rules-loaded hook firing for Sahiram, Ankit-S, Sahil ✓
- Abhishek, Kshitiz, Pranav: zero delivery ✗ ← CRITICAL
- 11 of 48 entries not in manifest ✗ ← CRITICAL
- Zero hurt signals (3 consecutive cycles) ✓
- Surfacing rate: ~15 surfacings across loaded entries, 0 explicit citations — acceptable for this stage
- Latency complaint: 1 direct user report (Abhishek) — rules volume overhead confirmed ✗
- langsmith-tracing-setup.md continues as highest-scoring entry (0.25, N=4) — only entry with positive trajectory

**Actions for Heimdall:**
1. Deploy rules-loaded hook to Abhishek, Kshitiz, Pranav
2. Update rules-loaded manifest to include all 48 entries (or auto-discover)
3. Consider reducing manifest size to address latency — implement relevance scoring
4. Create `anti-patterns/rules-volume-latency.md` (Gap N2)
5. Create `patterns/solo-gp-product-coverage-gap.md` (Gap N1) — high urgency
