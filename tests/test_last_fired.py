"""Tests for last_fired persistence (report/morning_trip double-fire prevention)."""

import json
from pathlib import Path
from unittest.mock import patch

from delta import app


class TestLoadLastFired:
    """Tests for _load_last_fired."""

    def test_returns_empty_when_no_file(self, tmp_path):
        with patch.object(app, "_LAST_FIRED_PATH", tmp_path / "missing.json"):
            assert app._load_last_fired() == {}

    def test_loads_existing_file(self, tmp_path):
        path = tmp_path / "last-fired.json"
        data = {"proj:report:2026-03-06": "2026-03-06T09:00:00+00:00"}
        path.write_text(json.dumps(data))
        with patch.object(app, "_LAST_FIRED_PATH", path):
            result = app._load_last_fired()
            assert result == data

    def test_returns_empty_on_corrupt_json(self, tmp_path):
        path = tmp_path / "last-fired.json"
        path.write_text("not valid json{{{")
        with patch.object(app, "_LAST_FIRED_PATH", path):
            assert app._load_last_fired() == {}


class TestSaveLastFired:
    """Tests for _save_last_fired."""

    def test_writes_json_file(self, tmp_path):
        path = tmp_path / "last-fired.json"
        data = {"proj:report:2026-03-06": "2026-03-06T09:00:00+00:00"}
        with patch.object(app, "_LAST_FIRED_PATH", path):
            app._save_last_fired(data)
        assert path.exists()
        assert json.loads(path.read_text()) == data

    def test_overwrites_existing(self, tmp_path):
        path = tmp_path / "last-fired.json"
        path.write_text(json.dumps({"old": "data"}))
        new_data = {"new": "data"}
        with patch.object(app, "_LAST_FIRED_PATH", path):
            app._save_last_fired(new_data)
        assert json.loads(path.read_text()) == new_data

    def test_survives_unwritable_path(self, tmp_path):
        path = tmp_path / "nonexistent-dir" / "last-fired.json"
        with patch.object(app, "_LAST_FIRED_PATH", path):
            # Should not raise
            app._save_last_fired({"key": "val"})


class TestRoundTrip:
    """Test save then load preserves data."""

    def test_roundtrip(self, tmp_path):
        path = tmp_path / "last-fired.json"
        data = {
            "myproject:report:2026-03-06": "2026-03-06T09:00:00+00:00",
            "myproject:morning_trip:2026-03-06": "2026-03-06T09:05:00+00:00",
        }
        with patch.object(app, "_LAST_FIRED_PATH", path):
            app._save_last_fired(data)
            loaded = app._load_last_fired()
        assert loaded == data
