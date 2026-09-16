"""Graph-boundary adapter for native provider turns.

The native canary bypasses ProjectBridge.  This adapter is the narrow bridge
from a delivered board ConversationMessage to that canary's next provider
turn.  It performs one graph pull, one serial provider call, then one graph
turn-start record.  A turn-start record is not action or completion evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


def _load_contract(name: str) -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / "mycelium" / "graph" / "control" / name).read_text()


class NativeConversationError(RuntimeError):
    pass


class NativeConversationAdapter:
    """Consume one graph-bound message and start at most one provider turn."""

    def __init__(self, query: Callable[[str, dict[str, Any]], list[dict[str, Any]]],
                 provider_start: Callable[[dict[str, Any]], dict[str, Any]], *,
                 worker_id: str, scope: str):
        self.query = query
        self.provider_start = provider_start
        self.worker_id = worker_id
        self.scope = scope

    def consume_and_start(self, *, message_id: str, workitem_id: str,
                          attempt_id: str) -> dict[str, Any]:
        consumed = self.query(_load_contract("claim-native-conversation-message.cypher"), {
            "message_id": message_id, "workitem_id": workitem_id,
            "attempt_id": attempt_id, "worker_id": self.worker_id,
            "scope": self.scope,
        })
        if not consumed:
            raise NativeConversationError("graph_message_not_bound_or_consumable")
        context = dict(consumed[0])
        context["attempt_id"] = attempt_id
        context["worker_id"] = self.worker_id
        # There is intentionally no thread, task, or parallel provider call
        # here. The provider receives exactly this bounded graph projection.
        provider_result = self.provider_start(dict(context))
        if not isinstance(provider_result, dict) or provider_result.get("started") is not True:
            raise NativeConversationError("provider_did_not_acknowledge_turn_start")
        turn_id = str(provider_result.get("turn_id") or "")
        provider = str(provider_result.get("provider") or "")
        model = str(provider_result.get("model") or "")
        if not turn_id or not provider or not model:
            raise NativeConversationError("provider_start_receipt_incomplete")
        started = self.query(_load_contract("record-provider-turn-start.cypher"), {
            "message_id": message_id, "workitem_id": workitem_id,
            "attempt_id": attempt_id, "turn_id": turn_id,
            "provider": provider, "model": model, "scope": self.scope,
        })
        if not started:
            raise NativeConversationError("provider_turn_start_not_recorded")
        return {
            "message": context,
            "provider_turn": dict(started[0]),
            "provider_response": provider_result.get("response"),
            "evidence_boundary": "provider_turn_started_only",
        }
