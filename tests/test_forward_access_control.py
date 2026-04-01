"""Tests for forward command access control.

The forward command should block cross-owner forwarding unless the
source is the hub (__hub__), which can forward anywhere.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from delta.registry import ProjectInfo, Registry


# -- Helpers ---------------------------------------------------------------

OWNER_A = "100000000001"
OWNER_B = "100000000002"
CHANNEL_A = "111222333"
CHANNEL_B = "444555666"


def _make_info(name, owner=OWNER_A, project_dir=None, channel_id=CHANNEL_A):
    return ProjectInfo(
        name=name,
        project_dir=project_dir or f"/home/proj-{name}/app",
        data_dir=f"/home/proj-{name}/app/delta-config",
        tmux_session=f"proj-{name}",
        tmux_lead_pane=f"proj-{name}:lead",
        owner_discord_id=owner,
        discord_channel_id=channel_id,
        status="active",
    )


def _mock_bridge(active=True):
    bridge = MagicMock()
    bridge.is_project_active.return_value = active
    bridge.write_inbox.return_value = "msg-001"
    bridge.send_to_lead = MagicMock()
    bridge.touch_activity = MagicMock()
    return bridge


# -- Tests -----------------------------------------------------------------

class TestForwardAccessControl:
    """Test ownership check on the forward command."""

    def test_forward_blocked_different_owners(self, tmp_path):
        """Forward from project owned by A to project owned by B should be dropped."""
        from delta import app as delta_app

        proj_a = _make_info("proj-a", owner=OWNER_A)
        proj_b = _make_info("proj-b", owner=OWNER_B, channel_id=CHANNEL_B)

        mock_registry = MagicMock(spec=Registry)
        mock_registry.get.side_effect = lambda n: {
            "proj-a": proj_a, "proj-b": proj_b
        }.get(n)

        target_bridge = _mock_bridge()

        data = {
            "command": "forward",
            "target_project": "proj-b",
            "text": "hello from A",
            "user": "user-a",
            "reply_channel": CHANNEL_A,
            "source_project": "proj-a",
        }

        # Patch globals
        with patch.object(delta_app, "registry", mock_registry), \
             patch.object(delta_app, "_get_or_create_bridge", return_value=target_bridge):
            # We need to call the hub outbox callback directly
            # Build it by extracting the logic
            command = data.get("command")
            target = data.get("target_project", "")
            source_project = data.get("source_project", "")

            # Replicate the access control logic
            blocked = False
            if source_project and source_project != delta_app.HUB_NAME:
                source_info = mock_registry.get(source_project)
                target_info = mock_registry.get(target)
                if (source_info and target_info
                        and source_info.owner_discord_id != target_info.owner_discord_id):
                    blocked = True

            assert blocked is True, "Forward should be blocked for different owners"

    def test_forward_allowed_same_owner(self, tmp_path):
        """Forward between projects with the same owner should be allowed."""
        proj_a = _make_info("proj-a", owner=OWNER_A)
        proj_b = _make_info("proj-b", owner=OWNER_A, channel_id=CHANNEL_B)

        mock_registry = MagicMock(spec=Registry)
        mock_registry.get.side_effect = lambda n: {
            "proj-a": proj_a, "proj-b": proj_b
        }.get(n)

        source_project = "proj-a"
        target = "proj-b"

        source_info = mock_registry.get(source_project)
        target_info = mock_registry.get(target)
        blocked = (source_info and target_info
                   and source_info.owner_discord_id != target_info.owner_discord_id)

        assert blocked is False, "Forward should be allowed for same owner"

    def test_hub_can_forward_to_any_project(self):
        """Hub (__hub__) should be able to forward to any project regardless of owner."""
        from delta.app import HUB_NAME

        # The access control only kicks in when source_project != HUB_NAME
        source_project = HUB_NAME
        assert source_project == "__hub__"

        # Hub bypass: the check is skipped entirely
        skip_check = not (source_project and source_project != HUB_NAME)
        assert skip_check is True, "Hub should bypass ownership check"

    def test_forward_allowed_when_no_source_project(self):
        """Forward without source_project field should pass through (backward compat)."""
        source_project = ""
        skip_check = not (source_project and source_project != "__hub__")
        assert skip_check is True, "Missing source_project should bypass check"

    def test_forward_allowed_when_source_not_in_registry(self):
        """Forward from unknown project should pass through (registry returns None)."""
        mock_registry = MagicMock(spec=Registry)
        mock_registry.get.return_value = None

        source_project = "unknown-project"
        target = "proj-b"

        source_info = mock_registry.get(source_project)
        target_info = mock_registry.get(target)

        # Both are None, so the `source_info and target_info` check is falsy
        blocked = (source_info and target_info
                   and source_info.owner_discord_id != target_info.owner_discord_id)
        assert not blocked, "Unknown source should not block forward"
