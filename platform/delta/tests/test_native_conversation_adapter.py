from pathlib import Path

from delta.native_conversation_adapter import NativeConversationAdapter, NativeConversationError


ROOT = Path(__file__).resolve().parents[2]


class GraphFixture:
    def __init__(self):
        self.calls = []
        self.message = {
            "message_id": "message-board-001", "scope_id": "fixture-cajon",
            "text": "Make the first beginner lesson concrete.",
            "request_hash": "hash-001", "sequence": 4,
            "conversation_id": "conversation-cajon",
            "workitem_id": "work-cajon", "consumption_id": "consumption-001",
            "consumption_status": "consumed",
        }

    def __call__(self, cypher, params):
        self.calls.append((cypher, params))
        if "ConversationConsumption" in cypher:
            return [self.message]
        assert "ProviderTurn" in cypher
        return [{"provider_turn_id": "provider-turn-001",
                 "provider_turn_status": "started",
                 "execution_state": "provider_turn_started"}]


def test_board_message_is_bound_at_turn_and_provider_start_is_recorded():
    graph = GraphFixture()
    provider_calls = []

    def provider(context):
        provider_calls.append(context)
        return {"started": True, "turn_id": "turn-001", "provider": "openrouter",
                "model": "deepseek/deepseek-v4-pro", "response": "accepted"}

    result = NativeConversationAdapter(graph, provider,
                                       worker_id="worker-cajon",
                                       scope="fixture-cajon").consume_and_start(
                                           message_id="message-board-001",
                                           workitem_id="work-cajon",
                                           attempt_id="attempt-001")

    assert len(provider_calls) == 1
    assert provider_calls[0]["text"] == "Make the first beginner lesson concrete."
    assert provider_calls[0]["workitem_id"] == "work-cajon"
    assert result["evidence_boundary"] == "provider_turn_started_only"
    assert "action" not in result["evidence_boundary"]
    assert "action" not in result["provider_turn"]
    assert "ConversationConsumption" in graph.calls[0][0]
    assert "ProviderTurn" in graph.calls[1][0]


def test_provider_is_not_called_when_graph_binding_is_missing():
    calls = []

    def graph(_cypher, _params):
        return []

    def provider(_context):
        calls.append(True)
        return {"started": True}

    adapter = NativeConversationAdapter(graph, provider,
                                        worker_id="worker-cajon",
                                        scope="fixture-cajon")
    try:
        adapter.consume_and_start(message_id="message-board-001",
                                  workitem_id="wrong-work", attempt_id="attempt-001")
    except NativeConversationError as exc:
        assert str(exc) == "graph_message_not_bound_or_consumable"
    else:
        raise AssertionError("expected graph binding failure")
    assert calls == []


def test_provider_start_without_ack_does_not_create_turn_record():
    graph = GraphFixture()

    def provider(_context):
        return {"started": False}

    adapter = NativeConversationAdapter(graph, provider,
                                        worker_id="worker-cajon",
                                        scope="fixture-cajon")
    try:
        adapter.consume_and_start(message_id="message-board-001",
                                  workitem_id="work-cajon", attempt_id="attempt-001")
    except NativeConversationError as exc:
        assert str(exc) == "provider_did_not_acknowledge_turn_start"
    else:
        raise AssertionError("expected provider acknowledgement failure")
    assert len(graph.calls) == 1
