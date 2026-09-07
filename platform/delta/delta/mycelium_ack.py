"""Validated, append-only acknowledgement handoff from Delta to Mycelium.

This is deliberately a narrow boundary.  It records that Delta received or
reviewed a conversation message; it is not an execution channel.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
_SCOPE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_STATUSES = frozenset({"received", "needs_review", "rejected"})
_MAX_SUMMARY = 2000
_REQUIRED = frozenset({"conversation_message_id", "ack_id", "ack_status", "scope"})


class AckValidationError(ValueError):
    """The Delta acknowledgement did not satisfy the handoff contract."""


def validate_ack(data: dict[str, Any]) -> dict[str, str]:
    """Return a sanitized acknowledgement or raise ``AckValidationError``."""
    if not isinstance(data, dict):
        raise AckValidationError("ack must be an object")
    if set(data) - (_REQUIRED | {"summary"}):
        raise AckValidationError("ack contains unsupported fields")
    if not _REQUIRED.issubset(data):
        raise AckValidationError("ack is missing required fields")

    result: dict[str, str] = {}
    for field in ("conversation_message_id", "ack_id"):
        value = data[field]
        if not isinstance(value, str) or not _ID.fullmatch(value):
            raise AckValidationError(f"invalid {field}")
        result[field] = value

    status = data["ack_status"]
    if not isinstance(status, str) or status not in _STATUSES:
        raise AckValidationError("invalid ack_status")
    result["ack_status"] = status

    scope = data["scope"]
    if not isinstance(scope, str) or not _SCOPE.fullmatch(scope):
        raise AckValidationError("invalid scope")
    result["scope"] = scope

    summary = data.get("summary", "")
    if not isinstance(summary, str) or len(summary) > _MAX_SUMMARY:
        raise AckValidationError("invalid summary")
    # A summary is evidence for a human, not a second command channel.
    result["summary"] = summary
    return result


def append_ack(path: str | Path, data: dict[str, Any], *, now: datetime | None = None) -> str:
    """Validate and durably append an acknowledgement; return its line hash."""
    record = validate_ack(data)
    timestamp = now or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise AckValidationError("timestamp must include timezone")
    record["recorded_at"] = timestamp.astimezone(timezone.utc).isoformat()
    line = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()

    target = Path(path)
    target.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o640)
    try:
        os.write(fd, line)
        os.fsync(fd)
    finally:
        os.close(fd)
    return hashlib.sha256(line).hexdigest()


def append_ack_once(path: str | Path, data: dict[str, Any], *, now: datetime | None = None) -> str:
    """Append one receipt for an acknowledgement ID; tolerate a delivery retry."""
    record = validate_ack(data)
    target = Path(path)
    if target.exists():
        try:
            for line in target.read_text().splitlines():
                existing = json.loads(line)
                if (existing.get("ack_id") == record["ack_id"] and
                        existing.get("conversation_message_id") == record["conversation_message_id"]):
                    return "already_recorded"
        except (OSError, json.JSONDecodeError):
            pass
    return append_ack(target, record, now=now)
