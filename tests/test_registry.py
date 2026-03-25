"""Tests for delta.registry."""

import json
import pytest
from delta.registry import ProjectInfo, Registry


@pytest.fixture
def registry_file(tmp_path):
    return tmp_path / "test-registry.json"


@pytest.fixture
def registry(registry_file):
    return Registry(registry_file)


@pytest.fixture
def sample_project():
    return ProjectInfo(
        name="audioworld",
        project_dir="/home/proj-audioworld/audioworld",
        data_dir="/home/proj-audioworld/audioworld/delta-config",
        tmux_session="proj-audioworld",
        tmux_lead_pane="proj-audioworld:lead",
        nudge_prefix="delta-config/inbox",
        github_repo="kagrawal29/audioworld",
        linux_user="proj-audioworld",
        discord_channel_id="1234567890",
        owner_discord_id="9876543210",
    )


def test_add_and_get(registry, sample_project):
    registry.add(sample_project)
    got = registry.get("audioworld")
    assert got is not None
    assert got.name == "audioworld"
    assert got.project_dir == "/home/proj-audioworld/audioworld"
    assert got.github_repo == "kagrawal29/audioworld"
    assert got.linux_user == "proj-audioworld"
    assert got.discord_channel_id == "1234567890"
    assert got.owner_discord_id == "9876543210"


def test_list_projects(registry, sample_project):
    assert registry.list_projects() == []
    registry.add(sample_project)
    assert registry.list_projects() == ["audioworld"]


def test_remove(registry, sample_project):
    registry.add(sample_project)
    assert registry.remove("audioworld") is True
    assert registry.get("audioworld") is None
    assert registry.remove("nonexistent") is False


def test_persistence(registry_file, sample_project):
    r1 = Registry(registry_file)
    r1.add(sample_project)

    r2 = Registry(registry_file)
    got = r2.get("audioworld")
    assert got is not None
    assert got.name == "audioworld"
    assert got.linux_user == "proj-audioworld"
    assert got.discord_channel_id == "1234567890"


def test_find_by_discord_channel(registry, sample_project):
    registry.add(sample_project)
    found = registry.find_by_discord_channel("1234567890")
    assert found is not None
    assert found.name == "audioworld"
    assert registry.find_by_discord_channel("UNKNOWN") is None


def test_find_by_owner(registry, sample_project):
    registry.add(sample_project)
    projects = registry.find_by_owner("9876543210")
    assert len(projects) == 1
    assert projects[0].name == "audioworld"


def test_find_by_owner_multiple(registry):
    p1 = ProjectInfo(
        name="project-a", project_dir="/home/proj-a", data_dir="/home/proj-a/delta-config",
        tmux_session="proj-a", tmux_lead_pane="proj-a:lead",
        owner_discord_id="USER1",
    )
    p2 = ProjectInfo(
        name="project-b", project_dir="/home/proj-b", data_dir="/home/proj-b/delta-config",
        tmux_session="proj-b", tmux_lead_pane="proj-b:lead",
        owner_discord_id="USER1",
    )
    registry.add(p1)
    registry.add(p2)
    projects = registry.find_by_owner("USER1")
    assert len(projects) == 2
    names = {p.name for p in projects}
    assert names == {"project-a", "project-b"}


def test_find_by_owner_empty(registry):
    projects = registry.find_by_owner("NOBODY")
    assert projects == []


def test_count(registry, sample_project):
    assert registry.count == 0
    registry.add(sample_project)
    assert registry.count == 1


def test_project_info_roundtrip():
    info = ProjectInfo(
        name="test",
        project_dir="/tmp/test",
        data_dir="/tmp/test/config",
        tmux_session="test",
        tmux_lead_pane="test:lead",
    )
    d = info.to_dict()
    restored = ProjectInfo.from_dict(d)
    assert restored.name == "test"
    assert restored.linux_user == ""
    assert restored.discord_channel_id == ""
    assert restored.nudge_prefix == "/tmp/test/config/inbox"
    assert restored.created_at != ""  # auto-set


def test_empty_file_loads_ok(tmp_path):
    f = tmp_path / "empty.json"
    f.write_text("{}")
    r = Registry(f)
    assert r.list_projects() == []


def test_corrupt_file_loads_ok(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("not json at all")
    r = Registry(f)
    assert r.list_projects() == []
