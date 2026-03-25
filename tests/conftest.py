"""Shared fixtures for delta tests."""

import os
import pytest
from pathlib import Path


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
