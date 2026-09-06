---
id: tool-config-auto-sync-hooks
category: tool-configs
discovered: 2026-04-06
last-validated: 2026-04-10
confidence: high
type: knowledge
source: maverick-meta — PostToolUse hook tested end-to-end, deployed to 13 branches across 2 repos
distributed-to: [VC-AI-Assoicate, maverick-market-research]
effectiveness: neutral
metrics:
  surfaced_count: 8
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.00
  last_scored: 2026-04-09
tags: [hooks, git, push, pull, rebase, auto-sync, post-tool-use, session-start, session-pull, settings-json]
relevant-when: setting up git auto-sync, configuring Claude Code hooks, troubleshooting push/pull issues, fixing delivery gap for distributed knowledge
related: [tool-config-hooks-data-capture, tool-config-langsmith-tracing, tool-config-rules-loaded-telemetry]
---

# Auto-Sync Hooks for Invisible Git Push/Pull

## What
Two complementary hooks that keep branches synced without manual intervention:
1. **PostToolUse hook** (auto-sync.sh): Runs `git pull --rebase --autostash && git push` after every `git commit`
2. **SessionStart hook** (session-pull.sh): Runs `git pull` at session start, ensuring agents load the latest distributed knowledge before anything else

## Why
Team members forget to push, causing invisible work. Manual push is friction that reduces commit frequency. Rebase+autostash handles concurrent changes cleanly.

## Procedure
1. Create the hook script at `.claude/hooks/auto-sync.sh`:
   - Read stdin JSON for the Bash command that was executed
   - Check if command contains `git commit`
   - If yes: run `git pull --rebase --autostash && git push`
   - If no: exit 0 silently
2. Make it executable: `chmod +x .claude/hooks/auto-sync.sh`
3. Add the hook to `.claude/settings.json`:
   ```json
   {
     "hooks": {
       "PostToolUse": [
         {
           "matcher": "Bash",
           "hooks": [
             {
               "type": "command",
               "command": "bash .claude/hooks/auto-sync.sh"
             }
           ]
         }
       ]
     }
   }
   ```
4. Test: make a commit and verify it appears on the remote within seconds
5. Deploy to other repos/branches via `scripts/deploy-auto-sync.sh`

## Pitfalls
- What breaks: Hook fires on ALL Bash commands, not just commits. Detection: high latency on non-git commands. Fix: script must exit 0 immediately when command is not `git commit`.
- What breaks: Rebase conflicts on divergent branches. Detection: push fails after pull. Fix: use `--autostash` flag and ensure branches don't have long-lived divergence.
- What breaks: Hook not executable. Detection: commits succeed but nothing pushes. Fix: `chmod +x .claude/hooks/auto-sync.sh`.
- What breaks: Session-pull hook removed during settings.json merge conflict. Detection: `git diff` shows SessionStart hooks array missing session-pull entry. Fix: When resolving settings.json conflicts, manually verify all hook entries survive the merge. This happened on 2026-04-10 when Abhishek accepted remote settings.json changes that didn't include the session-pull hook. The hook must be re-added after such conflicts.

## Verification
- [ ] After a commit, `git log origin/main` shows the commit on remote
- [ ] Non-commit Bash commands (e.g., `ls`) complete with zero added latency
- [ ] Remote changes from another user are pulled in on next local commit

## Session-Pull Hook (added 2026-04-10)

The delivery gap problem: distributed knowledge (rules, community-map, entries) was pushed to repos but agents didn't pick it up until someone manually pulled. The session-pull hook fixes this by running `git pull` at SessionStart — before rules or knowledge load.

Add to `.claude/settings.json`:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/session-pull.sh",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

The `session-pull.sh` script runs `git pull --rebase --autostash` silently. Deployed to both VC-AI-Assoicate and maverick-market-research on 2026-04-10 (commits b9186b9b, 415ab418).

## Evidence
- Tested end-to-end on maverick-meta: local commit auto-pushed, remote changes auto-pulled
- Deployed to 13 branches via `scripts/deploy-auto-sync.sh`
- Session-pull hook added 2026-04-10: commits b9186b9b (VC-AI-Assoicate), 415ab418 (maverick-market-research)
- Delivery verification (2026-04-10): only Kshitiz confirmed receiving rules. Session-pull hook expected to improve delivery visibility in next cycle.
