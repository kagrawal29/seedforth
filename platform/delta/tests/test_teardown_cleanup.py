"""Tests for teardown local directory cleanup in LOCAL_MODE."""

import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
import pytest_asyncio

from delta.registry import Registry, ProjectInfo


@pytest.fixture
def tmp_registry(tmp_path):
    reg = Registry(str(tmp_path / "registry.json"))
    return reg


@pytest.fixture
def local_projects_dir(tmp_path):
    d = tmp_path / "delta-projects"
    d.mkdir()
    return d


def _make_project(local_projects_dir, name="test-proj"):
    """Create a fake project directory under the sandbox."""
    project_dir = local_projects_dir / name
    project_dir.mkdir(parents=True)
    (project_dir / "CLAUDE.md").write_text("test")
    (project_dir / "delta-config").mkdir()
    return project_dir


@pytest.mark.asyncio
async def test_teardown_deletes_local_dir(tmp_registry, local_projects_dir):
    """Teardown in LOCAL_MODE should delete the project directory."""
    project_dir = _make_project(local_projects_dir)
    assert project_dir.exists()

    info = ProjectInfo(
        name="test-proj",
        project_dir=str(project_dir),
        data_dir=str(project_dir / "delta-config"),
        tmux_session="test-proj",
        tmux_lead_pane="test-proj:lead",
        owner_discord_id="123",
        discord_channel_id="456",
    )
    tmp_registry.add(info)

    with patch("delta.provisioner.LOCAL_MODE", True), \
         patch("delta.provisioner.LOCAL_PROJECTS_DIR", str(local_projects_dir)), \
         patch("delta.provisioner.stop_agent_serve"):

        from delta.provisioner import teardown
        result = await teardown("test-proj", tmp_registry, None, None)

    assert result is True
    assert not project_dir.exists()


@pytest.mark.asyncio
async def test_teardown_refuses_outside_sandbox(tmp_registry, tmp_path, local_projects_dir):
    """Teardown should refuse to delete dirs outside LOCAL_PROJECTS_DIR."""
    # Create a dir outside the sandbox
    outside_dir = tmp_path / "outside-project"
    outside_dir.mkdir()
    (outside_dir / "important.txt").write_text("don't delete me")

    info = ProjectInfo(
        name="rogue-proj",
        project_dir=str(outside_dir),
        data_dir=str(outside_dir / "delta-config"),
        tmux_session="rogue-proj",
        tmux_lead_pane="rogue-proj:lead",
        owner_discord_id="123",
        discord_channel_id="456",
    )
    tmp_registry.add(info)

    with patch("delta.provisioner.LOCAL_MODE", True), \
         patch("delta.provisioner.LOCAL_PROJECTS_DIR", str(local_projects_dir)), \
         patch("delta.provisioner.stop_agent_serve"):

        from delta.provisioner import teardown
        result = await teardown("rogue-proj", tmp_registry, None, None)

    assert result is True
    # Dir should still exist -- we refused to delete it
    assert outside_dir.exists()
    assert (outside_dir / "important.txt").exists()


@pytest.mark.asyncio
async def test_teardown_refuses_sandbox_root(tmp_registry, local_projects_dir):
    """Teardown should refuse to delete the sandbox root itself."""
    info = ProjectInfo(
        name="root-proj",
        project_dir=str(local_projects_dir),  # The sandbox root itself
        data_dir=str(local_projects_dir / "delta-config"),
        tmux_session="root-proj",
        tmux_lead_pane="root-proj:lead",
        owner_discord_id="123",
        discord_channel_id="456",
    )
    tmp_registry.add(info)

    with patch("delta.provisioner.LOCAL_MODE", True), \
         patch("delta.provisioner.LOCAL_PROJECTS_DIR", str(local_projects_dir)), \
         patch("delta.provisioner.stop_agent_serve"):

        from delta.provisioner import teardown
        result = await teardown("root-proj", tmp_registry, None, None)

    assert result is True
    # Sandbox root should still exist
    assert local_projects_dir.exists()


@pytest.mark.asyncio
async def test_teardown_skips_when_no_project_dir(tmp_registry, local_projects_dir):
    """Teardown with empty project_dir should not crash."""
    info = ProjectInfo(
        name="no-dir-proj",
        project_dir="",
        data_dir="",
        tmux_session="no-dir-proj",
        tmux_lead_pane="no-dir-proj:lead",
        owner_discord_id="123",
        discord_channel_id="456",
    )
    tmp_registry.add(info)

    with patch("delta.provisioner.LOCAL_MODE", True), \
         patch("delta.provisioner.LOCAL_PROJECTS_DIR", str(local_projects_dir)), \
         patch("delta.provisioner.stop_agent_serve"):

        from delta.provisioner import teardown
        result = await teardown("no-dir-proj", tmp_registry, None, None)

    assert result is True
