"""Tests for delta.agent_lifecycle."""

from unittest.mock import patch, MagicMock, call
import requests
import pytest
from delta.agent_lifecycle import (
    is_agent_running,
    start_agent_serve,
    stop_agent_serve,
    get_agent_health,
    nudge_agent,
)


def _mock_response(status_code=200, json_data=None, elapsed_s=0.0):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.elapsed.total_seconds.return_value = elapsed_s
    return resp


@patch("delta.agent_lifecycle.requests.get")
def test_is_agent_running_success(mock_get):
    mock_get.return_value = _mock_response(200, {"healthy": True})
    assert is_agent_running(7700) is True
    mock_get.assert_called_once_with("http://127.0.0.1:7700/global/health", timeout=5)


@patch("delta.agent_lifecycle.requests.get")
def test_is_agent_running_not_healthy(mock_get):
    mock_get.return_value = _mock_response(200, {"healthy": False})
    assert is_agent_running(7700) is False


@patch("delta.agent_lifecycle.requests.get")
def test_is_agent_running_connection_refused(mock_get):
    mock_get.side_effect = requests.ConnectionError("Connection refused")
    assert is_agent_running(7700) is False


@patch("delta.agent_lifecycle._run")
def test_stop_agent_serve_keep_config(mock_run):
    stop_agent_serve("myproject", keep_config=True)
    mock_run.assert_called_once_with(["supervisorctl", "stop", "proj-myproject"])


@patch("delta.agent_lifecycle.os.unlink")
@patch("delta.agent_lifecycle._run")
def test_stop_agent_serve_remove_config(mock_run, mock_unlink):
    stop_agent_serve("myproject", keep_config=False)
    assert mock_run.call_args_list == [
        call(["supervisorctl", "stop", "proj-myproject"]),
        call(["supervisorctl", "update"]),
    ]
    mock_unlink.assert_called_once_with("/etc/supervisor/conf.d/proj-myproject.conf")


@patch("delta.agent_lifecycle._wait_for_healthy")
@patch("delta.agent_lifecycle._run")
@patch("delta.agent_lifecycle._write_supervisor_config")
def test_start_agent_serve_success(mock_write_config, mock_run, mock_wait_healthy):
    mock_wait_healthy.return_value = True
    result = start_agent_serve("myproject", 7700, "/home/proj-myproject/myproject")
    assert result is True
    mock_write_config.assert_called_once_with(
        "myproject", 7700, "/home/proj-myproject/myproject", "proj-myproject", {}
    )
    assert mock_run.call_args_list == [
        call(["supervisorctl", "start", "proj-myproject"], check=True),
    ]
    mock_wait_healthy.assert_called_once_with(7700)


@patch("delta.agent_lifecycle._wait_for_healthy")
@patch("delta.agent_lifecycle._run")
@patch("delta.agent_lifecycle._write_supervisor_config")
def test_start_agent_serve_timeout(mock_write_config, mock_run, mock_wait_healthy):
    mock_wait_healthy.return_value = False
    result = start_agent_serve("myproject", 7700, "/home/proj-myproject/myproject")
    assert result is False


@patch("delta.agent_lifecycle.requests.get")
def test_get_agent_health(mock_get):
    mock_get.return_value = _mock_response(200, elapsed_s=0.042)
    health = get_agent_health(7700)
    assert health == {"agent_running": True, "response_ms": 42.0}


@patch("delta.agent_lifecycle.requests.get")
def test_get_agent_health_down(mock_get):
    mock_get.side_effect = requests.ConnectionError()
    health = get_agent_health(7700)
    assert health == {"agent_running": False, "response_ms": 0}


@patch("delta.agent_lifecycle.requests.get")
@patch("builtins.open")
def test_nudge_agent(mock_open, mock_get):
    nudge_agent("myproject", 7700)
    mock_open.assert_called_once_with(
        "/home/proj-myproject/myproject/delta-config/.nudge", "a"
    )
    mock_get.assert_called_once_with("http://127.0.0.1:7700/global/health", timeout=5)


@patch("delta.agent_lifecycle.requests.get")
@patch("builtins.open")
def test_nudge_agent_http_error_graceful(mock_open, mock_get):
    mock_get.side_effect = requests.ConnectionError()
    nudge_agent("myproject", 7700)
    mock_open.assert_called_once()
    mock_get.assert_called_once()
