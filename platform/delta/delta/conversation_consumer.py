"""Consume graph-delivered Delta directions at the worker boundary.

Delivery only creates an inbox file.  This consumer is the next boundary: it
validates the immutable handoff, asks the bound worker runtime to wake, and
emits a receipt.  It deliberately does not claim that the worker acted; that
must come from a separate worker evidence stream.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Callable, Any

from .mycelium_ack import append_ack_once

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
_SCOPE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class ConsumerError(ValueError):
    pass


def project_bridge_wakeup(bridge: Any, data: dict[str, Any]) -> dict[str, str]:
    """Adapt a ProjectBridge nudge into a bounded wakeup receipt."""
    if not bridge.send_to_lead(data["conversation_message_id"]):
        raise ConsumerError("worker_health_unavailable")
    return {
        "wakeup_id": "wakeup-" + data["conversation_message_id"],
        "worker_id": "worker-" + data["scope"],
    }


def validate_delivery(data: Any, scope: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ConsumerError("delivery_not_object")
    if data.get("source") != "mycelium-conversation-processor":
        raise ConsumerError("delivery_source_denied")
    if data.get("scope") != scope or not _SCOPE.fullmatch(scope):
        raise ConsumerError("delivery_scope_mismatch")
    for field in ("id", "conversation_message_id", "conversation_request_hash"):
        if not isinstance(data.get(field), str) or not _ID.fullmatch(data[field]):
            raise ConsumerError("delivery_identity_invalid")
    workitem_id = data.get("workitem_id")
    if workitem_id is not None and (not isinstance(workitem_id, str) or not _ID.fullmatch(workitem_id)):
        raise ConsumerError("delivery_workitem_invalid")
    if not isinstance(data.get("text"), str) or not data["text"]:
        raise ConsumerError("delivery_text_invalid")
    if data.get("trust") != "authenticated_origin_untrusted_content":
        raise ConsumerError("delivery_trust_invalid")
    return data


def consume_once(
    inbox: str | Path,
    ack_stream: str | Path,
    scope: str,
    wake_worker: Callable[[dict[str, Any]], dict[str, str]],
) -> dict[str, int]:
    """Consume pending files and request a bound worker wakeup.

    ``wake_worker`` is an adapter boundary.  It must return a wakeup id and
    worker id, but action evidence is intentionally not accepted here.
    """
    inbox_path = Path(inbox)
    consumed = inbox_path / "consumed"
    stats = {"seen": 0, "consumed": 0, "rejected": 0, "wake_failed": 0}
    for path in sorted(inbox_path.glob("*.json")):
        stats["seen"] += 1
        try:
            data = validate_delivery(json.loads(path.read_text()), scope)
            receipt = wake_worker(data)
            if (not isinstance(receipt, dict) or
                    not _ID.fullmatch(str(receipt.get("wakeup_id", ""))) or
                    not _ID.fullmatch(str(receipt.get("worker_id", "")))):
                raise ConsumerError("wakeup_receipt_invalid")
            append_ack_once(ack_stream, {
                "conversation_message_id": data["conversation_message_id"],
                "ack_id": "ack-" + receipt["wakeup_id"],
                "ack_status": "received",
                "scope": scope,
                "summary": "Delta consumed delivery and requested bound worker wakeup " + receipt["wakeup_id"],
            })
            consumed.mkdir(parents=True, exist_ok=True)
            path.replace(consumed / path.name)
            stats["consumed"] += 1
        except ConsumerError:
            stats["rejected"] += 1
        except Exception:
            # Leave the file for the existing retry/reconciliation path.
            stats["wake_failed"] += 1
    return stats
