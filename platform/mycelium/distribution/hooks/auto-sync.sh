#!/bin/bash
# Auto-sync hook: runs after Bash tool use
# If the command was a git commit, pull (to get latest rules) then push
# Designed to be silent and non-disruptive

# Read hook input from stdin
INPUT=$(cat)

# Extract the command that was run
COMMAND=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

# Only act on git commit commands
echo "$COMMAND" | grep -q "git commit" || exit 0

# Small delay to let the commit finish cleanly
sleep 0.5

# Pull latest (brings in new rules from meta system)
git pull --rebase --autostash 2>/dev/null

# Check if pull left us in a mid-rebase state (conflict)
# Exit code alone is unreliable — check for rebase directory
if [ -d ".git/rebase-merge" ] || [ -d ".git/rebase-apply" ]; then
    # Conflict: abort rebase to restore clean state, skip push
    git rebase --abort 2>/dev/null || true
    exit 0
fi

# Clean pull succeeded — push (with upstream tracking if needed)
git push 2>/dev/null || git push -u origin HEAD 2>/dev/null || true
