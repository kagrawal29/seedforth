"""Delta -- your projects run themselves. You just dream.

Discord bot where each project gets its own channel, its own Claude Code,
and its own Linux user. The conversation IS the project. Delta handles the rest.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Thread
from zoneinfo import ZoneInfo

import discord
from dotenv import load_dotenv

_delta_dir = Path(__file__).parent.parent
load_dotenv(_delta_dir / os.environ.get("DELTA_CONFIG_FILE", "delta.env"))

from delta import commands
from delta.lifecycle import (
    is_claude_running, is_session_alive, get_project_health,
    start_claude_code, stop_claude_code,
    create_tmux_session, _allocate_port, start_ttyd,
)
from delta.project_bridge import ProjectBridge
from delta.provisioner import provision, provision_in_channel, teardown, restore, LOCAL_MODE, LOCAL_PROJECTS_DIR
from delta.registry import Registry
from delta.resource_manager import resource_manager_loop
from delta.router import Router
from delta import connections

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("delta")

# -- Config ------------------------------------------------------------------

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN_DISCORD_ID = os.getenv("ADMIN_DISCORD_ID", "")
REGISTRY_PATH = os.getenv("DELTA_REGISTRY_PATH", str(_delta_dir / "delta-registry.json"))
_LAST_FIRED_PATH = Path(REGISTRY_PATH).parent / "delta-last-fired.json"
DELTA_SERVER_HOST = os.getenv("DELTA_SERVER_HOST", "")


def _get_ttyd_url(project_name: str) -> str:
    """Return the web terminal URL for a project, or empty string if unavailable."""
    info = registry.get(project_name)
    if not info or not getattr(info, "ttyd_port", 0) or not DELTA_SERVER_HOST:
        return ""
    return f"http://{DELTA_SERVER_HOST}:{info.ttyd_port}"

# -- Globals -----------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
registry = Registry(REGISTRY_PATH)
router = Router(registry)
bridges: dict[str, ProjectBridge] = {}

# -- Auth health tracking ----------------------------------------------------
_auth_alert_sent = False  # True after admin has been DM'd about auth failure
_auth_alert_time: float = 0  # Timestamp of last alert (cooldown)
_AUTH_ALERT_COOLDOWN = 900  # 15 minutes between alerts

# -- Stuck-agent detection ---------------------------------------------------
# Maps channel_id -> project_name for pending restart offers
_restart_offers: dict[str, tuple[str, float]] = {}
_RESTART_OFFER_TTL = 120  # seconds before offer expires

_FRUSTRATION_PATTERNS = {
    "hello?", "hello", "hey?", "hey", "hi?", "??", "?", "are you there",
    "are you there?", "anyone there", "anyone there?", "anyone home",
    "anyone home?", "what's going on", "what's going on?", "you there?",
    "still there?", "you there", "still there", "yo?", "yo",
}

_CONFIRM_PATTERNS = {
    "yes", "yeah", "yep", "sure", "do it", "please", "go ahead",
    "yes please", "ok", "okay", "y", "kick it", "restart it",
}

# -- Typing indicator --------------------------------------------------------
_typing_events: dict[str, asyncio.Event] = {}
_TYPING_TIMEOUT = 120  # max seconds to show "is typing..."


async def _typing_loop(channel, channel_id: str) -> None:
    """Show 'is typing...' until cancelled or timeout."""
    event = asyncio.Event()
    old = _typing_events.get(channel_id)
    if old:
        old.set()  # cancel previous typing for this channel
    _typing_events[channel_id] = event
    try:
        async with channel.typing():
            try:
                await asyncio.wait_for(event.wait(), timeout=_TYPING_TIMEOUT)
            except asyncio.TimeoutError:
                pass
    except Exception:
        pass
    finally:
        if _typing_events.get(channel_id) is event:
            _typing_events.pop(channel_id, None)


def _start_typing(channel, channel_id: str) -> None:
    """Start typing indicator for a channel (call from async context)."""
    asyncio.get_event_loop().create_task(_typing_loop(channel, channel_id))


def _stop_typing(channel_id: str) -> None:
    """Cancel typing indicator for a channel. Thread-safe."""
    event = _typing_events.get(channel_id)
    if event:
        try:
            client.loop.call_soon_threadsafe(event.set)
        except RuntimeError:
            pass

# -- Hub constants -----------------------------------------------------------

HUB_NAME = "__hub__"
HUB_TMUX_SESSION = os.getenv("HUB_TMUX_SESSION", "delta-hub")
HUB_TMUX_PANE = f"{HUB_TMUX_SESSION}:lead"
HUB_TTYD_PORT = int(os.getenv("HUB_TTYD_PORT", "7702"))
_TEMPLATE_DIR = os.getenv("DELTA_TEMPLATE_DIR", "project-template")
_HUB_TEMPLATE_PATH = Path(__file__).parent.parent / _TEMPLATE_DIR / "HUB_CLAUDE.md"
_HUB_LINUX_USER_DEFAULT = os.getenv("HUB_LINUX_USER", "proj-delta-hub")
_HUB_DIR_SERVER = os.getenv("HUB_DIR", "/opt/delta/hub")
_HUB_DIR_NAME = os.getenv("HUB_DIR_NAME", "delta-hub")
ONBOARDING_CHANNEL_ID = os.getenv("ONBOARDING_CHANNEL_ID", "")  # #seedforth-onboarding
LINKEDIN_ONBOARDING_CHANNEL_ID = os.getenv("LINKEDIN_ONBOARDING_CHANNEL_ID", "")

def _hub_dir() -> Path:
    if LOCAL_MODE:
        return Path(LOCAL_PROJECTS_DIR) / _HUB_DIR_NAME
    return Path(_HUB_DIR_SERVER)


# -- Bridge management -------------------------------------------------------

def _get_or_create_bridge(project_name: str) -> ProjectBridge | None:
    if project_name in bridges:
        return bridges[project_name]

    info = registry.get(project_name)
    if not info:
        return None

    bridge = ProjectBridge(
        name=info.name,
        data_dir=info.data_dir,
        tmux_lead_pane=info.tmux_lead_pane,
        nudge_prefix=info.nudge_prefix,
    )
    # Restore last_activity from registry so the resource manager
    # doesn't immediately hibernate a freshly restored project
    if info.last_activity:
        try:
            bridge.last_activity = datetime.fromisoformat(info.last_activity)
        except (ValueError, TypeError):
            pass
    bridges[project_name] = bridge
    return bridge


def _extract_text(data: dict) -> str:
    """Extract text from outbox data, handling dict-wrapped values."""
    text = data.get("text", "")
    if isinstance(text, dict):
        text = text.get("text", "") or ""
    return str(text) if text else ""


def _resolve_files(data: dict, project_dir: str) -> list[discord.File]:
    """Resolve file/files field from outbox data to discord.File objects.

    Paths are resolved relative to the project directory.
    Skips files that don't exist or exceed Discord's 25MB limit.
    """
    raw = data.get("files") or []
    single = data.get("file")
    if single and not raw:
        raw = [single]
    if not raw:
        return []

    project_path = Path(project_dir)
    result = []
    for fpath in raw:
        resolved = Path(fpath)
        if not resolved.is_absolute():
            resolved = project_path / fpath
        if not resolved.is_file():
            logger.warning(f"[outbox] File not found: {resolved}")
            continue
        if resolved.stat().st_size > 25 * 1024 * 1024:
            logger.warning(f"[outbox] File too large (>25MB): {resolved}")
            continue
        try:
            result.append(discord.File(str(resolved)))
        except OSError as e:
            logger.warning(f"[outbox] Could not read file {resolved}: {e}")
    return result


# -- LinkedIn onboarding handling --------------------------------------------

async def _handle_linkedin_onboarding(message: discord.Message) -> None:
    """Handle a message in the LinkedIn onboarding channel.

    Greets the user, then wraps _handle_linkedin_connect.
    """
    user_id = str(message.author.id)
    channel_id = str(message.channel.id)
    display_name = message.author.display_name or message.author.name

    # Show typing while we prepare
    async with message.channel.typing():
        await message.channel.send(
            f"hey {display_name}. let me generate a link to connect your linkedin. "
            f"one moment..."
        )

    await _handle_linkedin_connect(
        "__onboarding__", None, channel_id, display_name, user_id,
    )


# -- Connection command handling ----------------------------------------------

async def _handle_connect_command(
    project_name: str, bridge: ProjectBridge, channel_id: str, toolkit: str
) -> None:
    """Handle an agent's request to connect a user's account.

    Generates an OAuth link via Composio, sends it to Discord,
    then polls until connected or timeout (10 min).
    """
    info = registry.get(project_name)
    if not info:
        return

    user_id = info.owner_discord_id or ""
    if not user_id:
        logger.warning(f"No owner_id for {project_name}, can't initiate connection")
        return

    # Check if already connected
    existing = connections.get_active_connection(user_id, toolkit)
    if existing:
        bridge.write_inbox(
            channel_id, "delta:connection",
            f"User already has {toolkit} connected. You can use {toolkit} tools now."
        )
        return

    # Initiate OAuth
    result = connections.initiate_connection(user_id, toolkit)
    if "error" in result:
        bridge.write_inbox(
            channel_id, "delta:connection",
            f"Could not start {toolkit} connection: {result['error']}"
        )
        return

    redirect_url = result.get("redirect_url", "")
    connection_id = result.get("connection_id", "")

    # Send auth link to Discord
    ch = client.get_channel(int(channel_id)) if channel_id else None
    if not ch:
        try:
            ch = await client.fetch_channel(int(channel_id))
        except Exception:
            logger.warning(f"Could not find channel {channel_id} for connect link")
            return

    await ch.send(
        f"connect your {toolkit} account here (opens their login page, Delta never sees your password):\n{redirect_url}"
    )

    # Suppress silence nudges while waiting for OAuth
    bridge.connection_pending = True

    # Poll for connection completion (every 15s, max 10 min)
    max_polls = 40  # 40 * 15s = 10 min
    connected = False
    for _ in range(max_polls):
        await asyncio.sleep(15)
        status = connections.check_status(connection_id)
        if status == "ACTIVE":
            connected = True
            break
        if status not in ("INITIATED", "ERROR"):
            # FAILED or unknown -- stop polling
            break

    bridge.connection_pending = False

    if connected:
        await ch.send("connected.")
        bridge.write_inbox(
            channel_id, "delta:connection",
            f"User connected {toolkit}. You can now use {toolkit} tools via RUBE_SEARCH_TOOLS + RUBE_MULTI_EXECUTE_TOOL."
        )
        # Nudge agent to process the inbox
        try:
            msg_files = sorted(bridge.inbox_dir.glob("*.json"))
            if msg_files:
                bridge.send_to_lead(msg_files[-1].stem)
        except Exception:
            pass
    else:
        await ch.send(f"the {toolkit} connection didn't complete. no worries -- just let me know when you want to try again.")
        bridge.write_inbox(
            channel_id, "delta:connection",
            f"User did not complete {toolkit} connection. Offer to try again or use sample data."
        )

    logger.info(f"Connection flow for {project_name}/{toolkit}: {'connected' if connected else 'timeout/failed'}")


# -- Unipile LinkedIn connection flow ----------------------------------------

_UNIPILE_TOOL = str(_delta_dir / "tools" / "unipile.py")
if not LOCAL_MODE and Path("/opt/delta/tools/unipile.py").exists():
    _UNIPILE_TOOL = "/opt/delta/tools/unipile.py"


def _unipile_run(command: list[str]) -> dict:
    """Run a unipile.py CLI command and return parsed JSON."""
    env = {**os.environ}
    result = subprocess.run(
        ["python3", _UNIPILE_TOOL] + command,
        capture_output=True, text=True, env=env, timeout=30,
    )
    if result.returncode != 0:
        return {"error": result.stderr.strip() or "unipile command failed"}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON: {result.stdout[:200]}"}


def _sanitize_linkedin_name(display_name: str) -> str:
    """Convert a display name to a valid project slug.

    Max 21 chars so that 'linkedin-' + slug fits within the 30-char
    project name limit. Truncates at a hyphen boundary when possible.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", display_name.lower()).strip("-")
    if len(slug) > 21:
        # Try to cut at a hyphen boundary for a cleaner name
        truncated = slug[:21]
        last_hyphen = truncated.rfind("-")
        if last_hyphen > 5:
            truncated = truncated[:last_hyphen]
        slug = truncated.rstrip("-")
    return slug or "user"


async def _handle_linkedin_connect(
    source_project: str, bridge: ProjectBridge | None, channel_id: str,
    user_display_name: str, owner_discord_id: str,
) -> None:
    """Handle a request to connect a user's LinkedIn via Unipile.

    Generates a hosted auth link, polls for the new account, then
    auto-provisions a linkedin-{name} project. Users can have multiple
    linkedin projects (one per account).
    """
    # Snapshot existing accounts
    accounts_data = _unipile_run(["accounts"])
    existing_ids = set()
    for item in accounts_data.get("items", accounts_data.get("data", [])):
        existing_ids.add(item.get("id", ""))

    # Generate hosted auth link
    link_data = _unipile_run(["connect-linkedin", "--name", user_display_name])
    auth_url = link_data.get("url", "")
    if not auth_url:
        logger.error(f"Failed to generate Unipile link: {link_data}")
        ch = client.get_channel(int(channel_id)) if channel_id else None
        if ch:
            await ch.send("couldn't generate the linkedin connection link. try again in a moment.")
        return

    # Send link to Discord
    ch = client.get_channel(int(channel_id)) if channel_id else None
    if not ch:
        try:
            ch = await client.fetch_channel(int(channel_id))
        except Exception:
            logger.warning(f"Could not find channel {channel_id} for linkedin connect")
            return

    await ch.send(
        f"connect your linkedin here (opens Unipile's hosted login page, "
        f"Delta never sees your password):\n{auth_url}"
    )

    # Suppress silence nudges while waiting
    if bridge:
        bridge.connection_pending = True

    # Poll for new account (every 15s, max 10 min)
    max_polls = 40
    new_account_id = ""
    new_account_name = ""
    for i in range(max_polls):
        await asyncio.sleep(15)
        poll_data = _unipile_run(["accounts"])
        for item in poll_data.get("items", poll_data.get("data", [])):
            aid = item.get("id", "")
            if aid and aid not in existing_ids:
                new_account_id = aid
                new_account_name = item.get("name", user_display_name)
                break
        if new_account_id:
            break

    if bridge:
        bridge.connection_pending = False

    if not new_account_id:
        await ch.send(
            "the linkedin connection didn't complete within 10 minutes. "
            "no worries -- just let me know when you want to try again."
        )
        return

    # Account connected -- provision the linkedin project
    await ch.send("linkedin connected. setting up your agent now...")

    proj_slug = _sanitize_linkedin_name(new_account_name or user_display_name)
    proj_name = f"linkedin-{proj_slug}"
    # Avoid name collisions if user already has a project with this name
    if registry.get(proj_name):
        for i in range(2, 10):
            candidate = f"{proj_name}-{i}"
            if len(candidate) <= 30 and not registry.get(candidate):
                proj_name = candidate
                break

    try:
        guild = client.guilds[0] if client.guilds else None
        info = await provision(
            name=proj_name,
            registry=registry,
            discord_bot=client,
            guild=guild,
            owner_discord_id=owner_discord_id,
            project_type="linkedin",
            admin_brief=new_account_name or user_display_name,
        )

        # Write UNIPILE_ACCOUNT_ID to linkedin-config.env
        env_path = Path(info.project_dir) / "linkedin-config.env"
        if env_path.exists():
            content = env_path.read_text()
            content += f"export UNIPILE_ACCOUNT_ID={new_account_id}\n"
            env_path.write_text(content)
            # Fix ownership if server mode
            if info.linux_user:
                subprocess.run(
                    ["chown", f"{info.linux_user}:", str(env_path)],
                    capture_output=True, text=True,
                )

        # Update registry with account ID
        registry.update(proj_name, unipile_account_id=new_account_id)

        # Start watchers
        _start_watchers(proj_name)

        # Send welcome in new channel
        new_ch = client.get_channel(int(info.discord_channel_id)) if info.discord_channel_id else None
        if not new_ch:
            try:
                new_ch = await client.fetch_channel(int(info.discord_channel_id))
            except Exception:
                new_ch = None
        if new_ch:
            await new_ch.send(
                f"hey <@{owner_discord_id}>. your linkedin is connected and i'm your agent now. "
                f"tell me about your goals and i'll start managing your linkedin."
            )

        # Confirm back in source channel
        await ch.send(f"done. your linkedin agent is live in <#{info.discord_channel_id}>.")

    except Exception as e:
        logger.error(f"LinkedIn project provisioning failed: {e}", exc_info=True)
        await ch.send(f"something went wrong setting up the project: {e}")

    logger.info(
        f"LinkedIn connect for {owner_discord_id}: "
        f"account={new_account_id} project={proj_name}"
    )


def _gh_auth_start_subprocess(gh_cmd: list[str]) -> tuple[str, str, str, bool]:
    """Run gh auth login in a thread-safe blocking way.

    Returns (device_url, user_code, stderr_output, exited_early).
    This runs in a thread via asyncio.to_thread so it never blocks the
    event loop.
    """
    import os as _os

    proc = subprocess.Popen(
        gh_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stderr_output = ""
    device_url = ""
    user_code = ""

    # Set stderr to non-blocking so os.read won't hang
    fd = proc.stderr.fileno()
    import fcntl
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | _os.O_NONBLOCK)

    # Give it up to 15 seconds to produce the device code
    deadline = time.time() + 15
    while time.time() < deadline:
        if proc.poll() is not None:
            # Process exited early -- read remaining
            try:
                remaining = _os.read(fd, 65536)
                stderr_output += remaining.decode("utf-8", errors="replace")
            except (BlockingIOError, OSError):
                pass
            break
        try:
            chunk = _os.read(fd, 4096)
            if chunk:
                stderr_output += chunk.decode("utf-8", errors="replace")
                if "one-time code" in stderr_output.lower() or "enter the code" in stderr_output.lower():
                    break
        except (BlockingIOError, OSError):
            pass
        time.sleep(0.5)

    # Parse the device code from stderr
    for line in stderr_output.split("\n"):
        line_lower = line.lower().strip()
        if "github.com/login/device" in line:
            url_match = re.search(r'(https://github\.com/login/device\S*)', line)
            if url_match:
                device_url = url_match.group(1)
            elif not device_url:
                device_url = "https://github.com/login/device"
        if "code:" in line_lower or "code :" in line_lower:
            code_match = re.search(r'([A-Z0-9]{4}-[A-Z0-9]{4})', line)
            if code_match:
                user_code = code_match.group(1)

    exited_early = proc.poll() is not None

    if exited_early:
        try:
            stdout_out = proc.stdout.read().decode("utf-8", errors="replace") if proc.stdout else ""
        except Exception:
            stdout_out = ""
        stderr_output += stdout_out

    # If process is still running, leave it alive -- it needs to complete the
    # OAuth handshake and save the token to ~/.config/gh/. Killing it here
    # is why auth appeared to succeed on GitHub's side but never registered.
    if exited_early:
        try:
            proc.kill()
        except OSError:
            pass

    if not device_url:
        device_url = "https://github.com/login/device"

    return device_url, user_code, stderr_output, exited_early


async def _handle_gh_auth_command(
    project_name: str, bridge: ProjectBridge, channel_id: str
) -> None:
    """Handle an agent's request to authenticate GitHub CLI for its user.

    Runs `gh auth login --web` as the project's linux user, captures
    the device URL and one-time code, sends them to Discord, then polls
    for completion. All blocking subprocess work runs in a thread to
    avoid freezing the Discord event loop.
    """
    info = registry.get(project_name)
    if not info:
        return

    linux_user = info.linux_user or ""

    # Build the gh auth command
    # --git-protocol https avoids SSH key setup
    gh_cmd = ["gh", "auth", "login", "--web", "--git-protocol", "https"]
    if linux_user and not LOCAL_MODE:
        gh_cmd = ["sudo", "-u", linux_user] + gh_cmd

    # Suppress silence nudges while waiting for auth
    bridge.connection_pending = True
    authed = False

    try:
        # Run the blocking subprocess work in a thread
        device_url, user_code, stderr_output, exited_early = await asyncio.to_thread(
            _gh_auth_start_subprocess, gh_cmd
        )

        # Send to Discord
        ch = client.get_channel(int(channel_id)) if channel_id else None
        if not ch:
            try:
                ch = await client.fetch_channel(int(channel_id))
            except Exception:
                logger.warning(f"Could not find channel {channel_id} for gh auth")
                bridge.connection_pending = False
                return

        if user_code:
            await ch.send(
                f"go to {device_url} and enter code: **{user_code}**\n"
                f"this connects your github account so i can work with your repos."
            )
        elif exited_early:
            if "already logged in" in stderr_output.lower() or "logged in" in stderr_output.lower():
                bridge.write_inbox(
                    channel_id, "delta:system",
                    "GitHub CLI is already authenticated. You can use gh commands."
                )
                bridge.connection_pending = False
                return
            else:
                await ch.send(
                    "could not start github auth. the `gh` cli might not be installed on the server."
                )
                bridge.write_inbox(
                    channel_id, "delta:system",
                    f"GitHub auth failed to start. Output: {stderr_output[:300]}"
                )
                bridge.connection_pending = False
                return
        else:
            await ch.send(
                f"go to {device_url} to authenticate github.\n"
                f"could not capture the one-time code automatically -- check your terminal."
            )

        # Poll for auth completion (every 10s, up to 5 min)
        max_polls = 30
        authed = False
        for _ in range(max_polls):
            await asyncio.sleep(10)
            status_cmd = ["gh", "auth", "status"]
            if linux_user and not LOCAL_MODE:
                status_cmd = ["sudo", "-u", linux_user] + status_cmd
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    status_cmd, capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    authed = True
                    break
            except (subprocess.TimeoutExpired, OSError):
                pass

        bridge.connection_pending = False

        if authed:
            await ch.send("github connected.")
            bridge.write_inbox(
                channel_id, "delta:system",
                "GitHub CLI authenticated. You can now use `gh` for repo operations, PR creation, issue tracking."
            )
            try:
                msg_files = sorted(bridge.inbox_dir.glob("*.json"))
                if msg_files:
                    bridge.send_to_lead(msg_files[-1].stem)
            except Exception:
                pass
        else:
            await ch.send("github auth timed out. no worries, just let me know when you want to try again.")
            bridge.write_inbox(
                channel_id, "delta:system",
                "GitHub auth timed out. Offer to try again later."
            )

    except Exception as e:
        logger.error(f"gh auth handler error for {project_name}: {e}")
        bridge.connection_pending = False
        bridge.write_inbox(
            channel_id, "delta:system",
            f"GitHub auth failed: {e}"
        )

    logger.info(f"GitHub auth flow for {project_name}: {'authed' if authed else 'timeout/failed'}")


async def _handle_onboarding_complete(project_name: str, data: dict) -> None:
    """Handle personal agent onboarding_complete signal.

    1. Read YAML outputs from memory/
    2. Load PERSONAL_AGENT.md template
    3. Inject profile_summary
    4. Overwrite CLAUDE.md
    5. Restart Claude Code
    6. Update registry project_type to "persistent"
    7. Notify user in Discord
    """
    info = registry.get(project_name)
    if not info:
        logger.warning(f"onboarding_complete for unknown project {project_name}")
        return

    project_dir = Path(info.project_dir)
    profile_summary = data.get("profile_summary", "")
    channel_id = data.get("channel", info.discord_channel_id)

    # Load the persistent template
    persistent_template_path = (
        Path(__file__).parent.parent / _TEMPLATE_DIR / "PERSONAL_AGENT.md"
    )
    if not persistent_template_path.exists():
        logger.error(f"PERSONAL_AGENT.md not found at {persistent_template_path}")
        return

    template = persistent_template_path.read_text()
    claude_md = template.format(
        project_name=info.name,
        project_dir=info.project_dir,
        linux_user=info.linux_user or os.getenv("USER", "local"),
        discord_channel_id=info.discord_channel_id,
        profile_summary=profile_summary or "(onboarding profile available in memory/)",
        ttyd_url=_get_ttyd_url(info.name),
    )

    # Overwrite CLAUDE.md
    claude_md_path = project_dir / "CLAUDE.md"
    claude_md_path.write_text(claude_md)

    # Fix ownership on server
    if info.linux_user:
        subprocess.run(
            ["chown", f"{info.linux_user}:", str(claude_md_path)],
            capture_output=True, text=True,
        )

    # Git commit the transition
    if info.linux_user:
        from delta.isolation import run_as_user
        run_as_user(info.linux_user, f"git -C {info.project_dir} add -A")
        run_as_user(
            info.linux_user,
            f'git -C {info.project_dir} commit -m "onboarding: complete, transition to persistent agent"',
        )
    else:
        subprocess.run(
            ["git", "-C", info.project_dir, "add", "-A"],
            capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "-C", info.project_dir, "commit", "-m",
             "onboarding: complete, transition to persistent agent"],
            capture_output=True, text=True,
        )

    # Stop and restart Claude Code (picks up new CLAUDE.md)
    stop_claude_code(info.tmux_lead_pane, grace=5)
    await asyncio.sleep(2)
    start_claude_code(
        info.project_dir, info.tmux_lead_pane,
        linux_user=info.linux_user or None,
    )

    # Update registry
    registry.update(project_name, project_type="persistent")

    # Send completion message to user's DM
    owner_id = info.owner_discord_id
    if owner_id:
        try:
            user = await client.fetch_user(int(owner_id))
            dm_channel = await user.create_dm()
            await dm_channel.send(
                "onboarding complete. your personal agent is live. just DM me anytime."
            )
        except Exception as e:
            logger.warning(f"Could not DM user about onboarding completion: {e}")

    # Post final message in onboarding channel and archive it
    try:
        channel = client.get_channel(int(channel_id))
        if not channel:
            channel = await client.fetch_channel(int(channel_id))
        if channel:
            await channel.send(
                "onboarding complete. this channel is now archived. "
                "talk to your agent via DM from now on."
            )
            await channel.edit(archived=True)
            logger.info(f"Archived onboarding channel {channel_id} for {project_name}")
    except Exception as e:
        logger.warning(f"Could not archive onboarding channel: {e}")

    logger.info(f"Onboarding complete for {project_name}, transitioned to persistent agent")


def _start_watchers(project_name: str) -> None:
    bridge = _get_or_create_bridge(project_name)
    if not bridge:
        return

    loop = asyncio.get_event_loop()

    def _outbox_callback(data: dict) -> None:
        # -- Command interception: agent sends structured commands --
        command = data.get("command")
        if command == "onboarding_complete":
            asyncio.run_coroutine_threadsafe(
                _handle_onboarding_complete(project_name, data), loop,
            )
            return
        if command == "connect":
            toolkit = data.get("toolkit", "")
            if not toolkit:
                return
            channel_id = data.get("channel", "")
            asyncio.run_coroutine_threadsafe(
                _handle_connect_command(project_name, bridge, channel_id, toolkit),
                loop,
            )
            return
        if command == "check_connection":
            toolkit = data.get("toolkit", "")
            info = registry.get(project_name)
            user_id = info.owner_discord_id if info else ""
            conn = connections.get_active_connection(user_id, toolkit) if user_id else None
            ch_id = info.discord_channel_id if info else ""
            status = "connected" if conn else "not connected"
            bridge.write_inbox(ch_id, "delta:connection", f"{toolkit} status: {status}")
            try:
                bridge.send_to_lead(bridge._random_id())
            except Exception:
                pass
            return
        if command == "linkedin_connect":
            display_name = data.get("user_display_name", "user")
            channel_id = data.get("reply_channel", "") or data.get("channel", "")
            if not channel_id:
                info = registry.get(project_name)
                channel_id = info.discord_channel_id if info else ""
            info = registry.get(project_name)
            owner = info.owner_discord_id if info else ""
            if channel_id and owner:
                asyncio.run_coroutine_threadsafe(
                    _handle_linkedin_connect(
                        project_name, bridge, channel_id, display_name, owner
                    ),
                    loop,
                )
            return
        if command == "gh_auth_start":
            channel_id = data.get("reply_channel", "") or data.get("channel", "")
            if not channel_id:
                info = registry.get(project_name)
                channel_id = info.discord_channel_id if info else ""
            if channel_id:
                asyncio.run_coroutine_threadsafe(
                    _handle_gh_auth_command(project_name, bridge, channel_id),
                    loop,
                )
            return
        if command in ("create_project", "new_project"):
            # Project agent requesting a new project -- provision it
            proj_name = data.get("name", "")
            description = data.get("description", "")
            proj_type = data.get("project_type", "standard")
            proj_admin_brief = data.get("admin_brief", "")
            proj_target_user_id = data.get("target_user_id", "")
            info = registry.get(project_name)
            owner = info.owner_discord_id if info else ""
            source_channel = info.discord_channel_id if info else data.get("channel", "")

            async def _project_create():
                try:
                    guild = client.guilds[0] if client.guilds else None
                    new_info = await provision(
                        name=proj_name,
                        registry=registry,
                        discord_bot=client,
                        guild=guild,
                        owner_discord_id=owner,
                        project_type=proj_type,
                        admin_brief=proj_admin_brief,
                        target_user_id=proj_target_user_id,
                    )
                    _start_watchers(proj_name)
                    # Seed the new project with context if provided
                    if description:
                        seed_path = Path(new_info.project_dir) / "SEED.md"
                        try:
                            seed_path.write_text(f"# {proj_name}\n\n{description}\n")
                        except OSError:
                            pass

                    # Send welcome message in the new channel for onboarding projects
                    if proj_type == "personal" and new_info.discord_channel_id:
                        try:
                            new_channel = client.get_channel(int(new_info.discord_channel_id))
                            if not new_channel:
                                new_channel = await client.fetch_channel(int(new_info.discord_channel_id))
                            if new_channel:
                                if proj_target_user_id:
                                    welcome = (
                                        f"hey <@{proj_target_user_id}>. i'm Delta, your personal agent. "
                                        f"let's get to know each other."
                                    )
                                else:
                                    welcome = (
                                        "hey. i'm Delta, your personal agent. "
                                        "let's get to know each other."
                                    )
                                await new_channel.send(welcome)
                        except Exception as e:
                            logger.warning(f"Could not send welcome in {proj_name}: {e}")

                    # Notify the requesting agent
                    confirm = (
                        f"Project **{proj_name}** created. "
                        f"Channel: <#{new_info.discord_channel_id}>. "
                        f"Tell the user their project is ready."
                    )
                    bridge.write_inbox(source_channel, "delta:system", confirm)
                    try:
                        bridge.send_to_lead(bridge._random_id())
                    except Exception:
                        pass
                    logger.info(f"Project {proj_name} created by {project_name}")
                except Exception as e:
                    logger.error(f"Project creation by {project_name} failed: {e}")
                    bridge.write_inbox(
                        source_channel, "delta:system",
                        f"Could not create project {proj_name}: {e}"
                    )
                    try:
                        bridge.send_to_lead(bridge._random_id())
                    except Exception:
                        pass

            asyncio.run_coroutine_threadsafe(_project_create(), loop)
            return

        channel_id = data.get("channel")
        if not channel_id:
            return
        _stop_typing(channel_id)
        channel = client.get_channel(int(channel_id))

        async def _send():
            nonlocal channel
            # DM channels may not be in cache -- fetch if needed
            if not channel:
                try:
                    channel = await client.fetch_channel(int(channel_id))
                except Exception:
                    logger.warning(f"[outbox:{project_name}] Channel {channel_id} not found")
                    return
            try:
                info = registry.get(project_name)
                project_dir = info.project_dir if info else ""
                files = _resolve_files(data, project_dir) if project_dir else []
                embed_data = data.get("embed")
                if embed_data:
                    embed = discord.Embed(
                        title=embed_data.get("title", ""),
                        description=embed_data.get("description", ""),
                        color=embed_data.get("color", 0x2ecc71),
                    )
                    for field in embed_data.get("fields", []):
                        embed.add_field(
                            name=field.get("name", ""),
                            value=field.get("value", ""),
                            inline=field.get("inline", False),
                        )
                    if embed_data.get("footer"):
                        embed.set_footer(text=embed_data["footer"])
                    text = _extract_text(data)
                    await channel.send(content=text or None, embed=embed,
                                       files=files or discord.utils.MISSING)
                else:
                    await channel.send(_extract_text(data) or "(empty)",
                                       files=files or discord.utils.MISSING)
            except Exception as e:
                logger.warning(f"[outbox:{project_name}] Discord send failed: {e}")

        asyncio.run_coroutine_threadsafe(_send(), loop)

    t = Thread(target=bridge.watch_outbox, args=(_outbox_callback,), daemon=True)
    t.start()

    # Inbox re-nudge watcher -- retries nudges that got lost
    t2 = Thread(target=bridge.watch_inbox, daemon=True)
    t2.start()

    # Follow-up watcher -- delivers delayed messages from agents
    t3 = Thread(target=bridge.watch_followups, args=(_outbox_callback,), daemon=True)
    t3.start()

    # Progress watcher -- streams hook-generated updates to Discord
    def _progress_callback(message: str):
        async def _send_progress():
            try:
                channel = client.get_channel(int(info.discord_channel_id))
                if channel:
                    await channel.send(f"*{message}*")
            except Exception as e:
                logger.warning(f"[progress:{project_name}] send failed: {e}")
        asyncio.run_coroutine_threadsafe(_send_progress(), loop)

    t4 = Thread(target=bridge.watch_progress, args=(_progress_callback,), daemon=True)
    t4.start()

    logger.info(f"Watchers started for {project_name}")


# -- Status helpers ----------------------------------------------------------

def _format_project_status(name: str) -> str:
    info = registry.get(name)
    if not info:
        return f"**{name}** -- not found."

    if info.status == "hibernated":
        return f"**{name}** -- hibernated (will wake on contact)"

    health = get_project_health(info.tmux_lead_pane)
    bridge = _get_or_create_bridge(name)
    pending = bridge.pending_inbox_count() if bridge else 0

    if health["claude_running"]:
        auth_err = bridge.check_auth_error() if bridge else None
        if auth_err:
            status_line = "running but auth expired -- messages stuck"
        elif pending > 0:
            status_line = "running, messages waiting"
        else:
            status_line = "running, idle"
    elif health["session_alive"]:
        status_line = "stopped"
    else:
        status_line = "offline"

    # Show active tasks from schedule
    schedule = bridge.get_schedule() if bridge else []
    active = [t for t in schedule if t.get("status") in ("in_progress", "recurring")]

    lines = [
        f"**{name}** -- {status_line}",
        f"  {pending} messages waiting" if pending else "  inbox clear",
    ]
    if active:
        lines.append(f"  {len(active)} active tasks")
    if info.github_repo:
        lines.append(f"  repo: `{info.github_repo}`")
    return "\n".join(lines)


def _format_all_status() -> str:
    names = registry.list_projects()
    if not names:
        return "No projects running."

    lines = []
    for name in names:
        info = registry.get(name)
        if not info:
            continue
        owner = info.owner_discord_id
        if info.status == "hibernated":
            lines.append(f"`z` **{name}** | hibernated | owner: <@{owner}>")
            continue
        health = get_project_health(info.tmux_lead_pane)
        bridge = _get_or_create_bridge(name)
        pending = bridge.pending_inbox_count() if bridge else 0
        auth_err = bridge.check_auth_error() if bridge and health["claude_running"] else None
        ram = _get_user_ram(info.linux_user) if info.linux_user else "?"
        if auth_err:
            icon = "!"
            state = "auth expired"
        elif not health["claude_running"]:
            icon = "-"
            state = "stopped"
        elif pending > 0:
            icon = "?"
            state = f"{pending} msgs waiting"
        else:
            icon = "+"
            state = "idle"
        lines.append(f"`{icon}` **{name}** | {state} | {ram} RAM | owner: <@{owner}>")

    return f"**{len(names)} projects:**\n" + "\n".join(lines)


def _get_user_ram(linux_user: str) -> str:
    try:
        result = subprocess.run(
            ["ps", "--no-headers", "-u", linux_user, "-o", "rss"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return "n/a"
        total_kb = sum(int(line.strip()) for line in result.stdout.strip().split("\n") if line.strip())
        total_mb = total_kb // 1024
        return f"{total_mb}MB"
    except (ValueError, OSError):
        return "n/a"


def _format_logs(entries: list[dict]) -> str:
    if not entries:
        return "No recent conversation."

    lines = []
    for e in entries:
        ts = e.get("ts", "")[:19].replace("T", " ")
        direction = ">>>" if e["direction"] == "in" else "<<<"
        text = e.get("text", "")[:200]
        user = e.get("user", "?")
        lines.append(f"`{ts}` {direction} **{user}**: {text}")

    return "\n".join(lines)


# -- Command handlers --------------------------------------------------------

async def _handle_command(cmd: str, args: dict, message: discord.Message) -> None:
    user_id = str(message.author.id)
    is_admin = user_id == ADMIN_DISCORD_ID
    guild = message.guild or (client.guilds[0] if client.guilds else None)

    if cmd == "help":
        await message.channel.send(commands.HELP_TEXT)

    elif cmd == "list":
        projects = registry.find_by_owner(user_id)
        if not projects:
            await message.channel.send(
                "No projects yet. Say `new project <name>` and I'll set one up for you."
            )
        else:
            lines = [f"- **{p.name}**" for p in projects]
            await message.channel.send("\n".join(lines))

    elif cmd == "status":
        project_name = args.get("project")
        if project_name:
            await message.channel.send(_format_project_status(project_name))
        else:
            projects = registry.find_by_owner(user_id)
            if not projects:
                await message.channel.send("No projects yet.")
            elif len(projects) == 1:
                await message.channel.send(_format_project_status(projects[0].name))
            else:
                parts = [_format_project_status(p.name) for p in projects]
                await message.channel.send("\n\n".join(parts))

    elif cmd == "status_all":
        if not is_admin:
            await message.channel.send("Admin only.")
            return
        await message.channel.send(_format_all_status())

    elif cmd == "new_project":
        is_dm = isinstance(message.channel, discord.DMChannel)
        channel_id = str(message.channel.id)
        name = args.get("name")
        use_here = args.get("here", False)

        if not name and not use_here:
            await message.channel.send(
                "What do you want to call it? Just say `new project <name>` "
                "or `new project <name> here` to use this channel."
            )
            return

        # "new project here" without a name -- use channel name
        if not name and use_here:
            name = message.channel.name if hasattr(message.channel, "name") else None
            if not name:
                await message.channel.send("Give the project a name: `new project <name> here`")
                return

        github_repo = args.get("github_repo", "")
        await message.channel.send(f"Setting up **{name}**. One moment.")

        try:
            if use_here and not is_dm:
                # Use the current channel
                info = await provision_in_channel(
                    name=name,
                    registry=registry,
                    discord_bot=client,
                    guild=guild,
                    owner_discord_id=user_id,
                    channel_id=channel_id,
                    github_repo=github_repo,
                )
            else:
                info = await provision(
                    name=name,
                    registry=registry,
                    discord_bot=client,
                    guild=guild,
                    owner_discord_id=user_id,
                    github_repo=github_repo,
                )
            _start_watchers(name)

            if use_here and not is_dm:
                reply = f"**{name}** is live right here. go tell it what to build."
            else:
                reply = f"**{name}** is live. <#{info.discord_channel_id}> -- go tell it what to build."
            if github_repo:
                reply += f" (cloned from `{github_repo}`)"
            await message.channel.send(reply)
        except (ValueError, RuntimeError) as e:
            await message.channel.send(f"Could not set up: {e}")

    elif cmd == "teardown":
        project_name = args["project"]
        info = registry.get(project_name)
        if not info:
            await message.channel.send(f"No project called **{project_name}**.")
            return
        if info.owner_discord_id != user_id and not is_admin:
            await message.channel.send("That's not your project.")
            return

        await message.channel.send(f"Shutting down **{project_name}**.")
        try:
            await teardown(project_name, registry, client, guild)
            bridges.pop(project_name, None)
            await message.channel.send(f"**{project_name}** is gone. Channel deleted, user removed, everything cleaned up.")
        except Exception as e:
            await message.channel.send(f"Teardown hit a problem: {e}")

    # -- Admin commands --

    elif cmd == "logs":
        if not is_admin:
            await message.channel.send("Admin only.")
            return
        project_name = args["project"]
        bridge = _get_or_create_bridge(project_name)
        if not bridge:
            await message.channel.send(f"No project called **{project_name}**.")
            return
        entries = bridge.get_recent_logs(30)
        text = _format_logs(entries)
        # Discord has a 2000 char limit
        if len(text) > 1900:
            text = text[-1900:]
        await message.channel.send(text or "No recent logs.")

    elif cmd == "peek":
        if not is_admin:
            await message.channel.send("Admin only.")
            return
        project_name = args["project"]
        bridge = _get_or_create_bridge(project_name)
        if not bridge:
            await message.channel.send(f"No project called **{project_name}**.")
            return
        scrollback = bridge.capture_tmux_scrollback(40)
        # Wrap in code block for readability
        text = f"```\n{scrollback[:1800]}\n```"
        await message.channel.send(text)

    elif cmd == "admin_send":
        if not is_admin:
            await message.channel.send("Admin only.")
            return
        project_name = args["project"]
        msg_text = args["text"]
        bridge = _get_or_create_bridge(project_name)
        if not bridge:
            await message.channel.send(f"No project called **{project_name}**.")
            return
        info = registry.get(project_name)
        channel_id = info.discord_channel_id if info else ""
        msg_id = bridge.write_inbox(channel_id, f"admin:{user_id}", msg_text)
        if bridge.is_project_active():
            try:
                bridge.send_to_lead(msg_id)
            except Exception as e:
                logger.warning(f"Nudge failed: {e}")
        await message.channel.send(f"Sent to **{project_name}**.")

    elif cmd == "restart":
        project_name = args["project"]
        info = registry.get(project_name)
        if not info:
            await message.channel.send(f"No project called **{project_name}**.")
            return
        if not is_admin and info.owner_discord_id != user_id:
            await message.channel.send("That's not your project.")
            return
        await message.channel.send(f"Restarting Claude Code for **{project_name}**...")
        stop_claude_code(info.tmux_lead_pane, grace=5)
        # Recreate tmux session if it's gone (e.g. after service restart)
        if not is_session_alive(info.tmux_session):
            create_tmux_session(info.tmux_session)
        started = start_claude_code(
            info.project_dir, info.tmux_lead_pane,
            linux_user=info.linux_user or None,
        )
        if started:
            # Reset idle timer so resource manager doesn't immediately hibernate
            bridge = _get_or_create_bridge(project_name)
            if bridge:
                bridge.touch_activity()
            await message.channel.send(f"**{project_name}** Claude Code restarted.")
        else:
            await message.channel.send(f"Failed to restart. Check the tmux session `{info.tmux_session}`.")

    elif cmd == "restart_hub":
        if not is_admin:
            await message.channel.send("Admin only.")
            return
        await message.channel.send("Restarting hub...")
        stop_claude_code(HUB_TMUX_PANE, grace=5)
        hub_bridge = bridges.pop(HUB_NAME, None)
        if hub_bridge:
            hub_bridge.shutdown()
        _init_hub()
        _start_hub_watchers()
        await message.channel.send("Hub restarted.")

    elif cmd == "peek_hub":
        if not is_admin:
            await message.channel.send("Admin only.")
            return
        hub_bridge = bridges.get(HUB_NAME)
        if not hub_bridge:
            await message.channel.send("Hub not initialized.")
            return
        scrollback = hub_bridge.capture_tmux_scrollback(40)
        text = f"```\n{scrollback[:1800]}\n```"
        await message.channel.send(text)

    elif cmd == "schedule":
        project_name = args["project"]
        bridge = _get_or_create_bridge(project_name)
        if not bridge:
            await message.channel.send(f"No project called **{project_name}**.")
            return

        # Schedule is visible to owner and admin
        info = registry.get(project_name)
        if info and info.owner_discord_id != user_id and not is_admin:
            await message.channel.send("That's not your project.")
            return

        tasks = bridge.get_schedule()
        if not tasks:
            await message.channel.send(f"**{project_name}** has no tasks scheduled yet.")
            return

        lines = [f"**{project_name}** schedule ({len(tasks)} tasks):\n"]
        for t in tasks:
            status = t.get("status", "?")
            what = t.get("what", "(no description)")
            icon = {"in_progress": ">", "done": "+", "recurring": "~", "pending": "-"}.get(status, "?")
            line = f"`{icon}` {what}"
            if status == "recurring":
                line += f" (every {t.get('recurrence', '?')})"
            lines.append(line)

        text = "\n".join(lines)
        if len(text) > 1900:
            text = text[:1900] + "\n..."
        await message.channel.send(text)

    elif cmd == "refresh_templates":
        if not is_admin:
            await message.channel.send("Admin only.")
            return
        from delta.provisioner import refresh_templates
        await message.channel.send("Refreshing CLAUDE.md for all projects...")
        count = refresh_templates(registry)
        await message.channel.send(f"Done. Updated {count} project(s).")


# -- Hub (orchestrator) ------------------------------------------------------

def _init_hub() -> None:
    """Initialize the hub Claude Code instance for DM orchestration."""
    hub = _hub_dir()
    hub_linux_user = ""

    if LOCAL_MODE:
        hub.mkdir(parents=True, exist_ok=True)
    else:
        # Server mode: create a dedicated user for the hub
        from delta.isolation import linux_username, create_user, run_as_user, user_exists
        hub_linux_user = _HUB_LINUX_USER_DEFAULT
        if not user_exists(hub_linux_user):
            try:
                create_user("delta-hub")
            except RuntimeError as e:
                logger.warning(f"Hub user creation failed (may already exist): {e}")
        # Create hub dir owned by hub user
        run_as_user(hub_linux_user, f"mkdir -p {hub}")

    data_dir = hub / "delta-config"

    if LOCAL_MODE:
        (data_dir / "inbox").mkdir(parents=True, exist_ok=True)
        (data_dir / "outbox").mkdir(parents=True, exist_ok=True)
        (data_dir / "logs").mkdir(parents=True, exist_ok=True)
    else:
        from delta.isolation import run_as_user
        run_as_user(hub_linux_user, f"mkdir -p {data_dir}/inbox {data_dir}/outbox {data_dir}/logs")

    # Write CLAUDE.md from hub template
    claude_md_path = hub / "CLAUDE.md"
    if _HUB_TEMPLATE_PATH.exists():
        claude_md_path.write_text(_HUB_TEMPLATE_PATH.read_text())
        if hub_linux_user:
            subprocess.run(["chown", f"{hub_linux_user}:", str(claude_md_path)],
                           capture_output=True, text=True)

    if not LOCAL_MODE:
        # Ensure delta-config dirs are writable by hub user (root writes inbox, hub reads/deletes)
        for d in [data_dir, data_dir / "inbox", data_dir / "outbox", data_dir / "logs"]:
            os.chmod(str(d), 0o777)

        # Create settings.json in shared /root/.claude so ALL users skip the
        # --dangerously-skip-permissions TUI prompt (symlinked from each user's home)
        root_settings = Path("/root/.claude/settings.json")
        if not root_settings.exists():
            root_settings.write_text(json.dumps(
                {"skipDangerousModePermissionPrompt": True}, indent=2
            ))
            os.chmod(str(root_settings), 0o666)
            logger.info("Created /root/.claude/settings.json with skipDangerousModePermissionPrompt")

    # Create tmux session
    create_tmux_session(HUB_TMUX_SESSION)

    # Start Claude Code
    start_claude_code(str(hub), HUB_TMUX_PANE,
                      linux_user=hub_linux_user or None)

    # Start web terminal for the hub
    if not LOCAL_MODE:
        start_ttyd(HUB_NAME, HUB_TMUX_SESSION, HUB_TTYD_PORT)

    # Create bridge (not in registry -- special entry in bridges dict)
    bridge = ProjectBridge(
        name=HUB_NAME,
        data_dir=str(data_dir),
        tmux_lead_pane=HUB_TMUX_PANE,
        nudge_prefix="delta-config/inbox",
    )
    bridges[HUB_NAME] = bridge
    logger.info("Hub initialized")


def _start_hub_watchers() -> None:
    """Start outbox/inbox watchers for the hub with command interception."""
    bridge = bridges.get(HUB_NAME)
    if not bridge:
        return

    loop = asyncio.get_event_loop()

    def _hub_outbox_callback(data: dict) -> None:
        command = data.get("command")

        if command == "onboarding_complete":
            # Personal agent finished onboarding via hub outbox
            project_name = data.get("project_name", data.get("name", ""))
            if project_name:
                asyncio.run_coroutine_threadsafe(
                    _handle_onboarding_complete(project_name, data), loop,
                )
            return

        if command == "linkedin_connect":
            display_name = data.get("user_display_name", "user")
            channel_id = data.get("reply_channel", "") or data.get("channel", "")
            owner = data.get("owner_discord_id", "")
            if channel_id and owner:
                hub_bridge = bridges.get(HUB_NAME)
                asyncio.run_coroutine_threadsafe(
                    _handle_linkedin_connect(
                        HUB_NAME, hub_bridge, channel_id, display_name, owner
                    ),
                    loop,
                )
            return

        if command == "gh_auth_start":
            # Hub or agent requesting GitHub CLI auth
            target_project = data.get("project_name", data.get("name", ""))
            channel_id = data.get("reply_channel", "") or data.get("channel", "")
            if target_project:
                target_bridge = _get_or_create_bridge(target_project)
                if target_bridge and channel_id:
                    asyncio.run_coroutine_threadsafe(
                        _handle_gh_auth_command(target_project, target_bridge, channel_id),
                        loop,
                    )
            return

        if command == "new_project":
            # Hub is requesting a new project
            name = data.get("name", "")
            owner = data.get("owner_discord_id", "")
            reply_channel = data.get("reply_channel", "")
            github_repo = data.get("github_repo", "")
            use_channel = data.get("use_channel", "")
            project_type = data.get("project_type", "standard")
            admin_brief = data.get("admin_brief", "")
            target_user_id = data.get("target_user_id", "")

            async def _provision():
                try:
                    guild = client.guilds[0] if client.guilds else None
                    if use_channel:
                        info = await provision_in_channel(
                            name=name,
                            registry=registry,
                            discord_bot=client,
                            guild=guild,
                            owner_discord_id=owner,
                            channel_id=use_channel,
                            github_repo=github_repo,
                            is_dream_space=True,
                            project_type=project_type,
                            admin_brief=admin_brief,
                        )
                    else:
                        info = await provision(
                            name=name,
                            registry=registry,
                            discord_bot=client,
                            guild=guild,
                            owner_discord_id=owner,
                            github_repo=github_repo,
                            project_type=project_type,
                            admin_brief=admin_brief,
                            target_user_id=target_user_id,
                        )
                    _start_watchers(name)

                    # Send welcome message in the new channel for onboarding projects
                    if project_type == "personal" and info.discord_channel_id:
                        try:
                            new_channel = client.get_channel(int(info.discord_channel_id))
                            if not new_channel:
                                new_channel = await client.fetch_channel(int(info.discord_channel_id))
                            if new_channel:
                                if target_user_id:
                                    welcome = (
                                        f"hey <@{target_user_id}>. i'm Delta, your personal agent. "
                                        f"let's get to know each other."
                                    )
                                else:
                                    welcome = (
                                        "hey. i'm Delta, your personal agent. "
                                        "let's get to know each other."
                                    )
                                await new_channel.send(welcome)
                        except Exception as e:
                            logger.warning(f"Could not send welcome in {name}: {e}")

                    # Write confirmation back to hub inbox
                    hub_bridge = bridges.get(HUB_NAME)
                    if hub_bridge:
                        confirm_text = (
                            f"Project **{name}** created. "
                            f"Channel: <#{info.discord_channel_id}>. "
                            f"Tell the user."
                        )
                        msg_id = hub_bridge.write_inbox(
                            reply_channel, "delta:system", confirm_text
                        )
                        if hub_bridge.is_project_active():
                            try:
                                hub_bridge.send_to_lead(msg_id)
                            except Exception:
                                pass
                except Exception as e:
                    logger.error(f"Hub provision failed: {e}")
                    hub_bridge = bridges.get(HUB_NAME)
                    if hub_bridge:
                        msg_id = hub_bridge.write_inbox(
                            reply_channel, "delta:system",
                            f"Could not create project {name}: {e}"
                        )
                        if hub_bridge.is_project_active():
                            try:
                                hub_bridge.send_to_lead(msg_id)
                            except Exception:
                                pass

            asyncio.run_coroutine_threadsafe(_provision(), loop)
            return

        if command == "forward":
            # Forward a message to another project
            target = data.get("target_project", "")
            text = data.get("text", "")
            user = data.get("user", "")
            reply_channel = data.get("reply_channel", "")
            source_project = data.get("source_project", "")

            # Access control: source and target must share the same owner
            # Hub (__hub__) can forward to any project (it's the orchestrator)
            if source_project and source_project != HUB_NAME:
                source_info = registry.get(source_project)
                target_info = registry.get(target)
                if (source_info and target_info
                        and source_info.owner_discord_id != target_info.owner_discord_id):
                    logger.warning(f"Forward blocked: {source_project} -> {target} (different owners)")
                    return

            target_bridge = _get_or_create_bridge(target)
            if target_bridge:
                info = registry.get(target)
                ch = info.discord_channel_id if info else reply_channel
                msg_id = target_bridge.write_inbox(ch, user, text)
                target_bridge.touch_activity()
                if target_bridge.is_project_active():
                    try:
                        target_bridge.send_to_lead(msg_id)
                    except Exception as e:
                        logger.warning(f"Forward nudge to {target} failed: {e}")
            return

        # Normal outbox message -- send to Discord
        channel_id = data.get("channel")
        if not channel_id:
            return
        _stop_typing(channel_id)
        channel = client.get_channel(int(channel_id))

        async def _send():
            nonlocal channel
            if not channel:
                try:
                    channel = await client.fetch_channel(int(channel_id))
                except Exception:
                    logger.warning(f"[outbox:hub] Channel {channel_id} not found")
                    return
            try:
                hub_dir = str(_hub_dir())
                files = _resolve_files(data, hub_dir)
                embed_data = data.get("embed")
                if embed_data:
                    embed = discord.Embed(
                        title=embed_data.get("title", ""),
                        description=embed_data.get("description", ""),
                        color=embed_data.get("color", 0x2ecc71),
                    )
                    for field in embed_data.get("fields", []):
                        embed.add_field(
                            name=field.get("name", ""),
                            value=field.get("value", ""),
                            inline=field.get("inline", False),
                        )
                    if embed_data.get("footer"):
                        embed.set_footer(text=embed_data["footer"])
                    text = _extract_text(data)
                    await channel.send(content=text or None, embed=embed,
                                       files=files or discord.utils.MISSING)
                else:
                    await channel.send(_extract_text(data) or "(empty)",
                                       files=files or discord.utils.MISSING)
            except Exception as e:
                logger.warning(f"[outbox:hub] Discord send failed: {e}")

        asyncio.run_coroutine_threadsafe(_send(), loop)

    t = Thread(target=bridge.watch_outbox, args=(_hub_outbox_callback,), daemon=True)
    t.start()

    t2 = Thread(target=bridge.watch_inbox, daemon=True)
    t2.start()

    logger.info("Hub watchers started")


def _read_project_seed(project_dir: str, max_chars: int = 500) -> str:
    """Read first max_chars of SEED.md from a project directory."""
    seed_path = Path(project_dir) / "SEED.md"
    if not seed_path.exists():
        return ""
    try:
        return seed_path.read_text()[:max_chars]
    except OSError:
        return ""


def _read_project_schedule(project_dir: str, max_tasks: int = 15) -> list[dict]:
    """Read schedule tasks, returning up to max_tasks with status and truncated description."""
    schedule_path = Path(project_dir) / "delta-config" / "schedule.json"
    if not schedule_path.exists():
        return []
    try:
        data = json.loads(schedule_path.read_text())
        tasks = data.get("tasks", [])[:max_tasks]
        result = []
        for t in tasks:
            entry = {
                "status": t.get("status", "?"),
                "what": (t.get("what") or t.get("name") or t.get("description") or "")[:100],
            }
            # Include schedule timing for recurring tasks
            if t.get("schedule"):
                entry["schedule"] = t["schedule"]
            if t.get("time"):
                entry["time"] = t["time"]
            if t.get("timezone"):
                entry["timezone"] = t["timezone"]
            result.append(entry)
        return result
    except (json.JSONDecodeError, OSError):
        return []


def _read_project_recent_logs(project_dir: str, max_entries: int = 10) -> list[dict]:
    """Read last max_entries log lines from today/yesterday."""
    logs_dir = Path(project_dir) / "delta-config" / "logs"
    if not logs_dir.exists():
        return []
    entries = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    for date_str in [yesterday, today]:
        log_file = logs_dir / f"{date_str}.jsonl"
        if not log_file.exists():
            continue
        try:
            for line in log_file.read_text().strip().split("\n"):
                if line:
                    e = json.loads(line)
                    entries.append({
                        "ts": e.get("ts", ""),
                        "direction": e.get("direction", ""),
                        "user": e.get("user", ""),
                        "text": e.get("text", "")[:200],
                    })
        except (json.JSONDecodeError, OSError):
            pass
    return entries[-max_entries:]


def _read_project_recent_commits(project_dir: str, max_commits: int = 5) -> list[str]:
    """Read last max_commits git commit subjects from a project directory."""
    try:
        result = subprocess.run(
            ["git", "-C", project_dir, "log", "--oneline", f"-{max_commits}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    except (subprocess.TimeoutExpired, OSError):
        return []


def _read_project_claude_md(project_dir: str, max_chars: int = 3000) -> str:
    """Read first max_chars of CLAUDE.md from a project directory."""
    claude_md_path = Path(project_dir) / "CLAUDE.md"
    if not claude_md_path.exists():
        return ""
    try:
        return claude_md_path.read_text()[:max_chars]
    except OSError:
        return ""


def _read_project_memory_files(project_dir: str, max_chars: int = 2000) -> str:
    """Read all .md files from memory/ dir, concatenated with headers.

    Returns a string like:
        ## profile.md
        <content>

        ## time-architecture.md
        <content>
    Truncated to max_chars total.
    """
    memory_dir = Path(project_dir) / "memory"
    if not memory_dir.is_dir():
        return ""
    parts = []
    total = 0
    for md_file in sorted(memory_dir.glob("*.md")):
        try:
            header = f"## {md_file.name}\n"
            content = md_file.read_text()
            chunk = header + content + "\n"
            if total + len(chunk) > max_chars:
                remaining = max_chars - total
                if remaining > len(header) + 50:  # worth including partial
                    parts.append(chunk[:remaining])
                break
            parts.append(chunk)
            total += len(chunk)
        except OSError:
            continue
    return "".join(parts)


# Snapshot depth limits
_SNAPSHOT_LIMITS = {
    "standard": {
        "seed_chars": 500,
        "schedule_tasks": 15,
        "schedule_chars": 100,
        "log_entries": 10,
        "log_chars": 200,
        "commits": 5,
    },
    "deep": {
        "seed_chars": 1500,
        "schedule_tasks": 15,
        "schedule_chars": 100,
        "log_entries": 20,
        "log_chars": 400,
        "commits": 10,
    },
}


def _build_enriched_snapshot(project_dir: str, depth: str = "standard") -> dict:
    """Build snapshot data for a project at the given depth.

    depth="standard": current limits (for hub)
    depth="deep": enriched limits (for persistent agents) with CLAUDE.md and memory
    """
    limits = _SNAPSHOT_LIMITS.get(depth, _SNAPSHOT_LIMITS["standard"])
    result = {}

    seed = _read_project_seed(project_dir, max_chars=limits["seed_chars"])
    if seed:
        result["seed"] = seed

    schedule = _read_project_schedule(project_dir, max_tasks=limits["schedule_tasks"])
    if schedule:
        # Re-truncate what field to the depth-appropriate limit
        for t in schedule:
            if "what" in t:
                t["what"] = t["what"][:limits["schedule_chars"]]
        result["schedule"] = schedule

    recent_logs = _read_project_recent_logs(project_dir, max_entries=limits["log_entries"])
    if recent_logs:
        for entry in recent_logs:
            if "text" in entry:
                entry["text"] = entry["text"][:limits["log_chars"]]
        result["recent_logs"] = recent_logs

    recent_commits = _read_project_recent_commits(project_dir, max_commits=limits["commits"])
    if recent_commits:
        result["recent_commits"] = recent_commits

    if depth == "deep":
        claude_md = _read_project_claude_md(project_dir)
        if claude_md:
            result["claude_md"] = claude_md
        memory_summary = _read_project_memory_files(project_dir)
        if memory_summary:
            result["memory_summary"] = memory_summary

    return result


async def _hub_snapshot_loop():
    """Write a registry snapshot to the hub's delta-config every 60s."""
    global _auth_alert_sent, _auth_alert_time
    await client.wait_until_ready()

    while not client.is_closed():
        try:
            projects = []
            for name in registry.list_projects():
                info = registry.get(name)
                if not info:
                    continue
                if info.status == "active":
                    health = get_project_health(info.tmux_lead_pane)
                    health_str = "running" if health["claude_running"] else "stopped"
                else:
                    health_str = info.status

                project_data = {
                    "name": info.name,
                    "status": info.status,
                    "owner_discord_id": info.owner_discord_id,
                    "discord_channel_id": info.discord_channel_id,
                    "github_repo": info.github_repo,
                    "last_activity": info.last_activity,
                    "health": health_str,
                    "ttyd_port": getattr(info, "ttyd_port", 0),
                    "project_type": getattr(info, "project_type", "standard"),
                }

                if DELTA_SERVER_HOST and getattr(info, "ttyd_port", 0):
                    project_data["ttyd_url"] = f"http://{DELTA_SERVER_HOST}:{info.ttyd_port}"

                # Enrich with project internals (read as root)
                project_dir = info.project_dir
                if project_dir:
                    enriched = _build_enriched_snapshot(project_dir, depth="standard")
                    project_data.update(enriched)

                    # Read onboarding state for personal agent projects
                    if getattr(info, "project_type", "standard") in ("personal", "personal_dm"):
                        onboarding_state_path = Path(project_dir) / "memory" / "onboarding-state.json"
                        if onboarding_state_path.exists():
                            try:
                                onboarding_state = json.loads(onboarding_state_path.read_text())
                                project_data["onboarding_state"] = onboarding_state
                            except (json.JSONDecodeError, OSError):
                                pass

                projects.append(project_data)

            # Include the hub (DM router) as an instance
            hub_bridge = bridges.get(HUB_NAME)
            hub_health = "unknown"
            if hub_bridge:
                hub_health = "running" if hub_bridge.is_project_active() else "stopped"
            hub_data = {
                "name": "__hub__",
                "status": "active",
                "health": hub_health,
                "owner_discord_id": "",
                "discord_channel_id": "",
                "github_repo": "",
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "ttyd_port": HUB_TTYD_PORT if not LOCAL_MODE else 0,
                "is_hub": True,
                "tmux_session": HUB_TMUX_SESSION,
                "tmux_lead_pane": HUB_TMUX_PANE,
                "project_dir": str(_hub_dir()),
            }
            hub_logs = _read_project_recent_logs(str(_hub_dir()))
            if hub_logs:
                hub_data["recent_logs"] = hub_logs

            snapshot = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "projects": projects,
                "hub": hub_data,
            }

            snapshot_path = _hub_dir() / "delta-config" / "registry-snapshot.json"
            snapshot_path.write_text(json.dumps(snapshot, indent=2))
            # Ensure hub user can read the snapshot (written by root on server)
            os.chmod(str(snapshot_path), 0o644)

            # Write per-user snapshots for persistent agents
            for name in registry.list_projects():
                info = registry.get(name)
                if not info or info.project_type != "persistent":
                    continue
                owner = info.owner_discord_id
                if not owner:
                    continue
                # Build deep-enriched copies of user's projects
                user_projects = []
                for p in projects:
                    if p.get("owner_discord_id") != owner:
                        continue
                    p_info = registry.get(p["name"])
                    p_dir = p_info.project_dir if p_info else ""
                    if p_dir:
                        deep = _build_enriched_snapshot(p_dir, depth="deep")
                        enriched_p = dict(p)
                        enriched_p.update(deep)
                        user_projects.append(enriched_p)
                    else:
                        user_projects.append(p)
                user_snapshot = {
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "projects": user_projects,
                }
                try:
                    user_snapshot_path = Path(info.project_dir) / "delta-config" / "registry-snapshot.json"
                    user_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                    user_snapshot_path.write_text(json.dumps(user_snapshot, indent=2))
                    if info.linux_user:
                        os.chmod(str(user_snapshot_path), 0o644)
                except OSError as e:
                    logger.warning(f"Could not write snapshot for {name}: {e}")

            # Health check: restart hub Claude Code if it died or is stuck
            hub_bridge = bridges.get(HUB_NAME)
            if hub_bridge:
                hub_alive = hub_bridge.is_project_active()
                hub_pending = hub_bridge.pending_inbox_count()
                if not hub_alive:
                    logger.warning("Hub Claude Code not running, restarting...")
                    hub_linux_user = "" if LOCAL_MODE else "proj-delta-hub"
                    stop_claude_code(HUB_TMUX_PANE, grace=3)
                    start_claude_code(
                        str(_hub_dir()), HUB_TMUX_PANE,
                        linux_user=hub_linux_user or None,
                    )
                elif hub_pending > 0 and not _auth_alert_sent and hub_bridge._is_pane_at_prompt():
                    # Hub has messages but is sitting at prompt -- batch re-nudge (skip if auth down)
                    try:
                        pending = sorted(hub_bridge.inbox_dir.glob("*.json"))[:5]
                        for msg_file in pending:
                            try:
                                hub_bridge.send_to_lead(msg_file.stem)
                            except Exception:
                                break
                        logger.info(f"Hub pulse: re-nudged {len(pending)} of {hub_pending} pending")
                    except Exception as e:
                        logger.warning(f"Hub pulse re-nudge failed: {e}")

                # Auth health check: detect expired OAuth tokens
                if hub_alive:
                    auth_err = hub_bridge.check_auth_error()
                    if auth_err:
                        now = time.time()
                        if not _auth_alert_sent or (now - _auth_alert_time > _AUTH_ALERT_COOLDOWN):
                            logger.error(f"Auth failure detected: {auth_err}")
                            if ADMIN_DISCORD_ID:
                                try:
                                    admin_user = await client.fetch_user(int(ADMIN_DISCORD_ID))
                                    dm_channel = await admin_user.create_dm()
                                    await dm_channel.send(
                                        f"**Delta auth alert:** Claude Code auth has expired on the server.\n"
                                        f"All agents are down until you re-auth.\n"
                                        f"Run `claude /login` on the server to fix.\n\n"
                                        f"Error: `{auth_err[:150]}`"
                                    )
                                    logger.info("Admin DM sent about auth expiry")
                                except Exception as e:
                                    logger.warning(f"Could not DM admin about auth failure: {e}")
                            _auth_alert_sent = True
                            _auth_alert_time = now

                        # Don't re-nudge hub when auth is down -- pointless
                    elif _auth_alert_sent:
                        logger.info("Auth appears restored, resetting alert flag")
                        _auth_alert_sent = False
                        _auth_alert_time = 0
                        _auth_alert_sent = False

        except Exception as e:
            logger.warning(f"Hub snapshot loop error: {e}")

        await asyncio.sleep(60)


# -- Reporting daemon --------------------------------------------------------

def _is_schedule_time(time_str: str, tz_name: str, freq: str = "daily") -> bool:
    """Check if now matches a scheduled time (within 5-minute window)."""
    try:
        hour, minute = map(int, time_str.split(":"))
        tz = ZoneInfo(tz_name)
    except (ValueError, KeyError):
        return False

    now = datetime.now(tz)
    diff = now.minute - minute
    if now.hour == hour and 0 <= diff < 5:
        if freq == "daily" or (freq == "weekly" and now.weekday() == 0):
            return True
    return False


def _get_schedule_data(project_name: str) -> dict | None:
    """Read schedule.json for a project (works even when hibernated)."""
    info = registry.get(project_name)
    if not info:
        return None
    data_dir = Path(info.project_dir) / "delta-config"
    schedule_file = data_dir / "schedule.json"
    if not schedule_file.exists():
        return None
    try:
        return json.loads(schedule_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None


async def _wake_and_get_bridge(project_name: str) -> ProjectBridge | None:
    """Restore a hibernated project and return its bridge, ready to use."""
    info = registry.get(project_name)
    if not info:
        return None

    if info.status == "hibernated":
        logger.info(f"Waking {project_name} for scheduled task")
        restore(project_name, registry)
        _start_watchers(project_name)
        await asyncio.sleep(8)  # Wait for Claude Code to boot
        # Verify it actually started
        info = registry.get(project_name)
        if info and not is_claude_running(info.tmux_lead_pane):
            logger.warning(f"Post-boot check failed for {project_name} (scheduled wake)")
            return None

    return _get_or_create_bridge(project_name)


def _load_last_fired() -> dict[str, str]:
    """Load the last_fired dict from disk."""
    try:
        if _LAST_FIRED_PATH.exists():
            return json.loads(_LAST_FIRED_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _save_last_fired(last_fired: dict[str, str]) -> None:
    """Persist the last_fired dict to disk."""
    try:
        _LAST_FIRED_PATH.write_text(json.dumps(last_fired, indent=2))
    except OSError as e:
        logger.warning(f"Could not save last_fired: {e}")


async def _reporting_loop():
    """Check all projects' reporting + morning_trip schedules and nudge when it's time."""
    await client.wait_until_ready()
    # Track last nudge per project per type per day to avoid duplicates
    last_fired = _load_last_fired()

    while not client.is_closed():
        try:
            for name in list(registry.list_projects()):
                data = _get_schedule_data(name)
                if not data:
                    continue

                # Skip scheduled nudges for projects created less than 1 hour ago
                info = registry.get(name)
                if info and info.created_at:
                    try:
                        created = datetime.fromisoformat(info.created_at)
                        if datetime.now(timezone.utc) - created < timedelta(hours=1):
                            continue
                    except (ValueError, TypeError):
                        pass

                # -- Daily report --
                reporting = data.get("reporting")
                if reporting:
                    freq = reporting.get("frequency", "daily")
                    report_time = reporting.get("time", "09:00")
                    tz_name = reporting.get("timezone", "UTC")
                    tz = ZoneInfo(tz_name) if tz_name != "UTC" else timezone.utc
                    today_key = datetime.now(tz).strftime("%Y-%m-%d")
                    report_key = f"{name}:report:{today_key}"

                    if report_key not in last_fired and _is_schedule_time(report_time, tz_name, freq):
                        last_fired[report_key] = datetime.now(timezone.utc).isoformat()
                        _save_last_fired(last_fired)
                        bridge = await _wake_and_get_bridge(name)
                        if bridge:
                            _send_report_nudge(name, bridge, reporting)

                # -- Morning trip --
                morning = data.get("morning_trip")
                if morning and morning.get("enabled"):
                    trip_time = morning.get("time", "09:00")
                    tz_name = morning.get("timezone", "UTC")
                    tz = ZoneInfo(tz_name) if tz_name != "UTC" else timezone.utc
                    today_key = datetime.now(tz).strftime("%Y-%m-%d")
                    trip_key = f"{name}:morning_trip:{today_key}"

                    if trip_key not in last_fired and _is_schedule_time(trip_time, tz_name):
                        last_fired[trip_key] = datetime.now(timezone.utc).isoformat()
                        _save_last_fired(last_fired)
                        bridge = await _wake_and_get_bridge(name)
                        if bridge:
                            _send_morning_trip_nudge(name, bridge, morning, data.get("project", {}))

        except Exception as e:
            logger.warning(f"Reporting loop error: {e}")

        await asyncio.sleep(60)  # Check every minute


# -- General-purpose schedule fire loop --------------------------------------

def _should_fire_task(task: dict, now: datetime) -> bool:
    """Check if a scheduled task should fire right now.

    Supports two modes:
    - fire_at: ISO timestamp for one-shot triggers. Fires once when now >= fire_at.
    - schedule + time + timezone: recurring daily/weekly. Fires within a 3-minute window.
    """
    # One-shot: fire_at mode
    fire_at = task.get("fire_at")
    if fire_at:
        try:
            target = datetime.fromisoformat(fire_at)
            if target.tzinfo is None:
                target = target.replace(tzinfo=timezone.utc)
            return now >= target
        except (ValueError, TypeError):
            return False

    # Recurring: schedule + time + timezone
    schedule = task.get("schedule", "")
    time_str = task.get("time", "")
    tz_name = task.get("timezone", "UTC")
    if not schedule or not time_str:
        return False

    try:
        hour, minute = map(int, time_str.split(":"))
        tz = ZoneInfo(tz_name)
    except (ValueError, KeyError):
        return False

    local_now = now.astimezone(tz)
    diff_minutes = (local_now.hour * 60 + local_now.minute) - (hour * 60 + minute)

    if not (0 <= diff_minutes < 3):
        return False

    weekday = local_now.weekday()  # 0=Mon, 4=Fri, 5=Sat, 6=Sun
    day_names = {
        "mondays": 0, "tuesdays": 1, "wednesdays": 2, "thursdays": 3,
        "fridays": 4, "saturdays": 5, "sundays": 6,
        "mon": 0, "tue": 1, "wed": 2, "thu": 3,
        "fri": 4, "sat": 5, "sun": 6,
    }

    if schedule == "daily":
        return True
    elif schedule == "weekdays":
        return weekday < 5
    elif schedule == "weekends":
        return weekday >= 5
    elif schedule == "weekly":
        return weekday == 0
    elif schedule in day_names:
        return weekday == day_names[schedule]
    elif "," in schedule:
        # Comma-separated days: "wed,sat"
        return any(weekday == day_names.get(d.strip().lower(), -1) for d in schedule.split(","))
    return False


def _update_last_fired_in_schedule(project_name: str, task_id: str) -> None:
    """Update last_fired timestamp for a task in the project's schedule.json."""
    info = registry.get(project_name)
    if not info:
        return
    data_dir = Path(info.project_dir) / "delta-config"
    schedule_file = data_dir / "schedule.json"
    if not schedule_file.exists():
        return
    try:
        data = json.loads(schedule_file.read_text())
        for task in data.get("tasks", []):
            if task.get("id") == task_id:
                task["last_fired"] = datetime.now(timezone.utc).isoformat()
                break
        schedule_file.write_text(json.dumps(data, indent=2))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not update last_fired for {project_name}/{task_id}: {e}")


async def _schedule_fire_loop():
    """Fire scheduled tasks by writing inbox messages at the right time.

    Reads the 'tasks' array from each project's schedule.json. When a task
    is due, writes an inbox message so the agent processes it like any other
    user request. Delta IS the scheduler -- agents just respond to inbox.

    Polls every 30s for sub-60s delivery accuracy.
    """
    await client.wait_until_ready()
    # Track which tasks have been fired today to prevent double-firing
    fired_today: dict[str, str] = {}  # "project:task_id:date" -> iso timestamp

    while not client.is_closed():
        try:
            now = datetime.now(timezone.utc)

            for name in list(registry.list_projects()):
                data = _get_schedule_data(name)
                if not data:
                    continue

                tasks = data.get("tasks", [])
                for task in tasks:
                    task_id = task.get("id", "")
                    if not task_id:
                        continue
                    description = task.get("description", "") or task.get("what", "")
                    if not description:
                        continue
                    # Skip completed/done tasks
                    task_status = task.get("status", "")
                    if task_status in ("done", "completed"):
                        continue

                    # Build dedup key
                    tz_name = task.get("timezone", "UTC")
                    try:
                        tz = ZoneInfo(tz_name)
                    except KeyError:
                        tz = timezone.utc
                    local_date = now.astimezone(tz).strftime("%Y-%m-%d")

                    # For fire_at tasks, use the fire_at value as key (no date dedup)
                    if task.get("fire_at"):
                        dedup_key = f"{name}:{task_id}:fire_at:{task.get('fire_at')}"
                    else:
                        dedup_key = f"{name}:{task_id}:{local_date}"

                    if dedup_key in fired_today:
                        continue

                    # Check last_fired to avoid re-firing after restart
                    last_fired_str = task.get("last_fired", "")
                    if last_fired_str and not task.get("fire_at"):
                        try:
                            last_fired_dt = datetime.fromisoformat(last_fired_str)
                            if last_fired_dt.tzinfo is None:
                                last_fired_dt = last_fired_dt.replace(tzinfo=timezone.utc)
                            local_last = last_fired_dt.astimezone(tz)
                            if local_last.strftime("%Y-%m-%d") == local_date:
                                fired_today[dedup_key] = last_fired_str
                                continue
                        except (ValueError, TypeError):
                            pass

                    if not _should_fire_task(task, now):
                        continue

                    # Fire the task
                    logger.info(f"Firing scheduled task {task_id} for {name}")
                    bridge = await _wake_and_get_bridge(name)
                    if not bridge:
                        logger.warning(f"Could not get bridge for {name} to fire {task_id}")
                        continue

                    info = registry.get(name)
                    channel_id = info.discord_channel_id if info else ""
                    bridge.touch_activity()

                    inbox_text = f"Scheduled task: {description}"
                    msg_id = bridge.write_inbox(
                        channel_id, "delta:schedule", inbox_text
                    )
                    try:
                        bridge.send_to_lead(msg_id)
                        fired_today[dedup_key] = now.isoformat()
                        _update_last_fired_in_schedule(name, task_id)
                        logger.info(f"Scheduled task {task_id} fired for {name}")
                    except Exception as e:
                        logger.warning(f"Failed to fire {task_id} for {name}: {e}")

                    # For fire_at tasks, remove them after firing (one-shot)
                    if task.get("fire_at"):
                        _remove_fired_task(name, task_id)

            # Clean old entries from fired_today (keep only today's)
            today_str = now.strftime("%Y-%m-%d")
            stale = [k for k in fired_today if not k.endswith(today_str) and ":fire_at:" not in k]
            for k in stale:
                del fired_today[k]

        except Exception as e:
            logger.warning(f"Schedule fire loop error: {e}")

        await asyncio.sleep(30)


def _remove_fired_task(project_name: str, task_id: str) -> None:
    """Remove a one-shot (fire_at) task from schedule.json after it fires."""
    info = registry.get(project_name)
    if not info:
        return
    data_dir = Path(info.project_dir) / "delta-config"
    schedule_file = data_dir / "schedule.json"
    if not schedule_file.exists():
        return
    try:
        data = json.loads(schedule_file.read_text())
        tasks = data.get("tasks", [])
        data["tasks"] = [t for t in tasks if t.get("id") != task_id]
        schedule_file.write_text(json.dumps(data, indent=2))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not remove fired task {project_name}/{task_id}: {e}")


def _send_report_nudge(project_name: str, bridge: ProjectBridge,
                       reporting: dict) -> None:
    """Nudge a project's Claude Code to send its report."""
    if not bridge.is_project_active():
        return

    style = reporting.get("style", "calm")
    what_matters = reporting.get("what_matters", "progress and what's next")

    nudge = (
        f"Time for your report. Style: {style}. "
        f"Focus on: {what_matters}. "
        f"Use a Discord embed with color. Write the report to your outbox as a JSON file "
        f"with an 'embed' field containing title, description, color (hex int), and fields. "
        f"Make it feel like everything is handled. The user should read it and feel peace."
    )

    info = registry.get(project_name)
    channel_id = info.discord_channel_id if info else ""
    bridge.touch_activity()  # prevent resource manager from hibernating mid-work
    msg_id = bridge.write_inbox(channel_id, "delta:reporting", nudge)
    try:
        bridge.send_to_lead(msg_id)
        logger.info(f"Report nudge sent to {project_name}")
    except Exception as e:
        logger.warning(f"Report nudge to {project_name} failed: {e}")


def _send_morning_trip_nudge(project_name: str, bridge: ProjectBridge,
                             morning: dict, project_meta: dict) -> None:
    """Nudge a project's Claude Code to deliver its morning trip."""
    if not bridge.is_project_active():
        return

    philosophy = morning.get("philosophy", "Show something new. Push the project forward.")
    anchors = morning.get("integrity_anchors", [])
    anchors_str = " | ".join(anchors) if anchors else ""

    project_name_display = project_meta.get("name", project_name)
    core_idea = project_meta.get("core_idea", "")

    nudge = (
        f"Morning trip time. This is your daily moment to push {project_name_display} forward. "
        f"Philosophy: {philosophy} "
    )
    if anchors_str:
        nudge += f"Integrity anchors: {anchors_str}. "
    if core_idea:
        nudge += f"Core idea: {core_idea}. "
    nudge += (
        "Build or prototype something real, then show it. "
        "Write to your outbox -- a Discord embed with color works well. "
        "Make the user want to open the app."
    )

    info = registry.get(project_name)
    channel_id = info.discord_channel_id if info else ""
    bridge.touch_activity()  # prevent resource manager from hibernating mid-work
    msg_id = bridge.write_inbox(channel_id, "delta:morning_trip", nudge)
    try:
        bridge.send_to_lead(msg_id)
        logger.info(f"Morning trip nudge sent to {project_name}")
    except Exception as e:
        logger.warning(f"Morning trip nudge to {project_name} failed: {e}")


# -- Silence nudge -----------------------------------------------------------

_SILENCE_NUDGE_TEXT = (
    "SYSTEM CHECK: If you have already sent a response to the user's last "
    "message, ignore this completely. If you have NOT responded yet, write "
    "a one-line progress update to delta-config/outbox/ describing WHAT you "
    "are seeing or doing right now. Example: '412 contacts loaded, building "
    "the campaign breakdown.' NOT 'still working on it.' Be specific. "
    "Do NOT send a duplicate 'done' message."
)

# Per-project nudge state: tracks count, timing, and which inbox message we're nudging for
_nudge_state: dict[str, dict] = {}


async def _silence_nudge_loop():
    """Nudge agents that go silent after receiving a user message.

    Repeating nudge with anti-stacking: only nudges when the agent is at
    the Claude Code prompt (not mid-turn). Caps at 5 nudges per user message
    with 25s cooldown between nudges per project.
    """
    await client.wait_until_ready()

    while not client.is_closed():
        try:
            for name in list(registry.list_projects()):
                info = registry.get(name)
                if not info or info.status != "active":
                    continue
                bridge = bridges.get(name)
                if not bridge:
                    continue

                # Initialize nudge state for this project
                if name not in _nudge_state:
                    _nudge_state[name] = {"count": 0, "last_nudge": 0.0, "inbox_time": 0.0,
                                          "queued_nudge": False}
                state = _nudge_state[name]

                # Reset counter when a new user message arrives
                if bridge.last_inbox_time != state["inbox_time"]:
                    state["count"] = 0
                    state["last_nudge"] = 0.0
                    state["inbox_time"] = bridge.last_inbox_time
                    state["queued_nudge"] = False

                if not bridge.check_silence(timeout=25):
                    continue
                # Skip nudge if hooks are providing progress updates
                if bridge.has_recent_progress(window=30):
                    continue
                if not bridge.is_project_active():
                    continue

                # Cap: max 5 nudges per user message
                if state["count"] >= 5:
                    continue

                # Cooldown: at least 25s between nudges
                now = time.time()
                if now - state["last_nudge"] < 25:
                    continue

                # Anti-stacking: allow 1 queued nudge while mid-turn
                at_prompt = bridge._is_pane_at_prompt()
                if not at_prompt:
                    if state.get("queued_nudge", False):
                        continue  # already have one queued, don't stack
                else:
                    state["queued_nudge"] = False

                try:
                    from delta.lifecycle import nudge_lead
                    nudge_lead(bridge.tmux_lead_pane, _SILENCE_NUDGE_TEXT)
                    state["count"] += 1
                    state["last_nudge"] = now
                    if not at_prompt:
                        state["queued_nudge"] = True
                    logger.info(f"Silence nudge #{state['count']} sent to {name} (at_prompt={at_prompt})")
                except Exception as e:
                    logger.warning(f"Silence nudge to {name} failed: {e}")
        except Exception as e:
            logger.warning(f"Silence nudge loop error: {e}")

        await asyncio.sleep(15)


# -- Restore active projects on startup --------------------------------------

def _restore_active_projects() -> int:
    """Recreate tmux sessions and Claude Code for active projects after restart.

    After a systemd service restart, tmux sessions are gone but the registry
    still lists projects as active. This function detects that and restores them.
    Also ensures ttyd is running for active projects.
    Returns the number of projects restored.
    """
    restored = 0
    for name in registry.list_projects():
        info = registry.get(name)
        if not info or info.status != "active":
            continue

        session_alive = is_session_alive(info.tmux_session)
        claude_running = is_claude_running(info.tmux_lead_pane)

        if session_alive and claude_running:
            # Ensure ttyd is running even if project was already up
            if not info.ttyd_port:
                port = _allocate_port(registry)
                if start_ttyd(name, info.tmux_session, port):
                    registry.update(name, ttyd_port=port)
                    logger.info(f"Started ttyd for already-running {name} on port {port}")
            logger.info(f"Project {name} already running, skipping restore")
            continue

        logger.info(f"Restoring project {name} (session={session_alive}, claude={claude_running})")

        if not session_alive:
            create_tmux_session(info.tmux_session)

        if not is_claude_running(info.tmux_lead_pane):
            start_claude_code(
                info.project_dir, info.tmux_lead_pane,
                linux_user=info.linux_user or None,
            )

        # Start web terminal
        port = info.ttyd_port or _allocate_port(registry)
        if start_ttyd(name, info.tmux_session, port):
            if not info.ttyd_port:
                registry.update(name, ttyd_port=port)

        restored += 1

    return restored


# -- Discord event handlers --------------------------------------------------

@client.event
async def on_ready():
    logger.info(f"Delta connected as {client.user}")
    logger.info(f"Projects: {registry.list_projects()}")

    # Restore active projects whose tmux sessions died (e.g. after service restart)
    restored = _restore_active_projects()
    if restored:
        logger.info(f"Restored {restored} active projects")

    for name in registry.list_projects():
        info = registry.get(name)
        if info and info.status == "hibernated":
            logger.info(f"Skipping hibernated project {name}")
            continue
        _start_watchers(name)

    # Initialize hub orchestrator
    _init_hub()
    _start_hub_watchers()
    client.loop.create_task(_hub_snapshot_loop())

    # Start reporting daemon
    client.loop.create_task(_reporting_loop())

    # Start silence nudge loop (pokes agents that go dark)
    client.loop.create_task(_silence_nudge_loop())

    # Start general-purpose schedule fire loop (fires tasks from schedule.json)
    client.loop.create_task(_schedule_fire_loop())

    # Start resource manager (hibernates idle projects)
    client.loop.create_task(resource_manager_loop(client, registry, bridges))


# Lock per user to prevent double-provisioning when two DMs arrive fast
_dm_provision_locks: dict[str, asyncio.Lock] = {}


async def _auto_provision_personal_agent(message, channel_id, user_id, text, attachments_data):
    """Auto-provision a personal agent for a new DM user.

    Sends an instant greeting, provisions in background, then queues the
    first message for the new agent. Next DM will route normally.
    """
    lock = _dm_provision_locks.setdefault(user_id, asyncio.Lock())
    async with lock:
        # Double-check: another DM may have triggered provisioning while waiting
        personal = registry.find_personal_by_owner(user_id)
        if personal:
            await _route_dm_to_persistent(personal, message, channel_id, user_id, text, attachments_data)
            return

        # Instant greeting (user sees this in <1s while provisioning happens)
        await message.channel.send(
            "hey. i'm delta, your personal agent. i build things, manage projects, "
            "handle outreach, create docs, deploy apps, keep track of your schedule. "
            "whatever's taking up your time, just tell me and i'll take it off your plate."
        )

        # Derive project name from display name
        display_name = message.author.display_name or message.author.name
        slug = re.sub(r"[^a-z0-9]+", "-", display_name.lower()).strip("-")[:20]
        project_name = f"personal-{slug}"

        # Ensure unique name
        if registry.get(project_name):
            project_name = f"personal-{slug}-{user_id[-4:]}"

        guild = message.guild or (client.guilds[0] if client.guilds else None)

        try:
            logger.info(f"Auto-provisioning personal agent '{project_name}' for {display_name}")
            info = await provision_in_channel(
                name=project_name,
                registry=registry,
                discord_bot=client,
                guild=guild,
                owner_discord_id=user_id,
                channel_id=channel_id,  # DM channel ID
                project_type="personal_dm",
            )
            logger.info(f"Personal agent '{project_name}' provisioned for {display_name}")

            # Start watchers and queue the first message
            _start_watchers(project_name)
            await asyncio.sleep(5)  # Give Claude Code time to boot

            bridge = _get_or_create_bridge(project_name)
            if bridge:
                msg_id = bridge.write_inbox(
                    channel_id, user_id, text,
                    channel_type="dm",
                    attachments=attachments_data or None,
                )
                if bridge.is_project_active():
                    try:
                        bridge.send_to_lead(msg_id)
                    except Exception as e:
                        logger.warning(f"Nudge to new personal agent failed: {e}")

        except Exception as e:
            logger.error(f"Failed to auto-provision personal agent: {e}")
            await message.channel.send(
                "had trouble setting up. try messaging me again in a moment."
            )


async def _route_dm_to_persistent(project, message, channel_id, user_id, text, attachments_data=None):
    """Route a DM to the user's personal/persistent agent."""
    project_name = project.name
    logger.info(f"DM from {message.author} -> persistent agent {project_name}")

    # Wake from hibernation if needed
    if project.status == "hibernated":
        hub_bridge = bridges.get(HUB_NAME)
        if hub_bridge:
            auth_err = hub_bridge.check_auth_error()
            if auth_err:
                logger.warning(f"Auth failure before waking {project_name}: {auth_err}")
                await message.channel.send(
                    "I'm having trouble connecting right now. The admin has been notified."
                )
                return
        logger.info(f"Restoring hibernated persistent agent '{project_name}' on DM")
        await message.channel.send("waking up, one sec")
        restore(project_name, registry)
        _start_watchers(project_name)
        await asyncio.sleep(8)
        proj_check = registry.get(project_name)
        if proj_check and not is_claude_running(proj_check.tmux_lead_pane):
            logger.warning(f"Post-boot check failed for persistent agent {project_name}")
            await message.channel.send(
                "Had trouble waking up. Try again in a moment."
            )
            return

    bridge = _get_or_create_bridge(project_name)
    if not bridge:
        logger.error(f"Could not create bridge for persistent agent {project_name}, falling back to hub")
        # Fall back to hub
        hub_bridge = bridges.get(HUB_NAME)
        if hub_bridge:
            hub_bridge.touch_activity()
            msg_id = hub_bridge.write_inbox(
                channel_id, user_id, text, channel_type="dm",
                attachments=attachments_data or None,
            )
            _start_typing(message.channel, channel_id)
            if hub_bridge.is_project_active():
                try:
                    hub_bridge.send_to_lead(msg_id)
                except Exception:
                    pass
        return

    # Check auth
    auth_err = bridge.check_auth_error()
    if auth_err:
        logger.warning(f"Auth failure on persistent agent {project_name}: {auth_err}")
        await message.channel.send(
            "I'm having trouble connecting right now. The admin has been notified."
        )
        return

    # Ensure watchers are running
    _start_watchers(project_name)

    bridge.touch_activity()
    msg_id = bridge.write_inbox(
        channel_id, user_id, text, channel_type="dm",
        attachments=attachments_data or None,
    )
    _start_typing(message.channel, channel_id)
    if bridge.is_project_active():
        try:
            bridge.send_to_lead(msg_id)
        except Exception as e:
            logger.warning(f"Nudge to persistent agent {project_name} failed: {e}")
    else:
        logger.warning(f"Persistent agent {project_name} not running, cannot process DM")
        _stop_typing(channel_id)
        await message.channel.send(
            "I'm waking up, give me a sec. Try again in a moment."
        )


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    text = message.content.strip()
    has_attachments = len(message.attachments) > 0
    logger.debug(f"on_message: {message.author} in {message.channel}: {text[:80]}")
    if not text and not has_attachments:
        return

    # Extract attachment metadata for passing through to agents
    attachments_data = []
    if has_attachments:
        for att in message.attachments:
            attachments_data.append({
                "url": att.url,
                "filename": att.filename,
                "size": att.size,
                "content_type": getattr(att, "content_type", None) or "application/octet-stream",
            })
        if not text:
            text = f"[{len(attachments_data)} attachment(s): {', '.join(a['filename'] for a in attachments_data)}]"

    is_dm = isinstance(message.channel, discord.DMChannel)
    channel_id = str(message.channel.id)
    user_id = str(message.author.id)

    # -- DMs: route to personal agent (auto-provision if first contact) --
    if is_dm:
        # Admin commands still handled directly
        cmd_result = commands.parse(text)
        if cmd_result:
            cmd_name, cmd_args = cmd_result
            logger.info(f"Command from {message.author}: {cmd_name}")
            await _handle_command(cmd_name, cmd_args, message)
            return

        # Check if user has a personal or persistent agent
        personal = registry.find_personal_by_owner(user_id)
        if personal:
            await _route_dm_to_persistent(personal, message, channel_id, user_id, text, attachments_data)
            return

        # No personal agent yet -- auto-provision one
        await _auto_provision_personal_agent(message, channel_id, user_id, text, attachments_data)
        return

    # -- LinkedIn onboarding: any user can connect a LinkedIn account --
    if LINKEDIN_ONBOARDING_CHANNEL_ID and channel_id == LINKEDIN_ONBOARDING_CHANNEL_ID:
        if not message.author.bot:
            asyncio.ensure_future(_handle_linkedin_onboarding(message))
        return

    # -- Onboarding intake: admin posts in #seedforth-onboarding --
    if ONBOARDING_CHANNEL_ID and channel_id == ONBOARDING_CHANNEL_ID:
        is_admin = user_id == ADMIN_DISCORD_ID
        if not is_admin:
            return  # Only admins can trigger onboarding

        # Extract target user: filter out @Delta (bot) from mentions
        bot_id = str(client.user.id) if client.user else ""
        real_mentions = [m for m in message.mentions if str(m.id) != bot_id]

        target_user_id_str = ""
        target_display_name = ""

        if real_mentions:
            # A real user was mentioned -- use their display name
            target_user = real_mentions[0]
            target_user_id_str = str(target_user.id)
            target_display_name = target_user.display_name or target_user.name
        else:
            # No real user mentioned -- extract name from text
            # Strip all mentions, strip keywords, grab first capitalized word
            name_text = re.sub(r"<@!?\d+>", "", text).strip()
            name_text = re.sub(
                r"\b(?:onboard|onboarding|start|begin|hey|can you|help me|my friend|my colleague|he\'s|she\'s|they\'re|an?|the)\b",
                "", name_text, flags=re.IGNORECASE,
            ).strip()
            name_text = re.sub(r"^[,\-\s]+", "", name_text).strip()
            # Find first capitalized word (likely a name)
            name_match = re.search(r"\b([A-Z][a-z]+)\b", name_text)
            if name_match:
                target_display_name = name_match.group(1)
            else:
                await message.channel.send(
                    "Who should I onboard? Mention them or include their name. "
                    "Example: `onboard @alex -- runs a consulting firm` or "
                    "`onboard Alex, he's an accountant`"
                )
                return

        # Build slug from display name
        slug_name = re.sub(r"[^a-z0-9]+", "-", target_display_name.lower()).strip("-")[:20]
        project_slug = f"onboarding-{slug_name}"

        # Extract admin brief: strip mentions, keywords, and the target name
        brief_text = re.sub(r"<@!?\d+>", "", text).strip()
        brief_text = re.sub(r"^(?:onboard|start|begin)\s*", "", brief_text, flags=re.IGNORECASE).strip()
        brief_text = re.sub(r"^--?\s*", "", brief_text).strip()
        # Remove the target name from the brief if it appears at the start
        brief_text = re.sub(
            rf"^{re.escape(target_display_name)}\s*[,\-]?\s*",
            "", brief_text, flags=re.IGNORECASE,
        ).strip()

        # Route to hub as a structured onboarding request
        hub_bridge = bridges.get(HUB_NAME)
        if hub_bridge:
            onboard_request = json.dumps({
                "id": f"onboard-{int(time.time())}",
                "channel": channel_id,
                "user": user_id,
                "text": f"Create a personal onboarding project for {target_display_name}. "
                        f"Project name: {project_slug}. "
                        f"Admin brief: {brief_text}",
                "channel_type": "channel",
                "onboarding_request": {
                    "target_user_id": target_user_id_str,
                    "target_user_name": target_display_name,
                    "project_slug": project_slug,
                    "admin_brief": brief_text,
                },
            })
            msg_path = hub_bridge.inbox_dir / f"onboard-{int(time.time())}.json"
            msg_path.write_text(onboard_request)
            if hub_bridge.is_project_active():
                try:
                    hub_bridge.send_to_lead(f"onboard-{int(time.time())}")
                except Exception:
                    pass
            await message.channel.send(
                f"Starting onboarding for {target_display_name}. "
                f"Creating channel #proj-{project_slug}..."
            )
        else:
            await message.channel.send("Hub not ready. Try again in a moment.")
        return

    # -- Channel messages: check if this is a project channel --
    project_name = router.resolve_channel(channel_id)

    if not project_name:
        # Not a project channel. Only respond if @mentioned.
        mentioned = client.user and client.user.mentioned_in(message)
        if not mentioned:
            return

        # Strip the @mention to get the actual command/text
        text = re.sub(r"<@!?\d+>\s*", "", text).strip()
        logger.info(f"[channel:{message.channel}] @mention from {message.author}: {text[:80]}")

        # Check if it's a command first
        if text:
            cmd_result = commands.parse(text)
            if cmd_result:
                cmd_name, cmd_args = cmd_result
                await _handle_command(cmd_name, cmd_args, message)
                return

        # Route @mentions to hub (same as DMs but with channel metadata)
        channel_name = getattr(message.channel, "name", None) or f"channel-{channel_id[-6:]}"

        # Fetch recent channel history so hub has conversation context
        recent_context = []
        try:
            history = message.channel.history(limit=15, before=message)
            async for msg in history:
                recent_context.insert(0, {
                    "author": msg.author.display_name,
                    "content": msg.content[:500],
                    "timestamp": msg.created_at.isoformat(),
                })
        except Exception as e:
            logger.debug(f"Could not fetch channel history: {e}")

        hub_bridge = bridges.get(HUB_NAME)
        if hub_bridge:
            # Check for auth failure before routing
            auth_err = hub_bridge.check_auth_error()
            if auth_err:
                logger.warning(f"Hub auth failure on @mention: {auth_err}")
                await message.channel.send(
                    "I'm having trouble connecting right now. The admin has been notified."
                )
                return

            hub_bridge.touch_activity()
            msg_id = hub_bridge.write_inbox(
                channel_id, user_id, text,
                channel_type="channel",
                channel_name=channel_name,
                attachments=attachments_data or None,
                context_messages=recent_context if recent_context else None,
            )
            _start_typing(message.channel, channel_id)
            if hub_bridge.is_project_active():
                try:
                    hub_bridge.send_to_lead(msg_id)
                except Exception as e:
                    logger.warning(f"Nudge to hub failed: {e}")
            else:
                logger.warning("Hub Claude Code not running, cannot process @mention")
                _stop_typing(channel_id)
                await message.channel.send(
                    "I'm waking up, give me a sec. Try again in a moment."
                )
        else:
            logger.error("Hub bridge not initialized for @mention")
            await message.channel.send(
                "Something's off on my end. Try again in a moment."
            )
        return

    bridge = _get_or_create_bridge(project_name)
    if not bridge:
        await message.channel.send(
            f"Something's off with **{project_name}**'s bridge. Let an admin know."
        )
        return

    logger.info(f"{message.author} -> {project_name}: {text[:80]}")

    # Check if hibernated and restore
    proj_info = registry.get(project_name)
    if proj_info and proj_info.status == "hibernated":
        # Check auth via hub before attempting wake (no point booting a dead agent)
        hub_bridge = bridges.get(HUB_NAME)
        if hub_bridge:
            auth_err = hub_bridge.check_auth_error()
            if auth_err:
                logger.warning(f"Auth failure detected before wake for {project_name}: {auth_err}")
                await message.channel.send(
                    "I'm having trouble connecting right now. The admin has been notified."
                )
                return
        logger.info(f"Restoring hibernated project '{project_name}' on channel message")
        await message.channel.send("waking up, one sec")
        restore(project_name, registry)
        _start_watchers(project_name)
        bridge = _get_or_create_bridge(project_name)
        if not bridge:
            await message.channel.send(f"Could not restore **{project_name}**.")
            return
        # Give Claude Code time to boot, then verify it started
        await asyncio.sleep(8)
        proj_info_check = registry.get(project_name)
        if proj_info_check and not is_claude_running(proj_info_check.tmux_lead_pane):
            logger.warning(f"Post-boot check failed for {project_name}")
            await message.channel.send(
                "Had trouble waking up. Try again in a moment."
            )
            return

    bridge.touch_activity()

    # Check for auth failure before processing -- tell the user instead of silence.
    # Check project bridge first, fall back to hub (project pane may be fresh with no errors yet).
    auth_err = bridge.check_auth_error()
    if not auth_err:
        hub_bridge = bridges.get(HUB_NAME)
        if hub_bridge:
            auth_err = hub_bridge.check_auth_error()
    if auth_err:
        logger.warning(f"Auth failure detected for {project_name}: {auth_err}")
        await message.channel.send(
            "I'm having trouble connecting right now. The admin has been notified."
        )
        return

    # -- Stuck-agent detection --
    # Check if user is confirming a pending restart offer
    offer = _restart_offers.get(channel_id)
    if offer:
        offer_project, offer_time = offer
        del _restart_offers[channel_id]
        if (time.time() - offer_time < _RESTART_OFFER_TTL
                and text.lower().strip().rstrip("!.") in _CONFIRM_PATTERNS):
            info = registry.get(offer_project)
            if info:
                await message.channel.send(f"restarting **{offer_project}**...")
                stop_claude_code(info.tmux_lead_pane, grace=5)
                if not is_session_alive(info.tmux_session):
                    create_tmux_session(info.tmux_session)
                started = start_claude_code(
                    info.project_dir, info.tmux_lead_pane,
                    linux_user=info.linux_user or None,
                )
                if started:
                    bridge.touch_activity()
                    await message.channel.send(f"**{offer_project}** is back. try talking to it now.")
                else:
                    await message.channel.send("couldn't restart. let an admin know.")
                return

    # Detect frustration: short message + pending inbox = agent stuck
    pending = bridge.pending_inbox_count()
    if (pending > 0
            and len(text) < 30
            and text.lower().strip().rstrip("?!.") in _FRUSTRATION_PATTERNS):
        _restart_offers[channel_id] = (project_name, time.time())
        await message.channel.send(
            f"your agent seems stuck on something. want me to give it a kick?"
        )
        return

    # User re-engaged -- cancel any pending follow-ups
    cancelled = bridge.cancel_pending_followups()
    if cancelled:
        logger.info(f"Cancelled {cancelled} pending followup(s) for {project_name}")

    msg_id = bridge.write_inbox(channel_id, user_id, text, attachments=attachments_data or None)
    _start_typing(message.channel, channel_id)

    if bridge.is_project_active():
        try:
            bridge.send_to_lead(msg_id)
        except Exception as e:
            logger.warning(f"Nudge to {project_name} failed: {e}")
    else:
        # Project agent is down -- fall back to hub which has snapshot data
        logger.info(f"Project {project_name} agent down, routing to hub")
        hub_bridge = bridges.get(HUB_NAME)
        if hub_bridge:
            channel_name = getattr(message.channel, "name", None) or project_name
            hub_msg_id = hub_bridge.write_inbox(
                channel_id, user_id, text,
                channel_type="project_channel",
                channel_name=channel_name,
                project_name=project_name,
                attachments=attachments_data or None,
            )
            if hub_bridge.is_project_active():
                try:
                    hub_bridge.send_to_lead(hub_msg_id)
                except Exception as e:
                    logger.warning(f"Hub fallback nudge failed: {e}")
            else:
                _stop_typing(channel_id)
                await message.channel.send(
                    "I'm waking up, give me a sec. Try again in a moment."
                )
        else:
            _stop_typing(channel_id)
            await message.channel.send(
                "I'm waking up, give me a sec. Try again in a moment."
            )


# -- Main --------------------------------------------------------------------

def main() -> None:
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN must be set in delta.env")
        raise SystemExit(1)

    print("Starting Delta")
    print(f"  Projects: {registry.list_projects()}")
    print(f"  Admin: {ADMIN_DISCORD_ID or '(not set)'}")

    client.run(DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
