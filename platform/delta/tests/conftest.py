"""Shared fixtures for delta tests."""

import os
import importlib.util
import pytest
from pathlib import Path


# The imported test tree contains one pre-opencode lifecycle test module whose
# implementation (`delta.lifecycle`) no longer exists. Keep it visible in the
# repository as migration evidence, but do not let it break collection of the
# active suite. Optional integration modules are collected whenever their
# declared dependencies are installed (requirements.txt covers CI/server).
collect_ignore = [
    # Pre-opencode lifecycle tests retained as migration evidence.
    "test_lifecycle.py",
    # These suites assert the retired direct-DM-to-project and tmux/Claude
    # restore paths. Current DMs enter SuperAgent; opencode is supervisor-
    # managed. Replacement coverage belongs in the active hub/runtime tests.
    "test_dm_persistent_routing.py",
    "test_restore_on_startup.py",
]
if importlib.util.find_spec("discord") is None:
    collect_ignore.extend(["test_last_fired.py"])
if importlib.util.find_spec("pytest_asyncio") is None:
    collect_ignore.append("test_teardown_cleanup.py")


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary data directory with inbox/outbox/logs."""
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    logs = tmp_path / "logs"
    inbox.mkdir()
    outbox.mkdir()
    logs.mkdir()
    return tmp_path
