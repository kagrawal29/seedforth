---
id: tool-config-langsmith-tracing
category: tool-configs
discovered: 2026-04-06
last-validated: 2026-04-06
confidence: high
type: knowledge
source: https://docs.langchain.com/langsmith/trace-claude-code — official LangSmith docs
distributed-to: []
effectiveness: positive
metrics:
  surfaced_count: 4
  cited_count: 1
  correction_after: 0
  effectiveness_score: 0.25
  last_scored: 2026-04-12
tags: [langsmith, tracing, telemetry, monitoring, plugin, api-key, settings-local, debugging]
relevant-when: setting up LangSmith tracing, debugging trace issues, onboarding new team members, checking if traces are flowing
related: [tool-config-auto-sync-hooks, tool-config-hooks-data-capture, tool-config-rules-loaded-telemetry]
---

# LangSmith Tracing for Claude Code

## What
Full telemetry for every Claude Code session -- messages, tool calls, compaction events, subagent runs. Visible in LangSmith dashboard with thread grouping.

## Why
Cross-team visibility into who is active, what tools are used, and where people get stuck. Required for meta agent coordination signals.

## Procedure
1. Install the plugin (run inside Claude Code):
   ```
   /plugin marketplace add langchain-ai/langsmith-claude-code-plugins
   /plugin install langsmith-tracing@langsmith-claude-code-plugins
   /reload-plugins
   ```
2. Get a LangSmith API key from https://smith.langchain.com/settings/apikeys (format: `lsv2_pt_...`)
3. Create `.claude/settings.local.json` in project root:
   ```json
   {
     "env": {
       "TRACE_TO_LANGSMITH": "true",
       "CC_LANGSMITH_API_KEY": "<your-key>",
       "CC_LANGSMITH_PROJECT": "maverick-residency",
       "CC_LANGSMITH_DEBUG": "true"
     }
   }
   ```
4. If migrating from manual hooks, remove `~/.claude/hooks/stop_hook.sh` first
5. Start a new Claude Code session and send any message
6. Check the LangSmith dashboard -- a new trace should appear within seconds

## Pitfalls
- What breaks: API key committed to git. Detection: `git diff` shows key in tracked file. Fix: `.claude/settings.local.json` is gitignored by default -- never rename or move it.
- What breaks: Different project names across team. Detection: traces scattered across projects. Fix: everyone MUST use `maverick-residency` as project name.
- What breaks: Old manual hooks conflict with plugin. Detection: duplicate or missing traces. Fix: delete `~/.claude/hooks/stop_hook.sh` before installing plugin.
- What breaks: No traces appearing. Detection: dashboard empty after sending messages. Fix: check `tail -f ~/.claude/state/hook.log` for errors.

## Verification
- [ ] `.claude/settings.local.json` exists and is NOT tracked by git (`git status` shows no mention)
- [ ] After sending a message, a trace appears in the LangSmith `maverick-residency` project
- [ ] Trace shows user message, tool calls, and assistant response (NOT system prompts)
- [ ] Multiple turns are grouped under one thread in the Threads tab

## Evidence
- Deployed to full residency team (12-15 people)
- System prompts confirmed NOT captured (privacy preserved)
