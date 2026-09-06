"""Tests for delta.project_bridge module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from delta.project_bridge import ProjectBridge


@pytest.fixture
def bridge(tmp_path):
    """Create a ProjectBridge with a temp data dir."""
    return ProjectBridge(
        name="test-project",
        data_dir=str(tmp_path),
        tmux_lead_pane="test:lead",
    )


class TestCheckAuthError:
    """Tests for ProjectBridge.check_auth_error."""

    def test_returns_none_when_no_error(self, bridge):
        assert bridge.check_auth_error() is None

    def test_detects_401(self, bridge):
        (bridge.data_dir / "errors").mkdir()
        (bridge.data_dir / "errors" / "auth.json").write_text(
            json.dumps({"type": "auth_error", "message": "401 Unauthorized"})
        )
        result = bridge.check_auth_error()
        assert result is not None
        assert "401" in result

    def test_detects_oauth_token_expired(self, bridge):
        (bridge.data_dir / "errors").mkdir()
        (bridge.data_dir / "errors" / "auth.json").write_text(
            json.dumps({"type": "auth_error", "message": "OAuth token expired"})
        )
        result = bridge.check_auth_error()
        assert result is not None
        assert "expired" in result.lower()

    def test_detects_case_insensitive(self, bridge):
        (bridge.data_dir / "errors").mkdir()
        (bridge.data_dir / "errors" / "auth.json").write_text(
            json.dumps({"type": "auth_error", "message": "AUTHENTICATION FAILED"})
        )
        assert bridge.check_auth_error() == "AUTHENTICATION FAILED"

    def test_returns_none_on_tmux_error(self, bridge):
        assert bridge.check_auth_error() is None

    def test_returns_none_on_capture_failure(self, bridge):
        assert bridge.check_auth_error() is None

    def test_truncates_long_error_line(self, bridge):
        (bridge.data_dir / "errors").mkdir()
        long_message = "Unauthorized " + "x" * 300
        (bridge.data_dir / "errors" / "auth.json").write_text(
            json.dumps({"type": "auth_error", "message": long_message})
        )
        assert bridge.check_auth_error() == long_message


class TestWriteInbox:
    """Tests for ProjectBridge.write_inbox."""

    def test_creates_inbox_file(self, bridge):
        msg_id = bridge.write_inbox("C123", "U456", "hello")
        inbox_file = bridge.inbox_dir / f"{msg_id}.json"
        assert inbox_file.exists()
        data = json.loads(inbox_file.read_text())
        assert data["channel"] == "C123"
        assert data["user"] == "U456"
        assert data["text"] == "hello"

    def test_extra_kwargs_merged(self, bridge):
        msg_id = bridge.write_inbox("C123", "U456", "hello",
                                    channel_type="dm", channel_name="test")
        inbox_file = bridge.inbox_dir / f"{msg_id}.json"
        data = json.loads(inbox_file.read_text())
        assert data["channel_type"] == "dm"
        assert data["channel_name"] == "test"


class TestWatchOutboxDeadLetter:
    """Tests for malformed outbox file cleanup."""

    def test_malformed_file_moved_to_dead_letter(self, bridge):
        """Malformed JSON in outbox should be moved to dead-letter dir."""
        (bridge.outbox_dir / "bad.json").write_text("not valid json{{{")

        results = []
        call_count = 0

        def fake_callback(data):
            results.append(data)

        original_wait = bridge._shutdown_event.wait

        def limited_wait(timeout):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                bridge._shutdown_event.set()
            original_wait(0.01)

        bridge._shutdown_event.wait = limited_wait
        bridge.watch_outbox(fake_callback)

        # File should not be in outbox anymore
        assert not (bridge.outbox_dir / "bad.json").exists()
        # File should be in dead-letter
        dead_letter = bridge.outbox_dir / "dead-letter"
        assert (dead_letter / "bad.json").exists()
        # Callback should not have been called
        assert len(results) == 0

    def test_valid_file_not_moved_to_dead_letter(self, bridge):
        """Valid JSON should be processed and deleted, not moved to dead-letter."""
        valid = {"id": "test-1", "channel": "C1", "text": "hi"}
        (bridge.outbox_dir / "good.json").write_text(json.dumps(valid))

        results = []
        call_count = 0

        def fake_callback(data):
            results.append(data)

        original_wait = bridge._shutdown_event.wait

        def limited_wait(timeout):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                bridge._shutdown_event.set()
            original_wait(0.01)

        bridge._shutdown_event.wait = limited_wait
        bridge.watch_outbox(fake_callback)

        assert not (bridge.outbox_dir / "good.json").exists()
        dead_letter = bridge.outbox_dir / "dead-letter"
        assert not dead_letter.exists() or not (dead_letter / "good.json").exists()
        assert len(results) == 1
        assert results[0]["text"] == "hi"


class TestPendingInboxCount:
    """Tests for ProjectBridge.pending_inbox_count."""

    def test_empty_inbox(self, bridge):
        assert bridge.pending_inbox_count() == 0

    def test_counts_json_files(self, bridge):
        (bridge.inbox_dir / "msg-1.json").write_text("{}")
        (bridge.inbox_dir / "msg-2.json").write_text("{}")
        assert bridge.pending_inbox_count() == 2


class TestGetSchedule:
    """Tests for ProjectBridge.get_schedule."""

    def test_no_schedule_file(self, bridge):
        assert bridge.get_schedule() == []

    def test_reads_tasks(self, bridge):
        schedule = {"tasks": [{"what": "build thing", "status": "in_progress"}]}
        (bridge.data_dir / "schedule.json").write_text(json.dumps(schedule))
        result = bridge.get_schedule()
        assert len(result) == 1
        assert result[0]["what"] == "build thing"
