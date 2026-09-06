#!/usr/bin/env python3
"""Patches a repo's .claude/settings.json to include the rules-loaded SessionStart hook.
Merges non-destructively — preserves existing hooks, only adds if not already present.

Usage: Called by push-knowledge.sh for each repo/branch.
  python3 scripts/patch-settings-hooks.py <current-settings-json-string>
  Outputs the patched JSON to stdout.
"""

import json
import sys

RULES_LOADED_HOOK = {
    "matcher": ".*",
    "hooks": [
        {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/rules-loaded.py",
            "timeout": 10
        }
    ]
}


def has_rules_loaded_hook(settings):
    """Check if rules-loaded hook already exists in SessionStart."""
    session_start = settings.get("hooks", {}).get("SessionStart", [])
    for entry in session_start:
        for h in entry.get("hooks", []):
            if "rules-loaded" in h.get("command", ""):
                return True
    return False


def patch(settings):
    """Add rules-loaded hook to SessionStart if not present."""
    if "hooks" not in settings:
        settings["hooks"] = {}
    if "SessionStart" not in settings["hooks"]:
        settings["hooks"]["SessionStart"] = []

    if not has_rules_loaded_hook(settings):
        settings["hooks"]["SessionStart"].append(RULES_LOADED_HOOK)

    return settings


if __name__ == "__main__":
    raw = sys.stdin.read().strip()
    if not raw:
        raw = "{}"
    try:
        settings = json.loads(raw)
    except json.JSONDecodeError:
        settings = {}

    patched = patch(settings)
    print(json.dumps(patched, indent=2))
