"""Tests for _restore_active_projects() in delta.app.

After a systemd restart, active projects lose their tmux sessions and Claude
Code instances. _restore_active_projects() should detect this and recreate them.
"""

from unittest.mock import patch, MagicMock, call
import pytest


def _make_project_info(name, status="active", tmux_session=None,
                       tmux_lead_pane=None, project_dir=None,
                       linux_user=""):
    info = MagicMock()
    info.name = name
    info.status = status
    info.tmux_session = tmux_session or f"proj-{name}"
    info.tmux_lead_pane = tmux_lead_pane or f"proj-{name}:lead"
    info.project_dir = project_dir or f"/home/proj-{name}/app"
    info.linux_user = linux_user
    info.data_dir = f"/home/proj-{name}/app/delta-config"
    info.nudge_prefix = f"delta-config/inbox"
    info.discord_channel_id = "123456"
    info.last_activity = ""
    return info


@patch("delta.app.start_claude_code")
@patch("delta.app.create_tmux_session")
@patch("delta.app.is_claude_running")
@patch("delta.app.is_session_alive")
def test_restore_recreates_dead_session_and_claude(
    mock_session_alive, mock_claude_running,
    mock_create_tmux, mock_start_claude,
):
    """When tmux session is dead, restore creates session and starts Claude."""
    from delta.app import _restore_active_projects, registry

    info = _make_project_info("testproj")
    with patch.object(registry, "list_projects", return_value=["testproj"]), \
         patch.object(registry, "get", return_value=info):
        # Session dead, Claude not running
        mock_session_alive.return_value = False
        mock_claude_running.return_value = False
        mock_create_tmux.return_value = True
        mock_start_claude.return_value = True

        count = _restore_active_projects()

    assert count == 1
    mock_create_tmux.assert_called_once_with("proj-testproj")
    mock_start_claude.assert_called_once_with(
        "/home/proj-testproj/app", "proj-testproj:lead",
        linux_user=None,
    )


@patch("delta.app.start_claude_code")
@patch("delta.app.create_tmux_session")
@patch("delta.app.is_claude_running")
@patch("delta.app.is_session_alive")
def test_restore_skips_already_running(
    mock_session_alive, mock_claude_running,
    mock_create_tmux, mock_start_claude,
):
    """When both session and Claude are alive, restore does nothing."""
    from delta.app import _restore_active_projects, registry

    info = _make_project_info("testproj")
    with patch.object(registry, "list_projects", return_value=["testproj"]), \
         patch.object(registry, "get", return_value=info):
        mock_session_alive.return_value = True
        mock_claude_running.return_value = True

        count = _restore_active_projects()

    assert count == 0
    mock_create_tmux.assert_not_called()
    mock_start_claude.assert_not_called()


@patch("delta.app.start_claude_code")
@patch("delta.app.create_tmux_session")
@patch("delta.app.is_claude_running")
@patch("delta.app.is_session_alive")
def test_restore_skips_hibernated(
    mock_session_alive, mock_claude_running,
    mock_create_tmux, mock_start_claude,
):
    """Hibernated projects should not be restored."""
    from delta.app import _restore_active_projects, registry

    info = _make_project_info("sleepy", status="hibernated")
    with patch.object(registry, "list_projects", return_value=["sleepy"]), \
         patch.object(registry, "get", return_value=info):
        count = _restore_active_projects()

    assert count == 0
    mock_create_tmux.assert_not_called()
    mock_start_claude.assert_not_called()


@patch("delta.app.start_claude_code")
@patch("delta.app.create_tmux_session")
@patch("delta.app.is_claude_running")
@patch("delta.app.is_session_alive")
def test_restore_session_alive_but_claude_dead(
    mock_session_alive, mock_claude_running,
    mock_create_tmux, mock_start_claude,
):
    """When session exists but Claude Code died, restart Claude only."""
    from delta.app import _restore_active_projects, registry

    info = _make_project_info("testproj")
    with patch.object(registry, "list_projects", return_value=["testproj"]), \
         patch.object(registry, "get", return_value=info):
        mock_session_alive.return_value = True
        # First call in the initial check: not running. Second call after
        # create_tmux_session is skipped: still not running.
        mock_claude_running.return_value = False
        mock_start_claude.return_value = True

        count = _restore_active_projects()

    assert count == 1
    mock_create_tmux.assert_not_called()
    mock_start_claude.assert_called_once_with(
        "/home/proj-testproj/app", "proj-testproj:lead",
        linux_user=None,
    )


@patch("delta.app.start_claude_code")
@patch("delta.app.create_tmux_session")
@patch("delta.app.is_claude_running")
@patch("delta.app.is_session_alive")
def test_restore_with_linux_user(
    mock_session_alive, mock_claude_running,
    mock_create_tmux, mock_start_claude,
):
    """Linux user should be passed through to start_claude_code."""
    from delta.app import _restore_active_projects, registry

    info = _make_project_info("testproj", linux_user="proj-testproj")
    with patch.object(registry, "list_projects", return_value=["testproj"]), \
         patch.object(registry, "get", return_value=info):
        mock_session_alive.return_value = False
        mock_claude_running.return_value = False
        mock_create_tmux.return_value = True
        mock_start_claude.return_value = True

        count = _restore_active_projects()

    assert count == 1
    mock_start_claude.assert_called_once_with(
        "/home/proj-testproj/app", "proj-testproj:lead",
        linux_user="proj-testproj",
    )


@patch("delta.app.start_claude_code")
@patch("delta.app.create_tmux_session")
@patch("delta.app.is_claude_running")
@patch("delta.app.is_session_alive")
def test_restore_multiple_projects(
    mock_session_alive, mock_claude_running,
    mock_create_tmux, mock_start_claude,
):
    """Multiple active projects with dead sessions should all be restored."""
    from delta.app import _restore_active_projects, registry

    proj_a = _make_project_info("alpha")
    proj_b = _make_project_info("beta")
    hibernated = _make_project_info("sleepy", status="hibernated")

    def get_project(name):
        return {"alpha": proj_a, "beta": proj_b, "sleepy": hibernated}.get(name)

    with patch.object(registry, "list_projects", return_value=["alpha", "beta", "sleepy"]), \
         patch.object(registry, "get", side_effect=get_project):
        mock_session_alive.return_value = False
        mock_claude_running.return_value = False
        mock_create_tmux.return_value = True
        mock_start_claude.return_value = True

        count = _restore_active_projects()

    assert count == 2
    assert mock_create_tmux.call_count == 2
    assert mock_start_claude.call_count == 2
