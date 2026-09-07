from datetime import datetime, timezone
import json

import pytest

from delta.mycelium_ack import AckValidationError, append_ack, validate_ack


def valid(**overrides):
    value = {
        "conversation_message_id": "msg-123",
        "ack_id": "ack-123",
        "ack_status": "received",
        "scope": "cajon-sensei",
        "summary": "received",
    }
    value.update(overrides)
    return value


def test_validation_strips_command_and_credential_fields():
    with pytest.raises(AckValidationError):
        validate_ack(valid(command="run", token="secret"))


@pytest.mark.parametrize("status", ["sent", "executed", "approved", ""])
def test_only_receipt_statuses_are_allowed(status):
    with pytest.raises(AckValidationError):
        validate_ack(valid(ack_status=status))


def test_summary_is_bounded():
    with pytest.raises(AckValidationError):
        validate_ack(valid(summary="x" * 2001))


def test_append_is_durable_and_deterministically_shaped(tmp_path):
    target = tmp_path / "acks.jsonl"
    timestamp = datetime(2026, 9, 7, tzinfo=timezone.utc)
    digest = append_ack(target, valid(), now=timestamp)
    line = target.read_text()
    record = json.loads(line)
    assert record["recorded_at"] == "2026-09-07T00:00:00+00:00"
    assert "command" not in record
    assert len(digest) == 64


def test_symlink_target_is_rejected(tmp_path):
    target = tmp_path / "acks.jsonl"
    target.symlink_to(tmp_path / "other.jsonl")
    with pytest.raises(OSError):
        append_ack(target, valid())
