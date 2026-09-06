"""
graph_observer.py — Lightweight observability for agent-graph communication.

Logs every interaction with Asgard (ask calls, file reads) to
knowledge/meta/asgard-query-log.md in append-only markdown table format.

The log is readable by the demand engine — agent queries ARE demand signals.
Zero LLM cost. Non-blocking — if logging fails, the caller is unaffected.
"""

import os
from datetime import datetime, timezone

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOG_PATH = os.path.join(_REPO_ROOT, "knowledge", "meta", "asgard-query-log.md")

_HEADER = (
    "# Asgard Query Log\n\n"
    "Append-only. Each row is one agent interaction with the knowledge graph.\n"
    "Agent queries are demand signals — the demand engine reads this file.\n\n"
    "| timestamp (UTC) | agent / source | action | question / file | results | response_bytes |\n"
    "|-----------------|----------------|--------|-----------------|---------|----------------|\n"
)


def _ensure_log():
    """Create the log file with header if it doesn't exist."""
    if not os.path.exists(_LOG_PATH):
        os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
        with open(_LOG_PATH, "w") as f:
            f.write(_HEADER)


def _sanitize(text: str) -> str:
    """Collapse whitespace and escape pipe chars for markdown table cells."""
    return " ".join(str(text).split()).replace("|", "\\|")[:120]


def log_graph_interaction(
    agent_name: str,
    action: str,
    question_or_path: str,
    num_results: int = 0,
    response_bytes: int = 0,
) -> None:
    """
    Append one row to the Asgard query log.

    Args:
        agent_name:        Name of the calling agent or module (e.g. "ask_asgard", "heimdall").
        action:            What was done (e.g. "ask", "ask_neighborhood", "read_file").
        question_or_path:  The question asked or file path read.
        num_results:       Number of graph results returned (0 for file reads).
        response_bytes:    Length of the response string in bytes.
    """
    try:
        _ensure_log()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        row = (
            f"| {ts} "
            f"| {_sanitize(agent_name)} "
            f"| {_sanitize(action)} "
            f"| {_sanitize(question_or_path)} "
            f"| {num_results} "
            f"| {response_bytes} |\n"
        )
        with open(_LOG_PATH, "a") as f:
            f.write(row)
    except Exception:
        pass  # Never block the caller


def wrap_file_read(file_path: str, agent_name: str = "unknown") -> str:
    """
    Read a graph context file and log the access.

    Returns the file contents (empty string if the file doesn't exist).
    Logging failure never raises.
    """
    try:
        with open(file_path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""
    except Exception:
        content = ""

    log_graph_interaction(
        agent_name=agent_name,
        action="read_file",
        question_or_path=file_path,
        num_results=0,
        response_bytes=len(content.encode("utf-8")),
    )
    return content
