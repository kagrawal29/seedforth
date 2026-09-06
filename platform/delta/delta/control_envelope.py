"""Versioned transport envelope for Delta/Mycelium control messages.

The envelope carries an observation or request across the process boundary.
It is not durable state: Mycelium records accepted messages and derives graph
state idempotently from ``message_id``.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any
from uuid import uuid4

SCHEMA = "seedforth.control.v1"
KINDS = frozenset({"signal", "decision_request", "progress", "execution_result"})
SOURCES = frozenset({"delta", "mycelium", "agent", "provider"})


def make_envelope(
    *,
    kind: str,
    project: str,
    source: str,
    correlation_id: str,
    payload: dict[str, Any],
    message_id: str | None = None,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    """Create a JSON-compatible envelope with strict boundary fields."""
    envelope = {
        "schema": SCHEMA,
        "message_id": message_id or f"msg-{uuid4().hex}",
        "kind": kind,
        "project": project,
        "source": source,
        "occurred_at": occurred_at or datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id,
        "payload": payload,
    }
    validate_envelope(envelope)
    return envelope


def validate_envelope(envelope: dict[str, Any]) -> None:
    """Raise ``ValueError`` when an envelope violates the v1 contract."""
    required = {
        "schema", "message_id", "kind", "project", "source",
        "occurred_at", "correlation_id", "payload",
    }
    missing = required.difference(envelope)
    if missing:
        raise ValueError(f"missing envelope fields: {', '.join(sorted(missing))}")
    if envelope["schema"] != SCHEMA:
        raise ValueError(f"unsupported envelope schema: {envelope['schema']!r}")
    if envelope["kind"] not in KINDS:
        raise ValueError(f"unsupported envelope kind: {envelope['kind']!r}")
    if envelope["source"] not in SOURCES:
        raise ValueError(f"unsupported envelope source: {envelope['source']!r}")
    for field in ("message_id", "project", "correlation_id"):
        if not isinstance(envelope[field], str) or not envelope[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    if not isinstance(envelope["payload"], dict):
        raise ValueError("payload must be an object")
    if not isinstance(envelope["occurred_at"], str):
        raise ValueError("occurred_at must be an RFC3339 string")
    try:
        datetime.fromisoformat(envelope["occurred_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("occurred_at must be an RFC3339 string") from exc


def encode(envelope: dict[str, Any]) -> str:
    """Validate and serialize an envelope deterministically."""
    validate_envelope(envelope)
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"))


def dedupe_key(envelope: dict[str, Any]) -> str:
    """Return the idempotency key used by the Mycelium ingest boundary."""
    validate_envelope(envelope)
    return envelope["message_id"]
