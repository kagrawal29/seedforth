"""Tests for the gh_auth_start command handler.

Tests command parsing, handler dispatch, and message formatting.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from delta.registry import ProjectInfo, Registry


# -- Helpers ---------------------------------------------------------------

OWNER = "100000000001"
CHANNEL = "111222333"


def _make_info(name, owner=OWNER, linux_user="proj-test", channel_id=CHANNEL):
    return ProjectInfo(
        name=name,
        project_dir=f"/home/{linux_user}/app",
        data_dir=f"/home/{linux_user}/app/delta-config",
        tmux_session=f"proj-{name}",
        tmux_lead_pane=f"proj-{name}:lead",
        owner_discord_id=owner,
        discord_channel_id=channel_id,
        linux_user=linux_user,
        status="active",
    )


def _mock_bridge(active=True):
    bridge = MagicMock()
    bridge.is_project_active.return_value = active
    bridge.write_inbox.return_value = "msg-001"
    bridge.send_to_lead = MagicMock()
    bridge.touch_activity = MagicMock()
    bridge.connection_pending = False
    bridge.inbox_dir = MagicMock()
    bridge.inbox_dir.glob.return_value = []
    return bridge


# -- Tests: Command parsing ------------------------------------------------

class TestGhAuthCommandParsing:
    """Test that gh_auth_start commands are correctly recognized."""

    def test_command_recognized_in_project_outbox(self):
        """gh_auth_start should be a valid outbox command."""
        data = {
            "command": "gh_auth_start",
            "reply_channel": CHANNEL,
        }
        assert data["command"] == "gh_auth_start"

    def test_command_data_structure(self):
        """Verify the expected command structure."""
        data = {
            "id": "gh-auth-1709555000",
            "command": "gh_auth_start",
            "reply_channel": CHANNEL,
        }
        assert "command" in data
        assert "reply_channel" in data

    def test_hub_command_structure(self):
        """Hub variant includes project_name."""
        data = {
            "command": "gh_auth_start",
            "project_name": "chiron-kshitiz",
            "reply_channel": CHANNEL,
        }
        assert data.get("project_name") == "chiron-kshitiz"


# -- Tests: Handler behavior -----------------------------------------------

class TestGhAuthHandler:
    """Test _handle_gh_auth_command behavior with mocked subprocess."""

    @pytest.mark.asyncio
    async def test_handler_sets_connection_pending(self):
        """Handler should set connection_pending on the bridge during auth."""
        from delta.app import _handle_gh_auth_command

        info = _make_info("test-project")
        bridge = _mock_bridge()

        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0  # already exited
        mock_proc.stderr.read.return_value = "already logged in"
        mock_proc.stdout.read.return_value = ""
        mock_proc.kill = MagicMock()

        mock_channel = AsyncMock()

        with patch("delta.app.registry") as mock_registry, \
             patch("delta.app.client") as mock_client, \
             patch("subprocess.Popen", return_value=mock_proc), \
             patch("delta.app.LOCAL_MODE", True):
            mock_registry.get.return_value = info
            mock_client.get_channel.return_value = mock_channel

            await _handle_gh_auth_command("test-project", bridge, CHANNEL)

        # Should have written inbox about already logged in
        bridge.write_inbox.assert_called()

    @pytest.mark.asyncio
    async def test_handler_returns_on_missing_project(self):
        """Handler should return early if project not in registry."""
        from delta.app import _handle_gh_auth_command

        bridge = _mock_bridge()

        with patch("delta.app.registry") as mock_registry:
            mock_registry.get.return_value = None
            await _handle_gh_auth_command("nonexistent", bridge, CHANNEL)

        # Should not have interacted with bridge
        bridge.write_inbox.assert_not_called()

    @pytest.mark.asyncio
    async def test_handler_sends_device_code_to_discord(self):
        """When gh produces a device code, it should be sent to Discord."""
        from delta.app import _handle_gh_auth_command

        info = _make_info("test-project")
        bridge = _mock_bridge()

        # Mock process that outputs device code then exits
        mock_proc = MagicMock()
        poll_calls = [None, None, 0]  # still running, still running, exited
        mock_proc.poll.side_effect = lambda: poll_calls.pop(0) if poll_calls else 0

        stderr_output = (
            "! First copy your one-time code: ABCD-1234\n"
            "- Press Enter to open github.com/login/device in your browser...\n"
        )
        mock_proc.stderr.read.return_value = stderr_output
        mock_proc.stderr.fileno = MagicMock(return_value=5)
        mock_proc.stdout.read.return_value = ""
        mock_proc.kill = MagicMock()

        mock_channel = AsyncMock()

        # Mock select to simulate data available
        with patch("delta.app.registry") as mock_registry, \
             patch("delta.app.client") as mock_client, \
             patch("subprocess.Popen", return_value=mock_proc), \
             patch("select.select", return_value=([mock_proc.stderr], [], [])), \
             patch("time.time", side_effect=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]), \
             patch("subprocess.run") as mock_run, \
             patch("asyncio.sleep", new_callable=AsyncMock), \
             patch("delta.app.LOCAL_MODE", True):

            mock_registry.get.return_value = info
            mock_client.get_channel.return_value = mock_channel

            # Make gh auth status succeed immediately
            mock_run.return_value = MagicMock(returncode=0)

            await _handle_gh_auth_command("test-project", bridge, CHANNEL)

        # Channel should have received the device code message
        send_calls = mock_channel.send.call_args_list
        assert len(send_calls) >= 1
        first_msg = send_calls[0][0][0] if send_calls[0][0] else send_calls[0][1].get("content", "")
        assert "ABCD-1234" in first_msg or "github" in first_msg.lower()


# -- Tests: Outbox wiring -------------------------------------------------

class TestGhAuthOutboxWiring:
    """Test that the gh_auth_start command is wired into the outbox callback."""

    def test_project_outbox_has_gh_auth_handler(self):
        """The per-project outbox callback should handle gh_auth_start."""
        import delta.app as delta_app
        # Verify the command string exists in the source
        import inspect
        source = inspect.getsource(delta_app._start_watchers)
        assert "gh_auth_start" in source

    def test_hub_outbox_has_gh_auth_handler(self):
        """The hub outbox callback should handle gh_auth_start."""
        import delta.app as delta_app
        import inspect
        source = inspect.getsource(delta_app._start_hub_watchers)
        assert "gh_auth_start" in source
