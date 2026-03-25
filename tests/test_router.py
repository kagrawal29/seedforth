"""Tests for delta.router."""

import pytest
from delta.registry import ProjectInfo, Registry
from delta.router import Router


@pytest.fixture
def registry(tmp_path):
    return Registry(tmp_path / "test-registry.json")


@pytest.fixture
def router(registry):
    return Router(registry)


@pytest.fixture
def audioworld():
    return ProjectInfo(
        name="audioworld",
        project_dir="/home/proj-audioworld/audioworld",
        data_dir="/home/proj-audioworld/audioworld/delta-config",
        tmux_session="proj-audioworld",
        tmux_lead_pane="proj-audioworld:lead",
        linux_user="proj-audioworld",
        discord_channel_id="CH_AUDIO",
        owner_discord_id="USER_A",
    )


@pytest.fixture
def projectb():
    return ProjectInfo(
        name="projectb",
        project_dir="/home/proj-projectb/projectb",
        data_dir="/home/proj-projectb/projectb/delta-config",
        tmux_session="proj-projectb",
        tmux_lead_pane="proj-projectb:lead",
        linux_user="proj-projectb",
        discord_channel_id="CH_PROJB",
        owner_discord_id="USER_A",
    )


def test_resolve_channel_found(router, registry, audioworld):
    registry.add(audioworld)
    result = router.resolve_channel("CH_AUDIO")
    assert result == "audioworld"


def test_resolve_channel_not_found(router):
    result = router.resolve_channel("CH_UNKNOWN")
    assert result is None


def test_resolve_dm_single_project(router, registry, audioworld):
    registry.add(audioworld)
    result = router.resolve_dm("USER_A")
    assert result == "audioworld"


def test_resolve_dm_no_projects(router):
    result = router.resolve_dm("USER_NOBODY")
    assert result is None


def test_resolve_dm_multiple_projects(router, registry, audioworld, projectb):
    registry.add(audioworld)
    registry.add(projectb)
    result = router.resolve_dm("USER_A")
    assert isinstance(result, list)
    assert set(result) == {"audioworld", "projectb"}


def test_resolve_dm_different_owners(router, registry, audioworld, projectb):
    # Change projectb to a different owner
    projectb.owner_discord_id = "USER_B"
    registry.add(audioworld)
    registry.add(projectb)

    result_a = router.resolve_dm("USER_A")
    assert result_a == "audioworld"

    result_b = router.resolve_dm("USER_B")
    assert result_b == "projectb"
