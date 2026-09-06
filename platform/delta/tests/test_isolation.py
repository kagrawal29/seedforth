"""Tests for delta.isolation."""

from unittest.mock import patch, MagicMock
import subprocess
import pytest
from delta.isolation import (
    linux_username, create_user, delete_user, user_exists, run_as_user,
)


def test_linux_username():
    assert linux_username("myapp") == "proj-myapp"
    assert linux_username("test-app") == "proj-test-app"


@patch("delta.isolation.subprocess.run")
def test_create_user_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    result = create_user("myapp")
    assert result == "proj-myapp"

    # User creation also provisions opencode's shared config and data dirs.
    assert mock_run.call_count == 5
    useradd_call = mock_run.call_args_list[0]
    assert "useradd" in useradd_call[0][0]
    assert "-m" in useradd_call[0][0]
    assert "/home/proj-myapp" in useradd_call[0][0]

    chmod_call = mock_run.call_args_list[2]
    assert "chmod" in chmod_call[0][0]
    assert "2770" in chmod_call[0][0]


@patch("delta.isolation.subprocess.run")
def test_create_user_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stderr="user already exists")
    with pytest.raises(RuntimeError, match="useradd failed"):
        create_user("myapp")


@patch("delta.isolation.subprocess.run")
def test_delete_user_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    assert delete_user("proj-myapp") is True
    mock_run.assert_called_once()
    assert "userdel" in mock_run.call_args[0][0]
    assert "-r" in mock_run.call_args[0][0]


@patch("delta.isolation.subprocess.run")
def test_delete_user_not_found(mock_run):
    mock_run.return_value = MagicMock(returncode=6, stderr="user 'proj-myapp' does not exist")
    assert delete_user("proj-myapp") is False


@patch("delta.isolation.subprocess.run")
def test_user_exists_true(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    assert user_exists("proj-myapp") is True
    assert "id" in mock_run.call_args[0][0]


@patch("delta.isolation.subprocess.run")
def test_user_exists_false(mock_run):
    mock_run.return_value = MagicMock(returncode=1)
    assert user_exists("proj-myapp") is False


@patch("delta.isolation.subprocess.run")
def test_run_as_user_basic(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")
    result = run_as_user("proj-myapp", "echo hello")
    assert result.returncode == 0
    cmd = mock_run.call_args[0][0]
    assert cmd == ["sudo", "-u", "proj-myapp", "bash", "-c", "echo hello"]


@patch("delta.isolation.subprocess.run")
def test_run_as_user_with_cwd(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    run_as_user("proj-myapp", "ls", cwd="/home/proj-myapp")
    kwargs = mock_run.call_args[1]
    assert kwargs["cwd"] == "/home/proj-myapp"
