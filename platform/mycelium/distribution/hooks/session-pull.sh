#!/bin/bash
# SessionStart hook: pull latest from remote before rules load.
# This ensures every new session has the latest knowledge, rules, and context.
# Silent on failure — never blocks session start.
cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || exit 0
git pull --rebase --autostash --quiet 2>/dev/null || true
