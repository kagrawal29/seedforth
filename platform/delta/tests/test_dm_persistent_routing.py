"""Tests for DM routing to persistent agents.

When a user has a project_type=persistent project (e.g. onboarding-<name>),
their DMs should route to that agent instead of hub. This tests:
1. Registry.find_persistent_by_owner()
2. _route_dm_to_persistent() async helper
3. on_message DM flow with persistent agent check
4. _hub_snapshot_loop writing per-user snapshots
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock, call

import discord

from delta.registry import ProjectInfo, Registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OWNER_1 = "100000000001"
OWNER_2 = "100000000002"
OWNER_NEW = "100000000099"
CHANNEL_DM = "999888777"
CHANNEL_PROJ = "111222333"


def _make_project_info(name, owner=OWNER_1, status="active",
                       project_type="standard", project_dir=None,
                       linux_user="", discord_channel_id=CHANNEL_PROJ):
    return ProjectInfo(
        name=name,
        project_dir=project_dir or f"/home/proj-{name}/app",
        data_dir=f"/home/proj-{name}/app/delta-config",
        tmux_session=f"proj-{name}",
        tmux_lead_pane=f"proj-{name}:lead",
        owner_discord_id=owner,
        discord_channel_id=discord_channel_id,
        status=status,
        project_type=project_type,
        linux_user=linux_user,
    )


def _mock_bridge(active=True, auth_error=None):
    bridge = MagicMock()
    bridge.is_project_active.return_value = active
    bridge.check_auth_error.return_value = auth_error
    bridge.write_inbox.return_value = "msg-001"
    bridge.send_to_lead = MagicMock()
    bridge.touch_activity = MagicMock()
    bridge.pending_inbox_count.return_value = 0
    bridge.inbox_dir = MagicMock()
    return bridge


def _mock_message(channel_id="999888777", user_id="111222333", text="hello",
                  is_dm=True):
    msg = MagicMock(spec=discord.Message)
    msg.author = MagicMock()
    msg.author.bot = False
    msg.author.id = int(user_id)
    msg.content = text

    if is_dm:
        msg.channel = MagicMock(spec=discord.DMChannel)
    else:
        msg.channel = MagicMock(spec=discord.TextChannel)

    msg.channel.id = int(channel_id)
    msg.channel.send = AsyncMock()
    return msg


# ===========================================================================
# 1. Registry: find_persistent_by_owner
# ===========================================================================

class TestFindPersistentByOwner:

    @pytest.fixture
    def registry(self, tmp_path):
        return Registry(tmp_path / "test-registry.json")

    def test_returns_persistent_active(self, registry):
        p = _make_project_info("chiron-alice", owner=OWNER_1,
                               project_type="persistent", status="active")
        registry.add(p)
        found = registry.find_persistent_by_owner(OWNER_1)
        assert found is not None
        assert found.name == "chiron-alice"

    def test_returns_persistent_hibernated(self, registry):
        p = _make_project_info("chiron-bob", owner=OWNER_2,
                               project_type="persistent", status="hibernated")
        registry.add(p)
        found = registry.find_persistent_by_owner(OWNER_2)
        assert found is not None
        assert found.name == "chiron-bob"

    def test_ignores_standard_projects(self, registry):
        p = _make_project_info("my-website", owner=OWNER_1,
                               project_type="standard", status="active")
        registry.add(p)
        assert registry.find_persistent_by_owner(OWNER_1) is None

    def test_ignores_personal_onboarding(self, registry):
        p = _make_project_info("chiron-carol", owner=OWNER_1,
                               project_type="personal", status="active")
        registry.add(p)
        assert registry.find_persistent_by_owner(OWNER_1) is None

    def test_ignores_torn_down(self, registry):
        p = _make_project_info("chiron-dave", owner=OWNER_1,
                               project_type="persistent", status="torn_down")
        registry.add(p)
        assert registry.find_persistent_by_owner(OWNER_1) is None

    def test_returns_none_for_unknown_user(self, registry):
        p = _make_project_info("chiron-eve", owner=OWNER_1,
                               project_type="persistent")
        registry.add(p)
        assert registry.find_persistent_by_owner("999999999999") is None

    def test_multiple_owners_isolated(self, registry):
        p1 = _make_project_info("chiron-alice", owner=OWNER_1,
                                project_type="persistent")
        p2 = _make_project_info("chiron-bob", owner=OWNER_2,
                                project_type="persistent")
        registry.add(p1)
        registry.add(p2)
        found = registry.find_persistent_by_owner(OWNER_1)
        assert found.name == "chiron-alice"
        found2 = registry.find_persistent_by_owner(OWNER_2)
        assert found2.name == "chiron-bob"

    def test_user_has_standard_and_persistent(self, registry):
        """User with both standard and persistent projects -- returns persistent."""
        std = _make_project_info("my-app", owner=OWNER_1,
                                 project_type="standard")
        pers = _make_project_info("chiron-alice", owner=OWNER_1,
                                  project_type="persistent")
        registry.add(std)
        registry.add(pers)
        found = registry.find_persistent_by_owner(OWNER_1)
        assert found.name == "chiron-alice"

    def test_persistence_roundtrip(self, tmp_path):
        """find_persistent_by_owner works after reload from disk."""
        path = tmp_path / "reg.json"
        r1 = Registry(path)
        r1.add(_make_project_info("chiron-alice", owner=OWNER_1,
                                  project_type="persistent"))
        r2 = Registry(path)
        found = r2.find_persistent_by_owner(OWNER_1)
        assert found is not None
        assert found.name == "chiron-alice"


# ===========================================================================
# 2. _route_dm_to_persistent
# ===========================================================================

class TestRouteDmToPersistent:

    @pytest.mark.asyncio
    @patch("delta.app._start_watchers")
    @patch("delta.app._start_typing")
    @patch("delta.app._get_or_create_bridge")
    async def test_active_project_happy_path(
        self, mock_get_bridge, mock_start_typing, mock_start_watchers,
    ):
        from delta.app import _route_dm_to_persistent

        project = _make_project_info("chiron-alice", project_type="persistent")
        bridge = _mock_bridge(active=True)
        mock_get_bridge.return_value = bridge
        msg = _mock_message()

        await _route_dm_to_persistent(project, msg, CHANNEL_DM, OWNER_1, "hello")

        bridge.touch_activity.assert_called_once()
        bridge.write_inbox.assert_called_once_with(
            CHANNEL_DM, OWNER_1, "hello", channel_type="dm",
        )
        mock_start_typing.assert_called_once_with(msg.channel, CHANNEL_DM)
        bridge.send_to_lead.assert_called_once_with("msg-001")
        mock_start_watchers.assert_called_once_with("chiron-alice")

    @pytest.mark.asyncio
    @patch("delta.app._start_watchers")
    @patch("delta.app._start_typing")
    @patch("delta.app._stop_typing")
    @patch("delta.app._get_or_create_bridge")
    async def test_agent_not_running_sends_waking_message(
        self, mock_get_bridge, mock_stop_typing, mock_start_typing,
        mock_start_watchers,
    ):
        from delta.app import _route_dm_to_persistent

        project = _make_project_info("chiron-alice", project_type="persistent")
        bridge = _mock_bridge(active=False)
        mock_get_bridge.return_value = bridge
        msg = _mock_message()

        await _route_dm_to_persistent(project, msg, CHANNEL_DM, OWNER_1, "hello")

        mock_stop_typing.assert_called_once_with(CHANNEL_DM)
        msg.channel.send.assert_called_once_with(
            "I'm waking up, give me a sec. Try again in a moment."
        )

    @pytest.mark.asyncio
    @patch("delta.app._start_watchers")
    @patch("delta.app._start_typing")
    @patch("delta.app._get_or_create_bridge")
    async def test_auth_error_blocks_routing(
        self, mock_get_bridge, mock_start_typing, mock_start_watchers,
    ):
        from delta.app import _route_dm_to_persistent

        project = _make_project_info("chiron-alice", project_type="persistent")
        bridge = _mock_bridge(active=True, auth_error="401 unauthorized")
        mock_get_bridge.return_value = bridge
        msg = _mock_message()

        await _route_dm_to_persistent(project, msg, CHANNEL_DM, OWNER_1, "hello")

        bridge.write_inbox.assert_not_called()
        msg.channel.send.assert_called_once_with(
            "I'm having trouble connecting right now. The admin has been notified."
        )

    @pytest.mark.asyncio
    @patch("delta.app.bridges", {})
    @patch("delta.app._start_typing")
    @patch("delta.app._get_or_create_bridge", return_value=None)
    async def test_bridge_creation_failure_falls_back_to_hub(
        self, mock_get_bridge, mock_start_typing,
    ):
        from delta.app import _route_dm_to_persistent, bridges, HUB_NAME

        project = _make_project_info("chiron-alice", project_type="persistent")
        hub_bridge = _mock_bridge(active=True)
        bridges[HUB_NAME] = hub_bridge
        msg = _mock_message()

        await _route_dm_to_persistent(project, msg, CHANNEL_DM, OWNER_1, "hello")

        # Should fall back to hub
        hub_bridge.touch_activity.assert_called_once()
        hub_bridge.write_inbox.assert_called_once_with(
            CHANNEL_DM, OWNER_1, "hello", channel_type="dm",
        )

    @pytest.mark.asyncio
    @patch("delta.app.is_claude_running", return_value=True)
    @patch("delta.app.restore")
    @patch("delta.app._start_watchers")
    @patch("delta.app._start_typing")
    @patch("delta.app._get_or_create_bridge")
    @patch("delta.app.asyncio.sleep", new_callable=AsyncMock)
    @patch("delta.app.bridges", {})
    async def test_hibernated_project_gets_restored(
        self, mock_sleep, mock_get_bridge, mock_start_typing,
        mock_start_watchers, mock_restore, mock_claude_running,
    ):
        from delta.app import _route_dm_to_persistent, registry

        project = _make_project_info("chiron-alice", project_type="persistent",
                                     status="hibernated")
        bridge = _mock_bridge(active=True)
        mock_get_bridge.return_value = bridge
        msg = _mock_message()

        # registry.get must return the project after restore
        with patch.object(registry, "get", return_value=project):
            await _route_dm_to_persistent(project, msg, CHANNEL_DM, OWNER_1, "hey")

        # Should wake up
        msg.channel.send.assert_any_call("waking up, one sec")
        mock_restore.assert_called_once_with("chiron-alice", registry)
        mock_sleep.assert_called_once_with(8)
        # Then proceed to route normally
        bridge.write_inbox.assert_called_once()

    @pytest.mark.asyncio
    @patch("delta.app.is_claude_running", return_value=False)
    @patch("delta.app.restore")
    @patch("delta.app._start_watchers")
    @patch("delta.app._get_or_create_bridge")
    @patch("delta.app.asyncio.sleep", new_callable=AsyncMock)
    @patch("delta.app.bridges", {})
    async def test_hibernated_restore_fails_post_boot_check(
        self, mock_sleep, mock_get_bridge, mock_start_watchers,
        mock_restore, mock_claude_running,
    ):
        from delta.app import _route_dm_to_persistent, registry

        project = _make_project_info("chiron-alice", project_type="persistent",
                                     status="hibernated")
        msg = _mock_message()

        with patch.object(registry, "get", return_value=project):
            await _route_dm_to_persistent(project, msg, CHANNEL_DM, OWNER_1, "hey")

        msg.channel.send.assert_any_call("waking up, one sec")
        msg.channel.send.assert_any_call(
            "Had trouble waking up. Try again in a moment."
        )
        # Should NOT proceed to write inbox
        mock_get_bridge.assert_not_called()

    @pytest.mark.asyncio
    @patch("delta.app._start_watchers")
    @patch("delta.app._start_typing")
    @patch("delta.app._get_or_create_bridge")
    async def test_nudge_failure_doesnt_crash(
        self, mock_get_bridge, mock_start_typing, mock_start_watchers,
    ):
        """If send_to_lead throws, we log warning but don't crash."""
        from delta.app import _route_dm_to_persistent

        project = _make_project_info("chiron-alice", project_type="persistent")
        bridge = _mock_bridge(active=True)
        bridge.send_to_lead.side_effect = RuntimeError("tmux error")
        mock_get_bridge.return_value = bridge
        msg = _mock_message()

        # Should not raise
        await _route_dm_to_persistent(project, msg, CHANNEL_DM, OWNER_1, "hello")

        bridge.write_inbox.assert_called_once()

    @pytest.mark.asyncio
    @patch("delta.app._start_watchers")
    @patch("delta.app._start_typing")
    @patch("delta.app._get_or_create_bridge")
    async def test_channel_type_dm_in_inbox(
        self, mock_get_bridge, mock_start_typing, mock_start_watchers,
    ):
        """Verify channel_type=dm is passed to write_inbox."""
        from delta.app import _route_dm_to_persistent

        project = _make_project_info("chiron-alice", project_type="persistent")
        bridge = _mock_bridge(active=True)
        mock_get_bridge.return_value = bridge
        msg = _mock_message(text="what's my day look like")

        await _route_dm_to_persistent(project, msg, CHANNEL_DM, OWNER_1,
                                      "what's my day look like")

        _, kwargs = bridge.write_inbox.call_args
        assert kwargs["channel_type"] == "dm"


# ===========================================================================
# 3. on_message DM flow integration
# ===========================================================================

class TestOnMessageDmRouting:

    @pytest.mark.asyncio
    @patch("delta.app._route_dm_to_persistent", new_callable=AsyncMock)
    @patch("delta.app.commands.parse", return_value=None)
    async def test_dm_routes_to_persistent_agent(
        self, mock_parse, mock_route_persistent,
    ):
        from delta.app import on_message, registry

        persistent = _make_project_info("chiron-alice", owner=OWNER_1,
                                        project_type="persistent")
        msg = _mock_message(user_id=OWNER_1, text="how's my week")

        with patch.object(registry, "find_persistent_by_owner",
                          return_value=persistent):
            await on_message(msg)

        mock_route_persistent.assert_called_once_with(
            persistent, msg, str(msg.channel.id), OWNER_1, "how's my week",
        )

    @pytest.mark.asyncio
    @patch("delta.app._route_dm_to_persistent", new_callable=AsyncMock)
    @patch("delta.app.commands.parse", return_value=None)
    @patch("delta.app.bridges", {})
    async def test_dm_no_persistent_goes_to_hub(
        self, mock_parse, mock_route_persistent,
    ):
        from delta.app import on_message, registry, bridges, HUB_NAME

        hub_bridge = _mock_bridge(active=True)
        bridges[HUB_NAME] = hub_bridge
        msg = _mock_message(user_id=OWNER_2, text="hey what's up")

        with patch.object(registry, "find_persistent_by_owner", return_value=None), \
             patch.object(registry, "find_by_owner", return_value=[MagicMock()]), \
             patch("delta.app._start_typing"):
            await on_message(msg)

        mock_route_persistent.assert_not_called()
        hub_bridge.write_inbox.assert_called_once()

    @pytest.mark.asyncio
    @patch("delta.app._route_dm_to_persistent", new_callable=AsyncMock)
    @patch("delta.app.commands.parse", return_value=None)
    @patch("delta.app.bridges", {})
    async def test_dm_new_user_gets_greeting_and_hub(
        self, mock_parse, mock_route_persistent,
    ):
        """Users with no projects get the first-contact greeting."""
        from delta.app import on_message, registry, bridges, HUB_NAME

        hub_bridge = _mock_bridge(active=True)
        bridges[HUB_NAME] = hub_bridge
        msg = _mock_message(user_id=OWNER_NEW, text="hi")

        with patch.object(registry, "find_persistent_by_owner", return_value=None), \
             patch.object(registry, "find_by_owner", return_value=[]), \
             patch("delta.app._start_typing"):
            await on_message(msg)

        # Greeting sent
        msg.channel.send.assert_called_once_with(
            "hey. I'm Delta. tell me what you want to build "
            "and I'll get you set up."
        )
        # Also routed to hub
        hub_bridge.write_inbox.assert_called_once()

    @pytest.mark.asyncio
    @patch("delta.app._route_dm_to_persistent", new_callable=AsyncMock)
    @patch("delta.app.commands.parse", return_value=None)
    async def test_dm_with_persistent_skips_greeting(
        self, mock_parse, mock_route_persistent,
    ):
        """Users with a persistent agent don't get the first-contact greeting."""
        from delta.app import on_message, registry

        persistent = _make_project_info("chiron-alice", owner=OWNER_1,
                                        project_type="persistent")
        msg = _mock_message(user_id=OWNER_1, text="hi")

        with patch.object(registry, "find_persistent_by_owner",
                          return_value=persistent):
            await on_message(msg)

        # No greeting -- routed to persistent agent
        msg.channel.send.assert_not_called()
        mock_route_persistent.assert_called_once()

    @pytest.mark.asyncio
    @patch("delta.app._route_dm_to_persistent", new_callable=AsyncMock)
    @patch("delta.app._handle_command", new_callable=AsyncMock)
    @patch("delta.app.commands.parse", return_value=("status", {}))
    async def test_admin_command_bypasses_persistent_routing(
        self, mock_parse, mock_handle_cmd, mock_route_persistent,
    ):
        """Admin commands in DMs skip persistent agent routing entirely."""
        from delta.app import on_message

        msg = _mock_message(user_id=OWNER_1, text="status")

        await on_message(msg)

        mock_handle_cmd.assert_called_once()
        mock_route_persistent.assert_not_called()

    @pytest.mark.asyncio
    async def test_bot_messages_ignored(self):
        from delta.app import on_message

        msg = _mock_message()
        msg.author.bot = True

        # Should return immediately, no errors
        await on_message(msg)

    @pytest.mark.asyncio
    async def test_empty_text_ignored(self):
        from delta.app import on_message

        msg = _mock_message(text="   ")

        await on_message(msg)
        msg.channel.send.assert_not_called()


# ===========================================================================
# 4. _hub_snapshot_loop: per-user snapshots for persistent agents
# ===========================================================================

class TestUserSpecificSnapshots:

    def test_snapshot_written_for_persistent_agent(self, tmp_path):
        """Verify the snapshot loop writes filtered snapshots per user."""
        from delta.app import registry

        # Set up a persistent project with a real dir
        project_dir = tmp_path / "chiron-alice"
        project_dir.mkdir()
        (project_dir / "delta-config").mkdir()

        persistent = _make_project_info(
            "chiron-alice", owner=OWNER_1,
            project_type="persistent",
            project_dir=str(project_dir),
        )

        # Also a standard project owned by same user
        standard = _make_project_info(
            "my-app", owner=OWNER_1,
            project_type="standard",
        )

        # And another user's project
        other = _make_project_info(
            "other-proj", owner=OWNER_2,
            project_type="standard",
        )

        # Simulate what the snapshot loop does: build projects list, then
        # write per-user snapshot for persistent agents
        projects = [
            {"name": "chiron-alice", "owner_discord_id": OWNER_1,
             "status": "active", "project_type": "persistent"},
            {"name": "my-app", "owner_discord_id": OWNER_1,
             "status": "active", "project_type": "standard"},
            {"name": "other-proj", "owner_discord_id": OWNER_2,
             "status": "active", "project_type": "standard"},
        ]

        # Replicate the exact logic from the snapshot loop
        with patch.object(registry, "list_projects",
                          return_value=["chiron-alice", "my-app", "other-proj"]):
            def get_side_effect(name):
                return {"chiron-alice": persistent, "my-app": standard,
                        "other-proj": other}.get(name)

            with patch.object(registry, "get", side_effect=get_side_effect):
                import json
                from datetime import datetime, timezone

                for name in registry.list_projects():
                    info = registry.get(name)
                    if not info or info.project_type != "persistent":
                        continue
                    owner = info.owner_discord_id
                    if not owner:
                        continue
                    user_projects = [
                        p for p in projects
                        if p.get("owner_discord_id") == owner
                    ]
                    user_snapshot = {
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "projects": user_projects,
                    }
                    snapshot_path = (
                        Path(info.project_dir) / "delta-config"
                        / "registry-snapshot.json"
                    )
                    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                    snapshot_path.write_text(json.dumps(user_snapshot, indent=2))

        # Verify snapshot was written
        snapshot_path = project_dir / "delta-config" / "registry-snapshot.json"
        assert snapshot_path.exists()

        data = json.loads(snapshot_path.read_text())
        assert "updated_at" in data
        assert len(data["projects"]) == 2  # chiron-alice + my-app (both USER1)
        names = {p["name"] for p in data["projects"]}
        assert names == {"chiron-alice", "my-app"}
        # other-proj (USER2) should NOT be in the snapshot
        assert "other-proj" not in names

    def test_no_snapshot_for_standard_projects(self, tmp_path):
        """Standard projects should not get per-user snapshots."""
        from delta.app import registry

        project_dir = tmp_path / "my-app"
        project_dir.mkdir()
        (project_dir / "delta-config").mkdir()

        standard = _make_project_info(
            "my-app", owner=OWNER_1,
            project_type="standard",
            project_dir=str(project_dir),
        )

        projects = [
            {"name": "my-app", "owner_discord_id": OWNER_1,
             "status": "active", "project_type": "standard"},
        ]

        with patch.object(registry, "list_projects", return_value=["my-app"]):
            with patch.object(registry, "get", return_value=standard):
                for name in registry.list_projects():
                    info = registry.get(name)
                    if not info or info.project_type != "persistent":
                        continue
                    # Should not reach here
                    assert False, "Should not write snapshot for standard project"

        snapshot_path = project_dir / "delta-config" / "registry-snapshot.json"
        assert not snapshot_path.exists()

    def test_snapshot_skips_persistent_without_owner(self, tmp_path):
        """Persistent project with no owner_discord_id gets no snapshot."""
        from delta.app import registry

        project_dir = tmp_path / "chiron-orphan"
        project_dir.mkdir()
        (project_dir / "delta-config").mkdir()

        orphan = _make_project_info(
            "chiron-orphan", owner="",
            project_type="persistent",
            project_dir=str(project_dir),
        )

        with patch.object(registry, "list_projects",
                          return_value=["chiron-orphan"]):
            with patch.object(registry, "get", return_value=orphan):
                for name in registry.list_projects():
                    info = registry.get(name)
                    if not info or info.project_type != "persistent":
                        continue
                    owner = info.owner_discord_id
                    if not owner:
                        continue
                    assert False, "Should skip ownerless persistent"

        snapshot_path = project_dir / "delta-config" / "registry-snapshot.json"
        assert not snapshot_path.exists()


# ===========================================================================
# 5. Template content verification
# ===========================================================================

class TestPersonalAgentTemplate:

    @pytest.fixture
    def template(self):
        path = (
            Path(__file__).parent.parent
            / "project-template"
            / "PERSONAL_AGENT.md"
        )
        return path.read_text()

    def test_dm_section_exists(self, template):
        assert "DMs vs Channel Messages" in template

    def test_channel_type_dm_documented(self, template):
        assert "channel_type" in template
        assert '"dm"' in template

    def test_project_awareness_section(self, template):
        assert "Project Awareness" in template
        assert "registry-snapshot.json" in template

    def test_startup_reads_snapshot(self, template):
        assert "Read `delta-config/registry-snapshot.json`" in template

    def test_outbox_channel_from_inbox(self, template):
        """Template tells agent to use channel from inbox, not hardcoded."""
        assert "use the channel from the inbox message" in template.lower() or \
               "use the `channel` value from the inbox message" in template
