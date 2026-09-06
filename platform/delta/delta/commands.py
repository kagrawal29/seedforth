"""Command parsing for Delta Discord messages.

Extracts structured commands from user message text.
Returns (command_name, args_dict) or None if not a command.
"""

import re
from typing import Optional


_GITHUB_RE = re.compile(
    r"(?:https?://)?github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"
)


def parse(text: str) -> Optional[tuple[str, dict]]:
    """Parse a message into a command tuple or None."""
    stripped = text.strip()
    lower = stripped.lower()

    if lower in ("help", "commands"):
        return ("help", {})

    if lower in ("list", "list projects", "projects"):
        return ("list", {})

    if lower == "status all":
        return ("status_all", {})

    if lower == "status":
        return ("status", {})
    if lower.startswith("status "):
        project_name = stripped[7:].strip()
        return ("status", {"project": project_name})

    # "new <name>" is shorthand for "new project <name>"
    if lower.startswith("new ") and not lower.startswith("new project"):
        rest = stripped[4:].strip()
        if rest:
            parts = rest.split()
            name = parts[0]
            result = {"name": name}
            if len(parts) > 1 and parts[-1].lower() == "here":
                result["here"] = True
            return ("new_project", result)

    if lower.startswith("new project"):
        rest = stripped[11:].strip()
        if not rest:
            return ("new_project", {})
        # Check for "here" flag (use current channel)
        here = False
        gh_match = _GITHUB_RE.search(rest)
        if gh_match:
            repo = gh_match.group(1).rstrip("/")
            name = repo.split("/")[-1]
            # Check for trailing "here"
            after = rest[gh_match.end():].strip().lower()
            here = after == "here"
            result = {"name": name, "github_repo": repo}
            if here:
                result["here"] = True
            return ("new_project", result)
        parts = rest.split()
        name = parts[0]
        if name.lower() == "here":
            return ("new_project", {"here": True})
        result = {"name": name}
        if len(parts) > 1 and parts[-1].lower() == "here":
            result["here"] = True
        return ("new_project", result)

    if lower.startswith("tear down ") or lower.startswith("teardown "):
        prefix_len = 10 if lower.startswith("tear down ") else 9
        project = stripped[prefix_len:].strip()
        return ("teardown", {"project": project})

    if lower.startswith("delete "):
        project = stripped[7:].strip()
        return ("teardown", {"project": project})

    if lower.startswith("logs "):
        project = stripped[5:].strip()
        return ("logs", {"project": project})

    if lower.startswith("peek "):
        project = stripped[5:].strip()
        if project == "hub":
            return ("peek_hub", {})
        return ("peek", {"project": project})

    if lower.startswith("send "):
        rest = stripped[5:].strip()
        parts = rest.split(None, 1)
        if len(parts) == 2:
            return ("admin_send", {"project": parts[0], "text": parts[1]})

    if lower.startswith("restart "):
        project = stripped[8:].strip()
        if project == "hub":
            return ("restart_hub", {})
        return ("restart", {"project": project})

    if lower.startswith("schedule "):
        project = stripped[9:].strip()
        return ("schedule", {"project": project})

    if lower == "refresh templates":
        return ("refresh_templates", {})

    # -- Invariant Governance --
    if lower.startswith("approve-invariant") or lower.startswith("approve invariant"):
        rest = stripped.split(None, 2)
        proposal_id = rest[1] if len(rest) > 1 else ""
        reason = rest[2] if len(rest) > 2 else ""
        return ("approve_invariant", {"proposal_id": proposal_id, "reason": reason})

    if lower.startswith("reject-invariant") or lower.startswith("reject invariant"):
        rest = stripped.split(None, 2)
        proposal_id = rest[1] if len(rest) > 1 else ""
        reason = rest[2] if len(rest) > 2 else ""
        return ("reject_invariant", {"proposal_id": proposal_id, "reason": reason})

    if lower in ("list proposals", "invariant proposals", "proposals"):
        return ("list_proposals", {})

    return None


HELP_TEXT = """\
**Getting started**
`new project <name>` -- spin up a new project with its own channel
`new project <name> here` -- use this channel for the project
`new project github.com/owner/repo` -- start from an existing repo

**Your projects**
`status` -- how are your projects doing
`list` -- see your projects
`tear down <name>` -- shut it all down

**Admin**
`status all` -- everything at a glance
`logs <name>` -- recent conversation history
`peek <name>` -- recent opencode agent output
`send <name> <message>` -- talk to any project
`restart <name>` -- restart the opencode agent
`schedule <name>` -- see a project's task backlog

Or just talk. If you have one project, your DMs go straight to it.
"""
