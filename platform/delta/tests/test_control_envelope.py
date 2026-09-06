import pytest

from delta.control_envelope import encode, make_envelope, validate_envelope


def test_make_envelope_is_versioned_and_serializable():
    envelope = make_envelope(
        kind="progress",
        project="flowing-indian",
        source="delta",
        correlation_id="exec-123",
        payload={"status": "in_progress"},
        message_id="msg-123",
        occurred_at="2026-09-06T12:00:00+00:00",
    )
    assert envelope["schema"] == "seedforth.control.v1"
    assert '"message_id":"msg-123"' in encode(envelope)


@pytest.mark.parametrize("field", ["project", "message_id", "correlation_id"])
def test_empty_identity_fields_are_rejected(field):
    envelope = make_envelope(
        kind="signal", project="p", source="agent", correlation_id="c",
        payload={}, message_id="m", occurred_at="2026-09-06T12:00:00+00:00",
    )
    envelope[field] = ""
    with pytest.raises(ValueError, match=field):
        validate_envelope(envelope)


def test_unknown_kind_and_missing_project_are_rejected():
    with pytest.raises(ValueError, match="kind"):
        make_envelope(kind="command", project="p", source="delta",
                      correlation_id="c", payload={})
    with pytest.raises(ValueError, match="project"):
        make_envelope(kind="signal", project="", source="delta",
                      correlation_id="c", payload={})


def test_replay_keeps_same_message_id():
    first = make_envelope(kind="execution_result", project="p", source="agent",
                          correlation_id="exec-1", payload={}, message_id="msg-1",
                          occurred_at="2026-09-06T12:00:00+00:00")
    replay = dict(first)
    validate_envelope(replay)
    assert replay["message_id"] == first["message_id"]
