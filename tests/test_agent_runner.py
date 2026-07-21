"""Tests for delta.agent_runner."""

from delta.agent_runner import get_runner, OpencodeServeRunner, ClaudeCodeRunner
from delta.registry import ProjectInfo


def _make_project(**kwargs):
    defaults = {
        "name": "test",
        "project_dir": "/home/proj-test/test",
        "data_dir": "/home/proj-test/test/delta-config",
        "tmux_session": "proj-test",
        "tmux_lead_pane": "proj-test:lead",
    }
    defaults.update(kwargs)
    return ProjectInfo(**defaults)


def test_get_runner_opencode():
    project = _make_project(runtime="opencode")
    runner = get_runner(project)
    assert isinstance(runner, OpencodeServeRunner)


def test_get_runner_claude():
    project = _make_project(runtime="claude")
    runner = get_runner(project)
    assert isinstance(runner, ClaudeCodeRunner)


def test_get_runner_default():
    project = _make_project()
    runner = get_runner(project)
    assert isinstance(runner, ClaudeCodeRunner)
