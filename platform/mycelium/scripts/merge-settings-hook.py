#!/usr/bin/env python3
"""
Reads existing settings.json from stdin, adds auto-sync PostToolUse hook,
outputs merged JSON. Idempotent — won't add if already present.
"""
import json
import sys

HOOK_ENTRY = {
    "matcher": "Bash",
    "hooks": [
        {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/auto-sync.sh",
            "timeout": 30
        }
    ]
}

existing = sys.stdin.read().strip()
try:
    settings = json.loads(existing) if existing else {}
except json.JSONDecodeError:
    settings = {}

if "hooks" not in settings:
    settings["hooks"] = {}

if "PostToolUse" not in settings["hooks"]:
    settings["hooks"]["PostToolUse"] = []

# Check if auto-sync already present
already = False
for entry in settings["hooks"]["PostToolUse"]:
    for h in entry.get("hooks", []):
        if "auto-sync" in h.get("command", ""):
            already = True

if not already:
    settings["hooks"]["PostToolUse"].append(HOOK_ENTRY)

print(json.dumps(settings, indent=2))
