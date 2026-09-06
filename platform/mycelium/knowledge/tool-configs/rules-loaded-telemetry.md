---
id: tool-config-rules-loaded-telemetry
category: tool-configs
discovered: 2026-04-09
last-validated: 2026-04-10
confidence: high
type: procedure
version: 1
source: maverick-meta — built to close delivery verification gap discovered when checking Sahiram's traces
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.00
  last_scored: 2026-04-09
tags: [hooks, session-start, telemetry, langsmith, rules, delivery-verification, distribution]
relevant-when: verifying rule delivery to team members, debugging whether distributed knowledge was loaded, checking adoption of shared rules
related: [tool-config-auto-sync-hooks, tool-config-langsmith-tracing]
---

# Rules-Loaded Telemetry Hook

## What
SessionStart hook that posts a manifest of loaded `.claude/rules/`, `.claude/knowledge/`, `.claude/skills/`, and `.claude/hooks/` to LangSmith as a custom `rules-loaded` run. Enables the meta system to verify delivery without access to team members' machines.

## Why
Distribution is push-only — we push rules to branches via GitHub API, and auto-sync pulls them on commit. But LangSmith traces don't capture the system prompt, so we had no way to verify rules were actually loaded into a session. This hook closes that gap.

## Procedure
1. Hook script at `.claude/hooks/rules-loaded.py`:
   - Globs `.claude/rules/*.md`, `.claude/knowledge/entries/**/*.md`, `.claude/skills/*/SKILL.md`, `.claude/hooks/*`
   - Resolves LangSmith project UUID from `CC_LANGSMITH_PROJECT` env var
   - Posts a custom run with `name: "rules-loaded"`, manifest in `inputs.manifest`
   - Prints summary to stdout for session start output
2. Wired in `.claude/settings.json` under `SessionStart`:
   ```json
   {"matcher": ".*", "hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/rules-loaded.py", "timeout": 10}]}
   ```
3. Distributed via `push-knowledge.sh` which pushes the hook file + patches settings.json

## Querying rules-loaded traces
```python
body = {
    "session": [project_uuid],
    "limit": 5,
    "filter": 'eq(name, "rules-loaded")',
    "select": ["start_time", "inputs", "outputs"]
}
# inputs.manifest.rules = list of rule filenames
# inputs.manifest.knowledge_entries = list of knowledge entry filenames
# inputs.manifest.rules_count / knowledge_count = counts
```

## Pitfalls
- What breaks: `CC_LANGSMITH_API_KEY` or `CC_LANGSMITH_PROJECT` not set. Detection: no rules-loaded traces appear. Fix: ensure `.claude/settings.local.json` has both env vars.
- What breaks: Hook blocks session start on API timeout. Detection: slow session startup. Fix: 5s timeout on urllib + blanket try/except that exits 0.
- What breaks: Knowledge entries glob returns 0 on repos without `.claude/knowledge/`. Detection: `knowledge_count: 0` in manifest. Fix: expected for repos that haven't received knowledge push yet.

## Current Delivery Status (2026-04-10)
- Kshitiz: WORKING — 10 rules, 0 KB entries, 11 skills loaded (trace from 2026-04-09T12:42Z)
- Sahiram: UUID ERROR — 404, project UUID in config may be incorrect
- Abhishek, Ankit-S, Sahil, Pranav: NO DATA — hook not yet configured in their sessions
- Delivery verification coverage: 1/6 members (17%)
- Action needed: push rules-loaded hook to remaining team members' settings.json

## Verification
- [ ] After starting a new Claude Code session, a `rules-loaded` run appears in LangSmith
- [ ] The manifest lists the exact `.claude/rules/*.md` files present on the branch
- [ ] The hook completes in <5s and never blocks session startup
- [ ] `/ingest` can query and parse rules-loaded traces to verify delivery
