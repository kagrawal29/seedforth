#!/usr/bin/env python3
"""PostToolUse hook -- writes progress signals for Delta's bridge to stream to Discord.

Claude Code invokes this via PostToolUse hook with JSON on stdin:
    {"tool_name": "Write", "tool_input": {...}, "tool_response": "..."}

Classifies the signal level, extracts a short summary, and writes a progress
file to delta-config/progress/ for the bridge's watch_progress() to pick up.
"""

import json
import os
import random
import string
import sys
import time
from pathlib import Path

# delta-config/progress/ is two levels up from hooks/progress_hook.py
PROGRESS_DIR = Path(__file__).resolve().parent.parent / "delta-config" / "progress"

# Tools that indicate meaningful work
_HIGH_SIGNAL_TOOLS = {"Write", "Bash", "NotebookEdit"}
_MEDIUM_SIGNAL_TOOLS = {"Edit"}
_SKIP_TOOLS = {"Read", "Glob", "Grep", "WebFetch", "WebSearch", "ToolSearch"}

# Bash commands that are just reads/housekeeping, not real work
_SKIP_BASH_PREFIXES = ("cat ", "ls ", "echo ", "head ", "tail ", "pwd", "whoami",
                       "which ", "type ", "file ", "wc ", "git add", "git commit",
                       "git status", "git diff", "git log", "git push", "git pull",
                       "cd ", "mkdir ", "chmod ", "chown ")

# Bash commands that are high-signal deploys/builds
_HIGH_BASH_KEYWORDS = ("deploy", "build", "npm", "vercel", "npx", "pip",
                       "git push", "python", "node ", "bun ", "deno ")


def _classify(tool_name: str, tool_input: dict) -> str:
    """Return 'high', 'medium', or 'skip'."""
    if tool_name in _SKIP_TOOLS:
        return "skip"

    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        cmd_stripped = cmd.strip()
        for prefix in _SKIP_BASH_PREFIXES:
            if cmd_stripped.startswith(prefix):
                return "skip"
        for kw in _HIGH_BASH_KEYWORDS:
            if kw in cmd_stripped.lower():
                return "high"
        return "medium"

    if tool_name in _HIGH_SIGNAL_TOOLS:
        return "high"
    if tool_name in _MEDIUM_SIGNAL_TOOLS:
        return "medium"

    # MCP tools (mcp__*, RUBE_*, etc.) are high signal
    if tool_name.startswith("mcp__") or "RUBE" in tool_name:
        return "high"

    # Unknown tools default to medium
    return "medium"


def _summarize(tool_name: str, tool_input: dict) -> str:
    """Extract a short summary from the tool call."""
    if tool_name in ("Write", "NotebookEdit"):
        fp = tool_input.get("file_path", tool_input.get("notebook_path", ""))
        if fp:
            return Path(fp).name
        return tool_name

    if tool_name == "Edit":
        fp = tool_input.get("file_path", "")
        if fp:
            return Path(fp).name
        return "editing"

    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        return cmd[:80]

    # MCP / other tools: just the tool name
    return tool_name


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Skip writes to delta-config/ -- those are bridge mechanics, not user work
    if tool_name in ("Write", "Edit", "NotebookEdit"):
        fp = tool_input.get("file_path", tool_input.get("notebook_path", ""))
        if "delta-config/" in fp or "delta-config\\" in fp:
            return

    signal = _classify(tool_name, tool_input)
    if signal == "skip":
        return

    summary = _summarize(tool_name, tool_input)

    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)

    rand_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    filename = f"prog-{int(time.time())}-{rand_suffix}.json"
    tmp_path = PROGRESS_DIR / f".{filename}.tmp"
    final_path = PROGRESS_DIR / filename

    payload = json.dumps({
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tool": tool_name,
        "summary": summary,
        "signal": signal,
    })

    try:
        tmp_path.write_text(payload)
        os.rename(str(tmp_path), str(final_path))
    except OSError:
        # Clean up tmp on failure
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    main()
