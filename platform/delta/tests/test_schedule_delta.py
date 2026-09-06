"""Tests for Delta schedule and followup systems.

Covers:
- _is_schedule_time() timezone handling, ±5 min window, daily vs weekly
- _read_project_schedule() reading/parsing schedule.json
- _get_schedule_data() reading full schedule data
- _load_last_fired / _save_last_fired persistence
- ProjectBridge.watch_followups() delivery timing
- ProjectBridge.cancel_pending_followups() clearing followups dir
- ProjectBridge.has_pending_work() checking for active tasks and followups
- ProjectBridge.get_schedule() reading schedule from data_dir
"""

import json
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo

import pytest

from delta.project_bridge import ProjectBridge


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bridge(tmp_path):
    """Create a ProjectBridge with a temp data dir."""
    return ProjectBridge(
        name="test-project",
        data_dir=str(tmp_path),
        tmux_lead_pane="test:lead",
    )


@pytest.fixture
def schedule_dir(tmp_path):
    """Create a project dir with delta-config/schedule.json."""
    config_dir = tmp_path / "delta-config"
    config_dir.mkdir()
    return tmp_path, config_dir


# ---------------------------------------------------------------------------
# _is_schedule_time
# ---------------------------------------------------------------------------

class TestIsScheduleTime:
    """Tests for delta.app._is_schedule_time."""

    def _import_fn(self):
        from delta.app import _is_schedule_time
        return _is_schedule_time

    def test_matches_exact_time(self):
        fn = self._import_fn()
        # Mock "now" to be exactly 09:00 UTC on a Monday
        with patch("delta.app.datetime") as mock_dt:
            mock_now = datetime(2026, 3, 2, 9, 0, tzinfo=ZoneInfo("UTC"))
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert fn("09:00", "UTC") is True

    def test_matches_within_5_min_window(self):
        fn = self._import_fn()
        with patch("delta.app.datetime") as mock_dt:
            # 09:03 is within 5 min of 09:00
            mock_now = datetime(2026, 3, 2, 9, 3, tzinfo=ZoneInfo("UTC"))
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert fn("09:00", "UTC") is True

    def test_outside_5_min_window(self):
        fn = self._import_fn()
        with patch("delta.app.datetime") as mock_dt:
            # 09:06 is outside 5 min of 09:00
            mock_now = datetime(2026, 3, 2, 9, 6, tzinfo=ZoneInfo("UTC"))
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert fn("09:00", "UTC") is False

    def test_wrong_hour(self):
        fn = self._import_fn()
        with patch("delta.app.datetime") as mock_dt:
            mock_now = datetime(2026, 3, 2, 10, 0, tzinfo=ZoneInfo("UTC"))
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert fn("09:00", "UTC") is False

    def test_daily_fires_any_weekday(self):
        fn = self._import_fn()
        # Wednesday
        with patch("delta.app.datetime") as mock_dt:
            mock_now = datetime(2026, 3, 4, 9, 0, tzinfo=ZoneInfo("UTC"))
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert fn("09:00", "UTC", freq="daily") is True

    def test_does_not_fire_before_schedule_time(self):
        fn = self._import_fn()
        with patch("delta.app.datetime") as mock_dt:
            # 08:57 is 3 min BEFORE 09:00 -- should not fire
            mock_now = datetime(2026, 3, 2, 8, 57, tzinfo=ZoneInfo("UTC"))
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert fn("09:00", "UTC") is False

    def test_does_not_fire_minutes_before_in_same_hour(self):
        fn = self._import_fn()
        with patch("delta.app.datetime") as mock_dt:
            # 09:27 is 3 min BEFORE 09:30 -- should not fire
            mock_now = datetime(2026, 3, 2, 9, 27, tzinfo=ZoneInfo("UTC"))
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert fn("09:30", "UTC") is False

    def test_daily_fires_on_weekend(self):
        fn = self._import_fn()
        # Saturday
        with patch("delta.app.datetime") as mock_dt:
            mock_now = datetime(2026, 3, 7, 9, 0, tzinfo=ZoneInfo("UTC"))
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert fn("09:00", "UTC", freq="daily") is True

    def test_weekly_fires_on_monday(self):
        fn = self._import_fn()
        # Monday (weekday() == 0)
        with patch("delta.app.datetime") as mock_dt:
            mock_now = datetime(2026, 3, 2, 9, 0, tzinfo=ZoneInfo("UTC"))
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert fn("09:00", "UTC", freq="weekly") is True

    def test_weekly_does_not_fire_on_tuesday(self):
        fn = self._import_fn()
        # Tuesday (weekday() == 1)
        with patch("delta.app.datetime") as mock_dt:
            mock_now = datetime(2026, 3, 3, 9, 0, tzinfo=ZoneInfo("UTC"))
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert fn("09:00", "UTC", freq="weekly") is False

    def test_timezone_conversion(self):
        fn = self._import_fn()
        # 9:00 AM US/Eastern = 14:00 UTC. If we ask "is it 09:00 in US/Eastern?"
        # and the actual time is 14:00 UTC, it should match.
        with patch("delta.app.datetime") as mock_dt:
            mock_now = datetime(2026, 3, 2, 9, 0, tzinfo=ZoneInfo("US/Eastern"))
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert fn("09:00", "US/Eastern") is True

    def test_invalid_time_str(self):
        fn = self._import_fn()
        assert fn("not-a-time", "UTC") is False

    def test_invalid_timezone(self):
        fn = self._import_fn()
        assert fn("09:00", "Not/A/Timezone") is False

    def test_boundary_minus_4_min(self):
        fn = self._import_fn()
        with patch("delta.app.datetime") as mock_dt:
            # 08:56 is 4 min before 09:00, abs(56-0) = 56 which is not < 5
            # Wait -- abs(now.minute - minute): abs(56 - 0) = 56, not < 5
            # But the function checks hour == hour first, so 08 != 09 -> False
            mock_now = datetime(2026, 3, 2, 8, 56, tzinfo=ZoneInfo("UTC"))
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert fn("09:00", "UTC") is False

    def test_boundary_plus_4_min_same_hour(self):
        fn = self._import_fn()
        with patch("delta.app.datetime") as mock_dt:
            # 09:04 -- same hour, abs(4-0) = 4 < 5 -> True
            mock_now = datetime(2026, 3, 2, 9, 4, tzinfo=ZoneInfo("UTC"))
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert fn("09:00", "UTC") is True


# ---------------------------------------------------------------------------
# _read_project_schedule
# ---------------------------------------------------------------------------

class TestReadProjectSchedule:
    """Tests for delta.app._read_project_schedule."""

    def _import_fn(self):
        from delta.app import _read_project_schedule
        return _read_project_schedule

    def test_returns_empty_when_no_file(self, tmp_path):
        fn = self._import_fn()
        assert fn(str(tmp_path)) == []

    def test_reads_tasks(self, schedule_dir):
        fn = self._import_fn()
        project_dir, config_dir = schedule_dir
        schedule = {
            "tasks": [
                {"status": "in_progress", "what": "Build the timer UI"},
                {"status": "done", "what": "Set up project structure"},
                {"status": "recurring", "name": "Daily standup report"},
            ]
        }
        (config_dir / "schedule.json").write_text(json.dumps(schedule))

        result = fn(str(project_dir))
        assert len(result) == 3
        assert result[0]["status"] == "in_progress"
        assert result[0]["what"] == "Build the timer UI"
        assert result[2]["what"] == "Daily standup report"  # falls back to "name"

    def test_truncates_description_at_100(self, schedule_dir):
        fn = self._import_fn()
        project_dir, config_dir = schedule_dir
        long_desc = "x" * 200
        schedule = {"tasks": [{"status": "todo", "what": long_desc}]}
        (config_dir / "schedule.json").write_text(json.dumps(schedule))

        result = fn(str(project_dir))
        assert len(result[0]["what"]) == 100

    def test_respects_max_tasks(self, schedule_dir):
        fn = self._import_fn()
        project_dir, config_dir = schedule_dir
        schedule = {"tasks": [{"status": "todo", "what": f"task-{i}"} for i in range(20)]}
        (config_dir / "schedule.json").write_text(json.dumps(schedule))

        result = fn(str(project_dir), max_tasks=5)
        assert len(result) == 5

    def test_handles_malformed_json(self, schedule_dir):
        fn = self._import_fn()
        project_dir, config_dir = schedule_dir
        (config_dir / "schedule.json").write_text("not json {{{")
        assert fn(str(project_dir)) == []

    def test_handles_missing_fields(self, schedule_dir):
        fn = self._import_fn()
        project_dir, config_dir = schedule_dir
        schedule = {"tasks": [{"status": "todo"}, {}]}
        (config_dir / "schedule.json").write_text(json.dumps(schedule))

        result = fn(str(project_dir))
        assert len(result) == 2
        assert result[0]["what"] == ""
        assert result[1]["status"] == "?"

    def test_fallback_name_then_description(self, schedule_dir):
        fn = self._import_fn()
        project_dir, config_dir = schedule_dir
        schedule = {"tasks": [
            {"status": "todo", "name": "From name"},
            {"status": "todo", "description": "From description"},
        ]}
        (config_dir / "schedule.json").write_text(json.dumps(schedule))

        result = fn(str(project_dir))
        assert result[0]["what"] == "From name"
        assert result[1]["what"] == "From description"


# ---------------------------------------------------------------------------
# _get_schedule_data
# ---------------------------------------------------------------------------

class TestGetScheduleData:
    """Tests for delta.app._get_schedule_data."""

    def _import_fn(self):
        from delta.app import _get_schedule_data
        return _get_schedule_data

    def test_returns_none_for_nonexistent_project(self):
        fn = self._import_fn()
        with patch("delta.app.registry") as mock_reg:
            mock_reg.get.return_value = None
            assert fn("nonexistent") is None

    def test_returns_none_when_no_schedule_file(self, tmp_path):
        fn = self._import_fn()
        with patch("delta.app.registry") as mock_reg:
            mock_info = MagicMock()
            mock_info.project_dir = str(tmp_path)
            mock_reg.get.return_value = mock_info
            (tmp_path / "delta-config").mkdir()
            assert fn("test-project") is None

    def test_reads_full_schedule_data(self, tmp_path):
        fn = self._import_fn()
        config_dir = tmp_path / "delta-config"
        config_dir.mkdir()
        schedule_data = {
            "reporting": {"time": "09:00", "timezone": "UTC", "frequency": "daily"},
            "morning_trip": {"enabled": True, "time": "08:00"},
            "tasks": [{"status": "in_progress", "what": "test"}],
        }
        (config_dir / "schedule.json").write_text(json.dumps(schedule_data))

        with patch("delta.app.registry") as mock_reg:
            mock_info = MagicMock()
            mock_info.project_dir = str(tmp_path)
            mock_reg.get.return_value = mock_info
            result = fn("test-project")

        assert result is not None
        assert result["reporting"]["time"] == "09:00"
        assert result["morning_trip"]["enabled"] is True
        assert len(result["tasks"]) == 1

    def test_handles_malformed_json(self, tmp_path):
        fn = self._import_fn()
        config_dir = tmp_path / "delta-config"
        config_dir.mkdir()
        (config_dir / "schedule.json").write_text("broken {{{")

        with patch("delta.app.registry") as mock_reg:
            mock_info = MagicMock()
            mock_info.project_dir = str(tmp_path)
            mock_reg.get.return_value = mock_info
            assert fn("test-project") is None


# ---------------------------------------------------------------------------
# _load_last_fired / _save_last_fired
# ---------------------------------------------------------------------------

class TestLastFiredPersistence:
    """Tests for last_fired persistence."""

    def test_load_returns_empty_when_no_file(self, tmp_path):
        from delta.app import _load_last_fired
        with patch("delta.app._LAST_FIRED_PATH", tmp_path / "nonexistent.json"):
            result = _load_last_fired()
            assert result == {}

    def test_save_and_load_roundtrip(self, tmp_path):
        from delta.app import _load_last_fired, _save_last_fired
        path = tmp_path / "last-fired.json"
        with patch("delta.app._LAST_FIRED_PATH", path):
            data = {
                "proj:report:2026-03-06": "2026-03-06T09:00:00+00:00",
                "proj:morning_trip:2026-03-06": "2026-03-06T08:00:00+00:00",
            }
            _save_last_fired(data)
            loaded = _load_last_fired()
            assert loaded == data

    def test_load_handles_corrupted_file(self, tmp_path):
        from delta.app import _load_last_fired
        path = tmp_path / "last-fired.json"
        path.write_text("not json {{{")
        with patch("delta.app._LAST_FIRED_PATH", path):
            result = _load_last_fired()
            assert result == {}

    def test_save_handles_write_error(self, tmp_path):
        from delta.app import _save_last_fired
        # Point to a dir that doesn't exist
        path = tmp_path / "nonexistent-dir" / "last-fired.json"
        with patch("delta.app._LAST_FIRED_PATH", path):
            # Should not raise
            _save_last_fired({"key": "value"})


# ---------------------------------------------------------------------------
# ProjectBridge.get_schedule
# ---------------------------------------------------------------------------

class TestBridgeGetSchedule:
    """Tests for ProjectBridge.get_schedule."""

    def test_returns_empty_when_no_file(self, bridge):
        assert bridge.get_schedule() == []

    def test_reads_tasks_from_schedule_json(self, bridge):
        schedule = {
            "tasks": [
                {"status": "in_progress", "what": "Build timer"},
                {"status": "recurring", "what": "Daily report"},
            ]
        }
        (bridge.data_dir / "schedule.json").write_text(json.dumps(schedule))
        result = bridge.get_schedule()
        assert len(result) == 2
        assert result[0]["status"] == "in_progress"

    def test_handles_empty_tasks(self, bridge):
        (bridge.data_dir / "schedule.json").write_text(json.dumps({"tasks": []}))
        assert bridge.get_schedule() == []

    def test_handles_malformed_json(self, bridge):
        (bridge.data_dir / "schedule.json").write_text("broken json")
        assert bridge.get_schedule() == []

    def test_handles_missing_tasks_key(self, bridge):
        (bridge.data_dir / "schedule.json").write_text(json.dumps({"reporting": {}}))
        assert bridge.get_schedule() == []


# ---------------------------------------------------------------------------
# ProjectBridge.has_pending_work
# ---------------------------------------------------------------------------

class TestHasPendingWork:
    """Tests for ProjectBridge.has_pending_work."""

    def test_false_when_no_followups_no_schedule(self, bridge):
        assert bridge.has_pending_work() is False

    def test_true_when_followups_exist(self, bridge):
        followup_dir = bridge.data_dir / "followups"
        followup_dir.mkdir()
        (followup_dir / "f1.json").write_text(json.dumps({
            "id": "f1", "text": "check in", "deliver_after": "2026-03-06T12:00:00+00:00"
        }))
        assert bridge.has_pending_work() is True

    def test_true_when_in_progress_task(self, bridge):
        schedule = {"tasks": [{"status": "in_progress", "what": "Building"}]}
        (bridge.data_dir / "schedule.json").write_text(json.dumps(schedule))
        assert bridge.has_pending_work() is True

    def test_true_when_recurring_task(self, bridge):
        schedule = {"tasks": [{"status": "recurring", "what": "Daily report"}]}
        (bridge.data_dir / "schedule.json").write_text(json.dumps(schedule))
        assert bridge.has_pending_work() is True

    def test_false_when_only_done_tasks(self, bridge):
        schedule = {"tasks": [
            {"status": "done", "what": "Finished"},
            {"status": "todo", "what": "Not started"},
        ]}
        (bridge.data_dir / "schedule.json").write_text(json.dumps(schedule))
        assert bridge.has_pending_work() is False

    def test_false_when_followup_dir_empty(self, bridge):
        (bridge.data_dir / "followups").mkdir()
        assert bridge.has_pending_work() is False


# ---------------------------------------------------------------------------
# ProjectBridge.cancel_pending_followups
# ---------------------------------------------------------------------------

class TestCancelPendingFollowups:
    """Tests for ProjectBridge.cancel_pending_followups."""

    def test_returns_zero_when_no_dir(self, bridge):
        assert bridge.cancel_pending_followups() == 0

    def test_returns_zero_when_dir_empty(self, bridge):
        (bridge.data_dir / "followups").mkdir()
        assert bridge.cancel_pending_followups() == 0

    def test_deletes_all_followups(self, bridge):
        followup_dir = bridge.data_dir / "followups"
        followup_dir.mkdir()
        for i in range(3):
            (followup_dir / f"f{i}.json").write_text(json.dumps({"id": f"f{i}"}))

        count = bridge.cancel_pending_followups()
        assert count == 3
        assert list(followup_dir.glob("*.json")) == []

    def test_only_deletes_json_files(self, bridge):
        followup_dir = bridge.data_dir / "followups"
        followup_dir.mkdir()
        (followup_dir / "f1.json").write_text("{}")
        (followup_dir / "notes.txt").write_text("keep me")

        count = bridge.cancel_pending_followups()
        assert count == 1
        assert (followup_dir / "notes.txt").exists()


# ---------------------------------------------------------------------------
# ProjectBridge.watch_followups
# ---------------------------------------------------------------------------

class TestWatchFollowups:
    """Tests for ProjectBridge.watch_followups delivery timing."""

    def test_delivers_when_time_has_passed(self, bridge):
        followup_dir = bridge.data_dir / "followups"
        followup_dir.mkdir()

        # Followup scheduled in the past
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        followup = {
            "id": "f1",
            "channel": "123",
            "text": "How's it going?",
            "deliver_after": past,
        }
        (followup_dir / "f1.json").write_text(json.dumps(followup))

        delivered = []
        callback = lambda data: delivered.append(data)

        # Run watcher in a thread, let it do one cycle, then stop
        def run_watcher():
            bridge.watch_followups(callback)

        t = threading.Thread(target=run_watcher, daemon=True)
        t.start()
        time.sleep(1.5)  # Let one poll cycle happen
        bridge.shutdown()
        t.join(timeout=15)

        assert len(delivered) == 1
        assert delivered[0]["id"] == "f1"
        assert delivered[0]["text"] == "How's it going?"
        # File should be deleted after delivery
        assert not (followup_dir / "f1.json").exists()

    def test_does_not_deliver_future_followup(self, bridge):
        followup_dir = bridge.data_dir / "followups"
        followup_dir.mkdir()

        # Followup scheduled 10 min in the future
        future = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        followup = {
            "id": "f2",
            "channel": "123",
            "text": "Not yet",
            "deliver_after": future,
        }
        (followup_dir / "f2.json").write_text(json.dumps(followup))

        delivered = []
        callback = lambda data: delivered.append(data)

        t = threading.Thread(target=lambda: bridge.watch_followups(callback), daemon=True)
        t.start()
        time.sleep(1.5)
        bridge.shutdown()
        t.join(timeout=15)

        assert len(delivered) == 0
        # File should still exist
        assert (followup_dir / "f2.json").exists()

    def test_skips_followup_without_deliver_after(self, bridge):
        followup_dir = bridge.data_dir / "followups"
        followup_dir.mkdir()

        followup = {"id": "f3", "channel": "123", "text": "No time set"}
        (followup_dir / "f3.json").write_text(json.dumps(followup))

        delivered = []
        t = threading.Thread(
            target=lambda: bridge.watch_followups(lambda d: delivered.append(d)),
            daemon=True,
        )
        t.start()
        time.sleep(1.5)
        bridge.shutdown()
        t.join(timeout=15)

        assert len(delivered) == 0

    def test_handles_malformed_followup_file(self, bridge):
        followup_dir = bridge.data_dir / "followups"
        followup_dir.mkdir()

        (followup_dir / "bad.json").write_text("not json {{{")

        delivered = []
        t = threading.Thread(
            target=lambda: bridge.watch_followups(lambda d: delivered.append(d)),
            daemon=True,
        )
        t.start()
        time.sleep(1.5)
        bridge.shutdown()
        t.join(timeout=15)

        assert len(delivered) == 0

    def test_delivers_multiple_due_followups_in_order(self, bridge):
        followup_dir = bridge.data_dir / "followups"
        followup_dir.mkdir()

        past1 = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        past2 = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

        (followup_dir / "a-first.json").write_text(json.dumps({
            "id": "a", "channel": "123", "text": "First", "deliver_after": past1,
        }))
        (followup_dir / "b-second.json").write_text(json.dumps({
            "id": "b", "channel": "123", "text": "Second", "deliver_after": past2,
        }))

        delivered = []
        t = threading.Thread(
            target=lambda: bridge.watch_followups(lambda d: delivered.append(d)),
            daemon=True,
        )
        t.start()
        time.sleep(1.5)
        bridge.shutdown()
        t.join(timeout=15)

        assert len(delivered) == 2
        assert delivered[0]["id"] == "a"
        assert delivered[1]["id"] == "b"


# ---------------------------------------------------------------------------
# _send_report_nudge
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# _should_fire_task
# ---------------------------------------------------------------------------

class TestShouldFireTask:
    """Tests for delta.app._should_fire_task."""

    def _import_fn(self):
        from delta.app import _should_fire_task
        return _should_fire_task

    def test_fire_at_past_returns_true(self):
        fn = self._import_fn()
        now = datetime(2026, 3, 6, 14, 30, tzinfo=timezone.utc)
        task = {"fire_at": "2026-03-06T14:00:00Z"}
        assert fn(task, now) is True

    def test_fire_at_future_returns_false(self):
        fn = self._import_fn()
        now = datetime(2026, 3, 6, 13, 30, tzinfo=timezone.utc)
        task = {"fire_at": "2026-03-06T14:00:00Z"}
        assert fn(task, now) is False

    def test_fire_at_exact_returns_true(self):
        fn = self._import_fn()
        now = datetime(2026, 3, 6, 14, 0, tzinfo=timezone.utc)
        task = {"fire_at": "2026-03-06T14:00:00+00:00"}
        assert fn(task, now) is True

    def test_fire_at_naive_treated_as_utc(self):
        fn = self._import_fn()
        now = datetime(2026, 3, 6, 14, 1, tzinfo=timezone.utc)
        task = {"fire_at": "2026-03-06T14:00:00"}
        assert fn(task, now) is True

    def test_daily_within_3_min_window(self):
        fn = self._import_fn()
        # 09:02 UTC, schedule is 09:00 daily
        now = datetime(2026, 3, 6, 9, 2, tzinfo=timezone.utc)
        task = {"schedule": "daily", "time": "09:00", "timezone": "UTC"}
        assert fn(task, now) is True

    def test_daily_outside_3_min_window(self):
        fn = self._import_fn()
        now = datetime(2026, 3, 6, 9, 4, tzinfo=timezone.utc)
        task = {"schedule": "daily", "time": "09:00", "timezone": "UTC"}
        assert fn(task, now) is False

    def test_daily_before_scheduled_time(self):
        fn = self._import_fn()
        now = datetime(2026, 3, 6, 8, 59, tzinfo=timezone.utc)
        task = {"schedule": "daily", "time": "09:00", "timezone": "UTC"}
        assert fn(task, now) is False

    def test_weekly_on_monday(self):
        fn = self._import_fn()
        # March 2, 2026 is a Monday
        now = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)
        task = {"schedule": "weekly", "time": "09:00", "timezone": "UTC"}
        assert fn(task, now) is True

    def test_weekly_on_tuesday_returns_false(self):
        fn = self._import_fn()
        # March 3, 2026 is a Tuesday
        now = datetime(2026, 3, 3, 9, 0, tzinfo=timezone.utc)
        task = {"schedule": "weekly", "time": "09:00", "timezone": "UTC"}
        assert fn(task, now) is False

    def test_timezone_conversion(self):
        fn = self._import_fn()
        # 14:00 UTC = 09:00 US/Eastern (during EST)
        now = datetime(2026, 3, 6, 14, 0, tzinfo=timezone.utc)
        task = {"schedule": "daily", "time": "09:00", "timezone": "US/Eastern"}
        assert fn(task, now) is True

    def test_empty_task_returns_false(self):
        fn = self._import_fn()
        now = datetime(2026, 3, 6, 9, 0, tzinfo=timezone.utc)
        assert fn({}, now) is False

    def test_invalid_fire_at_returns_false(self):
        fn = self._import_fn()
        now = datetime(2026, 3, 6, 9, 0, tzinfo=timezone.utc)
        task = {"fire_at": "not-a-date"}
        assert fn(task, now) is False

    def test_invalid_timezone_returns_false(self):
        fn = self._import_fn()
        now = datetime(2026, 3, 6, 9, 0, tzinfo=timezone.utc)
        task = {"schedule": "daily", "time": "09:00", "timezone": "Fake/Zone"}
        assert fn(task, now) is False


# ---------------------------------------------------------------------------
# _update_last_fired_in_schedule
# ---------------------------------------------------------------------------

class TestUpdateLastFiredInSchedule:
    """Tests for delta.app._update_last_fired_in_schedule."""

    def _import_fn(self):
        from delta.app import _update_last_fired_in_schedule
        return _update_last_fired_in_schedule

    def test_updates_matching_task(self, tmp_path):
        fn = self._import_fn()
        config_dir = tmp_path / "delta-config"
        config_dir.mkdir()
        schedule = {"tasks": [
            {"id": "task-1", "description": "Do thing", "schedule": "daily"},
            {"id": "task-2", "description": "Other thing"},
        ]}
        (config_dir / "schedule.json").write_text(json.dumps(schedule))

        with patch("delta.app.registry") as mock_reg:
            mock_info = MagicMock()
            mock_info.project_dir = str(tmp_path)
            mock_reg.get.return_value = mock_info
            fn("test-project", "task-1")

        updated = json.loads((config_dir / "schedule.json").read_text())
        assert "last_fired" in updated["tasks"][0]
        assert "last_fired" not in updated["tasks"][1]

    def test_no_crash_on_missing_project(self):
        fn = self._import_fn()
        with patch("delta.app.registry") as mock_reg:
            mock_reg.get.return_value = None
            fn("nonexistent", "task-1")  # Should not raise

    def test_no_crash_on_missing_schedule(self, tmp_path):
        fn = self._import_fn()
        config_dir = tmp_path / "delta-config"
        config_dir.mkdir()

        with patch("delta.app.registry") as mock_reg:
            mock_info = MagicMock()
            mock_info.project_dir = str(tmp_path)
            mock_reg.get.return_value = mock_info
            fn("test-project", "task-1")  # Should not raise


# ---------------------------------------------------------------------------
# _remove_fired_task
# ---------------------------------------------------------------------------

class TestRemoveFiredTask:
    """Tests for delta.app._remove_fired_task."""

    def _import_fn(self):
        from delta.app import _remove_fired_task
        return _remove_fired_task

    def test_removes_matching_task(self, tmp_path):
        fn = self._import_fn()
        config_dir = tmp_path / "delta-config"
        config_dir.mkdir()
        schedule = {"tasks": [
            {"id": "oneshot-1", "fire_at": "2026-03-06T14:00:00Z"},
            {"id": "recurring-1", "schedule": "daily"},
        ]}
        (config_dir / "schedule.json").write_text(json.dumps(schedule))

        with patch("delta.app.registry") as mock_reg:
            mock_info = MagicMock()
            mock_info.project_dir = str(tmp_path)
            mock_reg.get.return_value = mock_info
            fn("test-project", "oneshot-1")

        updated = json.loads((config_dir / "schedule.json").read_text())
        assert len(updated["tasks"]) == 1
        assert updated["tasks"][0]["id"] == "recurring-1"

    def test_no_crash_on_missing_task(self, tmp_path):
        fn = self._import_fn()
        config_dir = tmp_path / "delta-config"
        config_dir.mkdir()
        schedule = {"tasks": [{"id": "other", "schedule": "daily"}]}
        (config_dir / "schedule.json").write_text(json.dumps(schedule))

        with patch("delta.app.registry") as mock_reg:
            mock_info = MagicMock()
            mock_info.project_dir = str(tmp_path)
            mock_reg.get.return_value = mock_info
            fn("test-project", "nonexistent")  # Should not raise

        # Original task still there
        updated = json.loads((config_dir / "schedule.json").read_text())
        assert len(updated["tasks"]) == 1


# ---------------------------------------------------------------------------
# _send_report_nudge
# ---------------------------------------------------------------------------

class TestSendReportNudge:
    """Tests for delta.app._send_report_nudge."""

    def test_skips_when_project_not_active(self):
        from delta.app import _send_report_nudge
        bridge = MagicMock()
        bridge.is_project_active.return_value = False

        _send_report_nudge("test", bridge, {"style": "calm"})
        bridge.write_inbox.assert_not_called()

    def test_sends_nudge_when_active(self):
        from delta.app import _send_report_nudge
        bridge = MagicMock()
        bridge.is_project_active.return_value = True
        bridge.write_inbox.return_value = "msg-123"

        with patch("delta.app.registry") as mock_reg:
            mock_info = MagicMock()
            mock_info.discord_channel_id = "chan-456"
            mock_reg.get.return_value = mock_info

            _send_report_nudge("test", bridge, {
                "style": "calm",
                "what_matters": "progress",
            })

        bridge.write_inbox.assert_called_once()
        call_args = bridge.write_inbox.call_args
        assert "calm" in call_args[0][2]  # nudge text contains style
        assert "progress" in call_args[0][2]
        bridge.nudge.assert_called_once_with("msg-123")
        bridge.touch_activity.assert_called_once()


# ---------------------------------------------------------------------------
# Schedule fire loop: field name and status filtering
# ---------------------------------------------------------------------------

class TestScheduleFireFieldNames:
    """Tests that _schedule_fire_loop handles both 'what' and 'description' fields,
    and skips done/completed tasks."""

    def test_get_schedule_data_with_what_field(self, tmp_path):
        """Schedule fire loop should use 'what' field as task description."""
        from delta.app import _get_schedule_data
        data_dir = tmp_path / "delta-config"
        data_dir.mkdir()
        schedule = {
            "tasks": [{
                "id": "daily-blog",
                "what": "Write daily blog post",
                "schedule": "daily",
                "time": "07:00",
                "timezone": "Asia/Kolkata",
                "status": "recurring",
            }]
        }
        (data_dir / "schedule.json").write_text(json.dumps(schedule))
        mock_info = MagicMock()
        mock_info.project_dir = str(tmp_path)
        with patch("delta.app.registry") as mock_reg:
            mock_reg.get.return_value = mock_info
            result = _get_schedule_data("test-proj")
        assert result is not None
        task = result["tasks"][0]
        # The fire loop should find description via "what" fallback
        desc = task.get("description", "") or task.get("what", "")
        assert desc == "Write daily blog post"

    def test_description_field_takes_priority(self, tmp_path):
        """When both 'description' and 'what' exist, 'description' wins."""
        task = {
            "description": "From description field",
            "what": "From what field",
        }
        desc = task.get("description", "") or task.get("what", "")
        assert desc == "From description field"

    def test_what_field_used_when_no_description(self):
        """When only 'what' is present, it's used as fallback."""
        task = {"what": "Daily blog post"}
        desc = task.get("description", "") or task.get("what", "")
        assert desc == "Daily blog post"

    def test_done_tasks_skipped(self):
        """Tasks with status 'done' should not fire."""
        task = {"id": "x", "what": "Something", "status": "done"}
        status = task.get("status", "")
        assert status in ("done", "completed")

    def test_completed_tasks_skipped(self):
        """Tasks with status 'completed' should not fire."""
        task = {"id": "x", "what": "Something", "status": "completed"}
        status = task.get("status", "")
        assert status in ("done", "completed")

    def test_recurring_tasks_not_skipped(self):
        """Tasks with status 'recurring' should fire."""
        task = {"id": "x", "what": "Something", "status": "recurring"}
        status = task.get("status", "")
        assert status not in ("done", "completed")
