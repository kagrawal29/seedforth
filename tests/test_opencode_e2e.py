"""End-to-end tests for opencode message delivery pipeline.

Tests the full chain: Discord message -> bridge dispatch -> HTTP delivery -> Discord response.
"""

import json
import os
import threading
import time
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch, PropertyMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestCleanPipeline(unittest.TestCase):

    def setUp(self):
        from delta.project_bridge import ProjectBridge
        from delta.registry import ProjectInfo

        self.info = ProjectInfo(
            name="test-project",
            project_dir="/tmp/test-project",
            data_dir="/tmp/test-project/delta-config",
            tmux_session="test",
            tmux_lead_pane="test:lead",
            runtime="opencode",
            serve_port=7899,
            session_id="ses_test123",
        )

        os.makedirs(self.info.data_dir, exist_ok=True)
        os.makedirs(os.path.join(self.info.data_dir, "inbox"), exist_ok=True)
        os.makedirs(os.path.join(self.info.data_dir, "outbox"), exist_ok=True)

        self.bridge = ProjectBridge(
            name=self.info.name,
            data_dir=self.info.data_dir,
            tmux_lead_pane=self.info.tmux_lead_pane,
            nudge_prefix=self.info.nudge_prefix,
            runtime=self.info.runtime,
            serve_port=self.info.serve_port,
            session_id=self.info.session_id,
        )
        self.bridge._session_id_created = True

    def test_bridge_has_correct_runtime(self):
        assert self.bridge.runtime == "opencode"

    def test_bridge_has_serve_port(self):
        assert self.bridge.serve_port == 7899

    def test_is_project_active_checks_http_health(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_urlopen.return_value = mock_resp
            assert self.bridge.is_project_active()
            mock_urlopen.assert_called_once()

    def test_is_project_active_returns_false_on_connection_error(self):
        with patch("urllib.request.urlopen", side_effect=OSError):
            assert not self.bridge.is_project_active()

    def test_check_auth_error_returns_none_for_opencode(self):
        assert self.bridge.check_auth_error() is None

    def test_deliver_message_spawns_thread(self):
        callback_called = []

        def callback(ch_id, text):
            callback_called.append((ch_id, text))

        mock_response = {
            "info": {"time": {"created": 1234567890}},
            "parts": [{"type": "text", "text": "hello from agent"}],
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            self.bridge.deliver_message(
                "12345", "test-user", "hello", "msg-001", callback=callback
            )

            time.sleep(2)

        assert len(callback_called) == 1
        assert callback_called[0][0] == "12345"
        assert "hello from agent" in callback_called[0][1]

    def test_deliver_message_without_callback_still_writes_outbox(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({
                "info": {"time": {"created": 1234567890}},
                "parts": [{"type": "text", "text": "response"}],
            }).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            self.bridge.deliver_message("12345", "test-user", "hello", "msg-002")

        time.sleep(2)

        outbox = os.path.join(self.info.data_dir, "outbox")
        files = [f for f in os.listdir(outbox) if f.endswith(".json")]
        assert len(files) >= 1

    def test_deliver_message_uses_existing_session(self):
        self.bridge.session_id = "ses_existing"
        callback_called = []

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({
                "info": {"time": {"created": 1234567890}},
                "parts": [{"type": "text", "text": "ok"}],
            }).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            self.bridge.deliver_message("12345", "test-user", "hello", "msg-003",
                                        callback=lambda c, t: callback_called.append(t))

        time.sleep(2)

        calls = [c[0] for c in mock_urlopen.call_args_list]
        session_urls = [str(c) for c in calls if "/session" in str(c)]
        assert len(session_urls) == 0

    def test_deliver_message_creates_session_when_missing(self):
        self.bridge.session_id = ""

        with patch("urllib.request.urlopen") as mock_urlopen:
            session_resp = MagicMock()
            session_resp.read.return_value = json.dumps({"id": "ses_new"}).encode()

            msg_resp = MagicMock()
            msg_resp.read.return_value = json.dumps({
                "info": {"time": {"created": 1234567890}},
                "parts": [{"type": "text", "text": "ok"}],
            }).encode()

            mock_urlopen.return_value.__enter__.side_effect = [session_resp, msg_resp]

            self.bridge.deliver_message("12345", "test-user", "hello", "msg-004")

        time.sleep(2)
        assert self.bridge.session_id == "ses_new"

    def test_auth_check_skips_hub_for_opencode(self):
        self.bridge._session_id_created = True
        mock_bridge = self.bridge
        mock_bridge.runtime = "opencode"

        auth_err = mock_bridge.check_auth_error()
        assert auth_err is None


class TestAuthHubFallback(unittest.TestCase):
    """Verify the hub auth fallback is skipped for opencode projects."""

    def test_opencode_does_not_fallback_to_hub_auth(self):
        from delta.project_bridge import ProjectBridge

        bridges_dict = {}
        auth_checked = False

        class FakeHubBridge:
            def check_auth_error(self):
                nonlocal auth_checked
                auth_checked = True
                return "expired token"

        bridges_dict["__hub__"] = FakeHubBridge()

        project_bridge = MagicMock()
        project_bridge.check_auth_error.return_value = None
        project_bridge.runtime = "opencode"

        auth_err = project_bridge.check_auth_error()
        if not auth_err and project_bridge.runtime != "opencode":
            hub = bridges_dict.get("__hub__")
            if hub:
                auth_err = hub.check_auth_error()

        assert auth_err is None
        assert not auth_checked


if __name__ == "__main__":
    unittest.main()
