"""Tests for delta.lifecycle."""

from unittest.mock import patch, MagicMock, call
import subprocess
import pytest
from delta.lifecycle import (
    is_session_alive, is_claude_running, start_claude_code, stop_claude_code,
    create_tmux_session, kill_tmux_session, get_project_health,
)


def _mock_run(returncode=0, stdout="", stderr=""):
    return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)


@patch("delta.lifecycle._run")
def test_is_session_alive_true(mock_run):
    mock_run.return_value = _mock_run(0)
    assert is_session_alive("myproject") is True


@patch("delta.lifecycle._run")
def test_is_session_alive_false(mock_run):
    mock_run.return_value = _mock_run(1)
    assert is_session_alive("myproject") is False


@patch("delta.lifecycle._run")
def test_is_claude_running_true(mock_run):
    mock_run.side_effect = [
        _mock_run(0),            # has-session
        _mock_run(0, "12345"),   # list-panes pane_pid
        _mock_run(0, "67890"),   # pgrep -P (child PIDs)
        _mock_run(0, "claude --dangerously-skip-permissions"),  # ps -p <pid> -o command=
    ]
    assert is_claude_running("myproject:lead") is True


@patch("delta.lifecycle._run")
def test_is_claude_running_no_session(mock_run):
    mock_run.return_value = _mock_run(1)
    assert is_claude_running("myproject:lead") is False


@patch("delta.lifecycle._run")
def test_is_claude_running_no_claude_process(mock_run):
    mock_run.side_effect = [
        _mock_run(0),            # has-session
        _mock_run(0, "12345"),   # list-panes pane_pid
        _mock_run(1),            # pgrep -- no claude process
    ]
    assert is_claude_running("myproject:lead") is False


@patch("delta.lifecycle.time.sleep")
@patch("delta.lifecycle._run")
def test_start_claude_code_no_user(mock_run, mock_sleep):
    mock_run.side_effect = [
        _mock_run(1),   # has-session (for is_claude_running) -> not alive = not running
        _mock_run(0),   # has-session (for start check)
        _mock_run(0),   # send-keys command
        _mock_run(0),   # send-keys Enter
    ]
    result = start_claude_code("/home/proj-test/app", "proj-test:lead")
    assert result is True
    # The command sent should be cd + claude (no sudo)
    send_keys_call = mock_run.call_args_list[2]
    cmd_sent = send_keys_call[0][0]
    assert "-l" in cmd_sent
    assert "sudo" not in " ".join(cmd_sent)


@patch("delta.lifecycle.time.sleep")
@patch("delta.lifecycle._run")
def test_start_claude_code_with_user(mock_run, mock_sleep):
    mock_run.side_effect = [
        _mock_run(1),   # has-session (for is_claude_running)
        _mock_run(0),   # has-session (for start check)
        _mock_run(0),   # send-keys command
        _mock_run(0),   # send-keys Enter
    ]
    result = start_claude_code("/home/proj-test/app", "proj-test:lead", linux_user="proj-test")
    assert result is True
    send_keys_call = mock_run.call_args_list[2]
    cmd_str = " ".join(send_keys_call[0][0])
    assert "sudo -u proj-test" in cmd_str or "proj-test" in cmd_str


@patch("delta.lifecycle.time.sleep")
@patch("delta.lifecycle.is_claude_running")
@patch("delta.lifecycle._run")
def test_stop_claude_code_graceful(mock_run, mock_is_running, mock_sleep):
    # First call: running (triggers stop), then: not running (stopped)
    mock_is_running.side_effect = [True, False]
    mock_run.return_value = _mock_run(0)

    result = stop_claude_code("proj-test:lead", grace=1)
    assert result is True


@patch("delta.lifecycle.time.sleep")
@patch("delta.lifecycle.is_claude_running")
@patch("delta.lifecycle._run")
def test_stop_claude_code_force_kill(mock_run, mock_is_running, mock_sleep):
    # Running through entire grace period, then force killed
    mock_is_running.side_effect = [True, True, False]
    mock_run.return_value = _mock_run(0, stdout="12345")

    result = stop_claude_code("proj-test:lead", grace=1)
    assert result is True


@patch("delta.lifecycle._run")
def test_create_tmux_session_new(mock_run):
    mock_run.side_effect = [
        _mock_run(1),   # has-session (doesn't exist)
        _mock_run(0),   # new-session
    ]
    assert create_tmux_session("proj-test") is True


@patch("delta.lifecycle._run")
def test_create_tmux_session_exists(mock_run):
    mock_run.return_value = _mock_run(0)  # has-session (exists)
    assert create_tmux_session("proj-test") is True
    assert mock_run.call_count == 1  # Only checked, didn't create


@patch("delta.lifecycle._run")
def test_kill_tmux_session_success(mock_run):
    mock_run.side_effect = [
        _mock_run(0),   # has-session (exists)
        _mock_run(0),   # kill-session
    ]
    assert kill_tmux_session("proj-test") is True


@patch("delta.lifecycle._run")
def test_kill_tmux_session_already_gone(mock_run):
    mock_run.return_value = _mock_run(1)  # has-session (doesn't exist)
    assert kill_tmux_session("proj-test") is True


@patch("delta.lifecycle.is_claude_running")
@patch("delta.lifecycle.is_session_alive")
def test_get_project_health(mock_alive, mock_running):
    mock_alive.return_value = True
    mock_running.return_value = True
    health = get_project_health("proj-test:lead")
    assert health == {"session_alive": True, "claude_running": True}

    mock_alive.return_value = True
    mock_running.return_value = False
    health = get_project_health("proj-test:lead")
    assert health == {"session_alive": True, "claude_running": False}
