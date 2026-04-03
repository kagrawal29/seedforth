"""Project provisioner -- Linux user creation, Claude Code launch, Discord channel setup.

Orchestrates everything needed to bring a new project online or tear one down.
Supports LOCAL_MODE for Mac development (skips Linux user isolation).
"""

import json
import logging
import os
import re
from pathlib import Path

from delta.lifecycle import (
    start_claude_code, stop_claude_code, create_tmux_session, kill_tmux_session,
    _allocate_port, start_ttyd, stop_ttyd,
)
from delta.registry import ProjectInfo, Registry

logger = logging.getLogger(__name__)

# Template CLAUDE.md ships with the tetrahedron repo. Override with DELTA_TEMPLATE_DIR.
_TEMPLATE_DIR = os.getenv("DELTA_TEMPLATE_DIR", "project-template")
_TEMPLATE_PATH = Path(__file__).parent.parent / _TEMPLATE_DIR / "CLAUDE.md"
_GITIGNORE_CONTENT = """\
delta-config/inbox/
delta-config/outbox/
delta-config/followups/
delta-config/progress/
"""

def _register_rube_mcp(project_dir: str, linux_user: str = "") -> bool:
    """Register Rube MCP server for a project using claude mcp add-json.

    Uses Bearer token auth (not X-API-Key) to avoid browser OAuth flow.
    When the Authorization header is pre-supplied, Claude Code sends it
    directly and never triggers the OAuth discovery that requires a browser.
    """
    import subprocess
    import shlex

    token = os.environ.get("RUBE_BEARER_TOKEN", "")
    if not token:
        logger.warning("RUBE_BEARER_TOKEN not set, skipping Rube MCP registration")
        return False

    mcp_json = json.dumps({
        "type": "http",
        "url": "https://rube.app/mcp",
        "headers": {
            "Authorization": f"Bearer {token}"
        }
    })
    cmd = ["claude", "mcp", "add-json", "rube", mcp_json, "--scope", "project"]

    if linux_user:
        from delta.isolation import run_as_user
        result = run_as_user(linux_user, " ".join(shlex.quote(c) for c in cmd), cwd=project_dir)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_dir)

    if result.returncode != 0:
        logger.warning(f"Failed to register Rube MCP: {result.stderr.strip()}")
        return False

    logger.info(f"Registered Rube MCP in {project_dir}")
    return True

# Valid project name: alphanumeric + hyphens, 2-30 chars
_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9-]{1,29}$")

LOCAL_MODE = os.getenv("LOCAL_MODE", "").lower() in ("true", "1", "yes")
LOCAL_PROJECTS_DIR = os.getenv("LOCAL_PROJECTS_DIR", os.path.expanduser("~/.delta-projects"))


def _github_clone_url(repo: str) -> str:
    """Build a clone URL, injecting GITHUB_TOKEN for private repo access."""
    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        return f"https://x-access-token:{token}@github.com/{repo}.git"
    return f"https://github.com/{repo}.git"


def _verify_github_repo(repo: str) -> bool:
    """Check if a GitHub repo exists and is accessible. Returns True if reachable."""
    import subprocess
    token = os.getenv("GITHUB_TOKEN", "")
    cmd = ["git", "ls-remote", _github_clone_url(repo)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return result.returncode == 0


GITHUB_ORG = "Seedforth"


def _setup_github_repo(name: str, project_dir: str, linux_user: str = "",
                       source_repo: str = "") -> str:
    """Ensure a Seedforth GitHub repo exists and configure it as the remote.

    If source_repo is provided (e.g. 'kagrawal29/solve-os'), the project was
    already cloned from it. We create a Seedforth repo and point origin there.

    Returns the full repo path (e.g. 'Seedforth/project-name') or empty on failure.
    """
    import subprocess
    import urllib.request
    import urllib.error

    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        logger.warning("GITHUB_TOKEN not set, skipping GitHub repo setup")
        return ""

    repo_name = name
    full_repo = f"{GITHUB_ORG}/{repo_name}"

    # Create repo in org (ignore 422 = already exists)
    try:
        data = json.dumps({"name": repo_name, "private": True}).encode()
        req = urllib.request.Request(
            f"https://api.github.com/orgs/{GITHUB_ORG}/repos",
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
            },
        )
        urllib.request.urlopen(req)
        logger.info(f"Created GitHub repo {full_repo}")
    except urllib.error.HTTPError as e:
        if e.code == 422:
            logger.info(f"GitHub repo {full_repo} already exists")
        else:
            body = e.read().decode()
            logger.warning(f"Failed to create GitHub repo: {e.code} {body}")
            return ""

    # Configure remote
    clone_url = f"https://x-access-token:{token}@github.com/{full_repo}.git"
    if linux_user:
        from delta.isolation import run_as_user
        run_as_user(linux_user, f"git -C {project_dir} remote remove origin 2>/dev/null; true")
        run_as_user(linux_user, f"git -C {project_dir} remote add origin {clone_url}")
    else:
        subprocess.run(["git", "-C", project_dir, "remote", "remove", "origin"],
                       capture_output=True, text=True)
        subprocess.run(["git", "-C", project_dir, "remote", "add", "origin", clone_url],
                       capture_output=True, text=True)

    logger.info(f"Configured remote origin -> {full_repo}")
    return full_repo


def _init_git_repo(project_path: Path, linux_user: str = "") -> None:
    """Initialize a git repo with .gitignore if one doesn't exist."""
    import subprocess

    git_dir = project_path / ".git"
    if git_dir.exists():
        # Already a repo (cloned). Just add .gitignore if missing.
        gitignore = project_path / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(_GITIGNORE_CONTENT)
        return

    if linux_user:
        from delta.isolation import run_as_user
        run_as_user(linux_user, f"git init {project_path}")
        run_as_user(linux_user, f"git -C {project_path} config user.email delta@seedforth.com")
        run_as_user(linux_user, f"git -C {project_path} config user.name Delta")
    else:
        subprocess.run(["git", "init", str(project_path)], capture_output=True, text=True)
        subprocess.run(["git", "-C", str(project_path), "config", "user.email", "delta@seedforth.com"],
                       capture_output=True, text=True)
        subprocess.run(["git", "-C", str(project_path), "config", "user.name", "Delta"],
                       capture_output=True, text=True)

    gitignore = project_path / ".gitignore"
    gitignore.write_text(_GITIGNORE_CONTENT)
    logger.info(f"Initialized git repo in {project_path}")


def _validate_name(name: str) -> None:
    if not _NAME_RE.match(name):
        raise ValueError(
            f"Invalid project name '{name}'. "
            "Must be 2-30 characters, alphanumeric and hyphens only, "
            "starting with a letter or number."
        )


def _initial_schedule(name: str) -> dict:
    """Return the initial schedule.json content for a new project."""
    return {
        "tasks": [],
        "reporting": {
            "frequency": "daily",
            "time": "09:00",
            "timezone": "UTC",
            "style": "calm",
            "what_matters": "what shipped and what's next",
        },
        "morning_trip": {
            "enabled": False,
            "time": "09:00",
            "timezone": "UTC",
            "philosophy": "Show something new. Push the project forward.",
            "integrity_anchors": [],
        },
        "project": {
            "name": name,
            "core_idea": "",
        },
    }


def _init_linkedin_data(project_path: Path, linux_user: str = "") -> None:
    """Seed empty data files and config for a linkedin project."""
    from datetime import datetime, timezone

    data_dir = project_path / "data"
    data_dir.mkdir(exist_ok=True)

    templates = {
        "contacts.json": {"contacts": [], "updated_at": ""},
        "pipeline.json": {"ideas": [], "drafts": [], "ready": [], "posted": []},
        "targets.json": {"quarterly": {}, "weekly": {}},
        "dm-tracker.json": {"threads": [], "templates": []},
        "autonomy.json": {
            "profile_view": "auto",
            "reaction": "auto",
            "search": "auto",
            "draft_content": "auto",
            "warmth_update": "auto",
            "dm_to_connection": "notify",
            "accept_connection": "notify",
            "comment_on_connection": "notify",
            "connection_request": "approval",
            "cold_dm": "approval",
            "publish_post": "approval",
            "send_inmail": "approval",
            "withdraw_connection": "blocked",
            "delete_post": "blocked",
            "block_user": "blocked",
        },
    }

    for filename, content in templates.items():
        filepath = data_dir / filename
        if not filepath.exists():
            filepath.write_text(json.dumps(content, indent=2))

    # Touch activity log
    log_file = data_dir / "activity-log.jsonl"
    if not log_file.exists():
        log_file.touch()

    # Write linkedin-config.env (UNIPILE_ACCOUNT_ID added later after polling)
    env_file = project_path / "linkedin-config.env"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    env_file.write_text(
        f"export LINKEDIN_DATA_DIR={project_path}/data\n"
        f"export ACCOUNT_START_DATE={today}\n"
    )

    if linux_user:
        import subprocess as _sp
        _sp.run(["sudo", "chown", "-R", f"{linux_user}:", str(data_dir)],
                capture_output=True, text=True)
        _sp.run(["sudo", "chown", f"{linux_user}:", str(env_file)],
                capture_output=True, text=True)


def _setup_project_dirs(name: str, github_repo: str = "",
                        project_type: str = "standard") -> tuple[str, str, str]:
    """Create project directory, delta-config dirs, and git repo.

    Returns (project_dir, data_dir, linux_username).
    Handles both LOCAL_MODE (Mac) and server mode (Linux user isolation).
    """
    username = ""

    if LOCAL_MODE:
        import subprocess

        base = Path(LOCAL_PROJECTS_DIR)
        base.mkdir(parents=True, exist_ok=True)
        project_path = base / name
        data_path = project_path / "delta-config"

        if github_repo:
            if not _verify_github_repo(github_repo):
                raise RuntimeError(
                    f"Cannot access {github_repo} -- repo doesn't exist, is private "
                    f"without GITHUB_TOKEN set, or network error"
                )
            url = _github_clone_url(github_repo)
            logger.info(f"Cloning {github_repo}")
            result = subprocess.run(
                ["git", "clone", url, str(project_path)],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"git clone failed: {result.stderr.strip()}")
        else:
            project_path.mkdir(parents=True, exist_ok=True)

        (data_path / "inbox").mkdir(parents=True, exist_ok=True)
        (data_path / "outbox").mkdir(parents=True, exist_ok=True)
        (data_path / "logs").mkdir(parents=True, exist_ok=True)
        (data_path / "followups").mkdir(parents=True, exist_ok=True)
        (data_path / "progress").mkdir(parents=True, exist_ok=True)
        schedule_file = data_path / "schedule.json"
        if not schedule_file.exists():
            schedule_file.write_text(json.dumps(_initial_schedule(name), indent=2))

        # Personal agent projects need memory/ and memory/checklists/ directories
        if project_type in ("personal", "personal_dm"):
            (project_path / "memory" / "checklists").mkdir(parents=True, exist_ok=True)
        # LinkedIn projects need data/ directory for unipile safety controller
        if project_type == "linkedin":
            (project_path / "data").mkdir(parents=True, exist_ok=True)

        project_dir = str(project_path)
        data_dir = str(data_path)

        _init_git_repo(project_path)

    else:
        from delta.isolation import linux_username, create_user, run_as_user

        username = linux_username(name)
        project_dir = f"/home/{username}/{name}"
        data_dir = f"{project_dir}/delta-config"

        logger.info(f"Creating user {username}")
        create_user(name)

        if github_repo:
            if not _verify_github_repo(github_repo):
                raise RuntimeError(
                    f"Cannot access {github_repo} -- repo doesn't exist, is private "
                    f"without GITHUB_TOKEN set, or network error"
                )
            url = _github_clone_url(github_repo)
            logger.info(f"Cloning {github_repo}")
            result = run_as_user(username, f"git clone {url} {project_dir}")
            if result.returncode != 0:
                raise RuntimeError(f"git clone failed: {result.stderr.strip()}")
        else:
            result = run_as_user(username, f"mkdir -p {project_dir}")
            if result.returncode != 0:
                raise RuntimeError(f"mkdir failed: {result.stderr.strip()}")

        run_as_user(username, f"mkdir -p {data_dir}/inbox {data_dir}/outbox {data_dir}/logs {data_dir}/followups {data_dir}/progress")
        if project_type in ("personal", "personal_dm"):
            run_as_user(username, f"mkdir -p {project_dir}/memory/checklists")
        if project_type == "linkedin":
            run_as_user(username, f"mkdir -p {project_dir}/data")
        # Write schedule.json (delta user has group write via 2770 home dir)
        schedule_path = Path(data_dir) / "schedule.json"
        schedule_path.write_text(json.dumps(_initial_schedule(name), indent=2))
        import subprocess as _sp
        _sp.run(["sudo", "chown", f"{username}:delta", str(schedule_path)],
                capture_output=True, text=True)

        _init_git_repo(Path(project_dir), linux_user=username)

    return project_dir, data_dir, username


def _finalize_project(name: str, project_dir: str, data_dir: str,
                      username: str, discord_channel_id: str,
                      github_repo: str, owner_discord_id: str,
                      is_dream_space: bool, registry: Registry,
                      project_type: str = "standard",
                      admin_brief: str = "",
                      unipile_account_id: str = "") -> ProjectInfo:
    """Write CLAUDE.md, create tmux session, start Claude Code, register.

    Common tail shared by provision() and provision_in_channel().
    Returns the registered ProjectInfo.
    """
    tmux_session = f"proj-{name}"
    tmux_pane = f"{tmux_session}:lead"

    # Allocate ttyd port early so we can include the URL in CLAUDE.md
    port = _allocate_port(registry)
    server_host = os.getenv("DELTA_SERVER_HOST", "")
    ttyd_url = f"http://{server_host}:{port}" if server_host and port else ""

    # Write CLAUDE.md from template -- select template based on project_type
    if project_type == "personal":
        template_file = Path(__file__).parent.parent / _TEMPLATE_DIR / "PERSONAL_ONBOARDING.md"
    elif project_type == "personal_dm":
        template_file = Path(__file__).parent.parent / _TEMPLATE_DIR / "PERSONAL_DM.md"
    elif project_type == "linkedin":
        template_file = Path(__file__).parent.parent / _TEMPLATE_DIR / "LINKEDIN.md"
    else:
        template_file = _TEMPLATE_PATH  # standard CLAUDE.md

    if template_file.exists():
        template = template_file.read_text()
        format_vars = {
            "project_name": name,
            "project_dir": project_dir,
            "linux_user": username or os.getenv("USER", "local"),
            "discord_channel_id": discord_channel_id,
            "ttyd_url": ttyd_url,
        }
        if project_type == "personal":
            format_vars["admin_brief"] = admin_brief or "(no admin brief provided)"
        if project_type == "linkedin":
            if LOCAL_MODE:
                unipile_tool = str(Path(__file__).parent.parent / "tools" / "unipile.py")
            else:
                unipile_tool = "/opt/delta/tools/unipile.py"
            format_vars["unipile_tool_path"] = unipile_tool
            format_vars["user_display_name"] = admin_brief or name
        claude_md = template.format(**format_vars)
        claude_md_path = Path(project_dir) / "CLAUDE.md"
        claude_md_path.write_text(claude_md)

    # Seed LinkedIn data files and config
    if project_type == "linkedin":
        _init_linkedin_data(Path(project_dir), username)

    # Copy hooks directory into project
    import shutil
    hooks_src = Path(__file__).parent.parent / "project-template" / "hooks"
    hooks_dst = Path(project_dir) / "hooks"
    if hooks_src.exists():
        if hooks_dst.exists():
            shutil.rmtree(hooks_dst)
        shutil.copytree(hooks_src, hooks_dst)
        hook_script = hooks_dst / "progress_hook.py"
        if hook_script.exists():
            hook_script.chmod(0o755)

    # Write project-level .claude/settings.json with PostToolUse hook
    claude_settings_dir = Path(project_dir) / ".claude"
    claude_settings_dir.mkdir(parents=True, exist_ok=True)
    claude_settings = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"python3 {project_dir}/hooks/progress_hook.py",
                            "async": True,
                        }
                    ]
                }
            ]
        }
    }
    (claude_settings_dir / "settings.json").write_text(json.dumps(claude_settings, indent=2))

    # Fix file ownership and make initial git commit
    if username:
        import subprocess as _sp
        for fname in ["CLAUDE.md", ".gitignore"]:
            fpath = Path(project_dir) / fname
            if fpath.exists():
                _sp.run(["sudo", "chown", f"{username}:", str(fpath)],
                        capture_output=True, text=True)
        # Fix ownership on hooks and .claude/settings.json
        if hooks_dst.exists():
            _sp.run(["sudo", "chown", "-R", f"{username}:", str(hooks_dst)],
                    capture_output=True, text=True)
        if claude_settings_dir.exists():
            _sp.run(["sudo", "chown", "-R", f"{username}:", str(claude_settings_dir)],
                    capture_output=True, text=True)
        from delta.isolation import run_as_user
        run_as_user(username, f"git -C {project_dir} add -A")
        run_as_user(username, f'git -C {project_dir} commit -m "Initial project setup"')
    else:
        import subprocess as _sp
        _sp.run(["git", "-C", project_dir, "add", "-A"],
                capture_output=True, text=True)
        _sp.run(["git", "-C", project_dir, "commit", "-m", "Initial project setup"],
                capture_output=True, text=True)

    # Set up GitHub repo in Seedforth org and push initial commit
    seedforth_repo = _setup_github_repo(name, project_dir, username, github_repo)
    if seedforth_repo and username:
        from delta.isolation import run_as_user
        branch = "master"  # git init defaults to master
        run_as_user(username, f"git -C {project_dir} push -u origin {branch} 2>/dev/null || true")
        logger.info(f"Pushed initial commit to {seedforth_repo}")
    elif seedforth_repo:
        import subprocess as _sp
        _sp.run(["git", "-C", project_dir, "push", "-u", "origin", "master"],
                capture_output=True, text=True)

    # Clean up old .mcp.json BEFORE registering (claude mcp add-json writes
    # to .mcp.json, so deleting after would nuke the new config)
    old_mcp = Path(project_dir) / ".mcp.json"
    if old_mcp.exists():
        old_mcp.unlink()
        logger.info(f"Removed old .mcp.json from {project_dir}")

    # Register Rube MCP via claude mcp add-json
    _register_rube_mcp(project_dir, username)

    # Create tmux session + start Claude Code
    logger.info(f"Creating tmux session {tmux_session}")
    create_tmux_session(tmux_session)

    logger.info(f"Starting Claude Code in {tmux_pane}")
    extra_env: dict = {}
    if project_type == "linkedin" and unipile_account_id:
        extra_env["UNIPILE_ACCOUNT_ID"] = unipile_account_id
        for key in ("UNIPILE_DSN", "UNIPILE_API_KEY"):
            val = os.environ.get(key, "")
            if val:
                extra_env[key] = val
    start_claude_code(project_dir, tmux_pane,
                      linux_user=username if username else None,
                      extra_env=extra_env if extra_env else None)

    # Start per-project web terminal (port allocated earlier for CLAUDE.md)
    start_ttyd(name, tmux_session, port)

    # Register
    info = ProjectInfo(
        name=name,
        project_dir=project_dir,
        data_dir=data_dir,
        tmux_session=tmux_session,
        tmux_lead_pane=tmux_pane,
        nudge_prefix="delta-config/inbox",
        github_repo=seedforth_repo or github_repo,
        linux_user=username,
        discord_channel_id=discord_channel_id,
        owner_discord_id=owner_discord_id,
        is_dream_space=is_dream_space,
        ttyd_port=port,
        project_type=project_type,
    )
    registry.add(info)

    return info


async def provision(name: str, registry: Registry, discord_bot, guild,
                    owner_discord_id: str, github_repo: str = "",
                    is_dream_space: bool = False,
                    project_type: str = "standard",
                    admin_brief: str = "",
                    target_user_id: str = "",
                    unipile_account_id: str = "") -> ProjectInfo:
    """Provision a new project end-to-end.

    Creates a new Discord channel, sets up project files, launches Claude Code.
    In LOCAL_MODE (Mac): skips Linux user creation, uses local project dir.
    In server mode: full Linux user isolation.

    Returns ProjectInfo.
    Raises ValueError for bad names, RuntimeError for infra failures.
    """
    _validate_name(name)
    if registry.get(name):
        raise ValueError(f"Project '{name}' already exists")

    project_dir, data_dir, username = _setup_project_dirs(
        name, github_repo, project_type=project_type,
    )

    # Create private Discord channel
    discord_channel_id = ""
    if discord_bot and guild:
        logger.info(f"Creating Discord channel for {name}")
        channel = await _create_project_channel(
            discord_bot, guild, name, owner_discord_id,
            target_user_id=target_user_id,
        )
        discord_channel_id = str(channel.id)

    info = _finalize_project(
        name, project_dir, data_dir, username, discord_channel_id,
        github_repo, owner_discord_id, is_dream_space, registry,
        project_type=project_type, admin_brief=admin_brief,
        unipile_account_id=unipile_account_id,
    )
    logger.info(f"Project {name} provisioned and registered")
    return info


async def provision_in_channel(name: str, registry: Registry, discord_bot, guild,
                               owner_discord_id: str, channel_id: str,
                               github_repo: str = "",
                               is_dream_space: bool = False,
                               project_type: str = "standard",
                               admin_brief: str = "",
                               unipile_account_id: str = "") -> ProjectInfo:
    """Provision a project using an existing Discord channel.

    Same as provision() but skips channel creation and uses the given channel_id.
    """
    _validate_name(name)
    if registry.get(name):
        raise ValueError(f"Project '{name}' already exists")

    project_dir, data_dir, username = _setup_project_dirs(
        name, github_repo, project_type=project_type,
    )

    info = _finalize_project(
        name, project_dir, data_dir, username, channel_id,
        github_repo, owner_discord_id, is_dream_space, registry,
        project_type=project_type, admin_brief=admin_brief,
        unipile_account_id=unipile_account_id,
    )
    logger.info(f"Project {name} provisioned in existing channel {channel_id}")
    return info


def refresh_templates(registry) -> int:
    """Re-render CLAUDE.md from template for all registered projects.

    Use after updating project-template/CLAUDE.md to push changes to
    existing projects. Commits the update in each project's git repo.
    Skips personal agent projects (they have their own template lifecycle).
    Returns the number of projects updated.
    """
    if not _TEMPLATE_PATH.exists():
        logger.error("Template not found: %s", _TEMPLATE_PATH)
        return 0

    template = _TEMPLATE_PATH.read_text()
    updated = 0

    for name in registry.list_projects():
        info = registry.get(name)
        if not info:
            continue

        # Skip personal agent projects -- their CLAUDE.md is managed by the
        # onboarding/transition lifecycle, not bulk refresh
        if getattr(info, "project_type", "standard") in ("personal", "persistent", "personal_dm", "linkedin"):
            logger.info(f"Skipping {name} (project_type={info.project_type})")
            continue

        server_host = os.getenv("DELTA_SERVER_HOST", "")
        ttyd_port = getattr(info, "ttyd_port", 0)
        ttyd_url = f"http://{server_host}:{ttyd_port}" if server_host and ttyd_port else ""
        claude_md = template.format(
            project_name=info.name,
            project_dir=info.project_dir,
            linux_user=info.linux_user or os.getenv("USER", "local"),
            discord_channel_id=info.discord_channel_id,
            ttyd_url=ttyd_url,
        )

        claude_md_path = Path(info.project_dir) / "CLAUDE.md"
        if not claude_md_path.parent.exists():
            logger.warning(f"Project dir missing for {name}, skipping")
            continue

        claude_md_path.write_text(claude_md)

        # Copy hooks directory
        import shutil
        hooks_src = Path(__file__).parent.parent / "project-template" / "hooks"
        hooks_dst = Path(info.project_dir) / "hooks"
        if hooks_src.exists():
            if hooks_dst.exists():
                shutil.rmtree(hooks_dst)
            shutil.copytree(hooks_src, hooks_dst)
            hook_script = hooks_dst / "progress_hook.py"
            if hook_script.exists():
                hook_script.chmod(0o755)

        # Write project-level .claude/settings.json with PostToolUse hook
        claude_settings_dir = Path(info.project_dir) / ".claude"
        claude_settings_dir.mkdir(parents=True, exist_ok=True)
        claude_settings = {
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "",
                        "hooks": [
                            {
                                "type": "command",
                                "command": f"python3 {info.project_dir}/hooks/progress_hook.py",
                                "async": True,
                            }
                        ]
                    }
                ]
            }
        }
        (claude_settings_dir / "settings.json").write_text(json.dumps(claude_settings, indent=2))

        # Create progress dir if missing
        progress_dir = Path(info.project_dir) / "delta-config" / "progress"
        progress_dir.mkdir(parents=True, exist_ok=True)

        # Fix ownership on server
        if info.linux_user:
            import subprocess as _sp
            _sp.run(["sudo", "chown", f"{info.linux_user}:", str(claude_md_path)],
                    capture_output=True, text=True)
            if hooks_dst.exists():
                _sp.run(["sudo", "chown", "-R", f"{info.linux_user}:", str(hooks_dst)],
                        capture_output=True, text=True)
            if claude_settings_dir.exists():
                _sp.run(["sudo", "chown", "-R", f"{info.linux_user}:", str(claude_settings_dir)],
                        capture_output=True, text=True)
            _sp.run(["sudo", "chown", "-R", f"{info.linux_user}:", str(progress_dir)],
                    capture_output=True, text=True)

        # Clean up old .mcp.json BEFORE registering (claude mcp add-json
        # refuses to add if "rube" already exists in .mcp.json)
        old_mcp = Path(info.project_dir) / ".mcp.json"
        if old_mcp.exists():
            old_mcp.unlink()
            logger.info(f"Removed old .mcp.json from {info.project_dir}")

        # Register Rube MCP via claude mcp add-json
        _register_rube_mcp(info.project_dir, info.linux_user)

        # Commit the update (must run as project user to avoid root-owned git objects)
        if info.linux_user:
            from delta.isolation import run_as_user
            run_as_user(info.linux_user, f"git -C {info.project_dir} add CLAUDE.md hooks/ .claude/settings.json")
            run_as_user(info.linux_user, f'git -C {info.project_dir} commit -m "Update template, hooks, and settings"')
        else:
            import subprocess as _sp
            _sp.run(["git", "-C", info.project_dir, "add", "CLAUDE.md", "hooks/", ".claude/settings.json"],
                    capture_output=True, text=True)
            _sp.run(["git", "-C", info.project_dir, "commit", "-m",
                     "Update template, hooks, and settings"],
                    capture_output=True, text=True)

        logger.info(f"Refreshed CLAUDE.md for {name}")
        updated += 1

    return updated


def git_save(project_dir: str, linux_user: str = "") -> bool:
    """Commit all project state to git for hibernation. Returns True on success."""
    import subprocess
    from datetime import datetime, timezone

    project_path = Path(project_dir)
    if not (project_path / ".git").exists():
        logger.warning(f"No git repo in {project_dir}, skipping git save")
        return False

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    msg = f"hibernate: {timestamp}"

    def _git(*args):
        cmd = ["git", "-C", str(project_path)] + list(args)
        if linux_user:
            from delta.isolation import run_as_user
            import shlex
            return run_as_user(linux_user, " ".join(shlex.quote(c) for c in cmd))
        return subprocess.run(cmd, capture_output=True, text=True)

    # Stage everything including logs (force-add past gitignore)
    _git("add", "-A")
    logs_dir = project_path / "delta-config" / "logs"
    if logs_dir.exists():
        _git("add", "-f", "delta-config/logs/")

    # Commit (may be empty if nothing changed)
    result = _git("commit", "-m", msg, "--allow-empty")
    if result.returncode != 0:
        logger.warning(f"git commit in {project_dir}: {result.stderr.strip()}")

    # Best-effort push
    _git("push")

    logger.info(f"git save complete for {project_dir}")
    return True


def hibernate(name: str, registry, bridges: dict) -> bool:
    """Hibernate a project: save state, stop Claude Code, kill tmux, shutdown bridge.

    Does NOT delete project dir or Discord channel.
    Returns True on success.
    """
    info = registry.get(name)
    if not info:
        logger.warning(f"Cannot hibernate {name}: not in registry")
        return False

    logger.info(f"Hibernating {name}")

    # 1. Git save
    git_save(info.project_dir, info.linux_user)

    # 2. Stop web terminal
    stop_ttyd(name)

    # 3. Stop Claude Code
    stop_claude_code(info.tmux_lead_pane, grace=5)

    # 4. Kill tmux session
    kill_tmux_session(info.tmux_session)

    # 5. Shutdown bridge watchers
    bridge = bridges.get(name)
    if bridge:
        bridge.shutdown()
        del bridges[name]

    # 6. Mark as hibernated in registry
    registry.update(name, status="hibernated")

    logger.info(f"{name} hibernated")
    return True


def restore(name: str, registry) -> bool:
    """Restore a hibernated project: re-create tmux, start Claude Code, mark active.

    Project dir and git repo already exist.
    Returns True on success.
    """
    info = registry.get(name)
    if not info:
        logger.warning(f"Cannot restore {name}: not in registry")
        return False

    if info.status != "hibernated":
        logger.info(f"{name} is not hibernated (status: {info.status})")
        return True

    logger.info(f"Restoring {name}")

    # Ensure .claude.json exists (prevents theme/onboarding prompts)
    if info.linux_user:
        user_home = Path(f"/home/{info.linux_user}")
        claude_json = user_home / ".claude.json"
        if user_home.exists() and not claude_json.exists():
            claude_json.write_text(json.dumps({
                "theme": "dark",
                "hasCompletedOnboarding": True,
            }))
            import subprocess as _sp
            _sp.run(["sudo", "chown", f"{info.linux_user}:", str(claude_json)],
                    capture_output=True, text=True)

    # Re-create tmux session
    create_tmux_session(info.tmux_session)

    # Start Claude Code
    start_claude_code(
        info.project_dir, info.tmux_lead_pane,
        linux_user=info.linux_user or None,
    )

    # Restart web terminal
    port = info.ttyd_port or _allocate_port(registry)
    start_ttyd(name, info.tmux_session, port)
    if not info.ttyd_port:
        registry.update(name, ttyd_port=port)

    # Mark as active
    from datetime import datetime, timezone
    registry.update(
        name,
        status="active",
        last_activity=datetime.now(timezone.utc).isoformat(),
    )

    logger.info(f"{name} restored")
    return True


async def teardown(name: str, registry: Registry, discord_bot, guild) -> bool:
    """Tear down a project completely.

    1. Stop Claude Code + kill tmux session
    2. Delete Discord channel
    3. Remove from registry
    4. Delete Linux user

    Returns True on success.
    """
    info = registry.get(name)
    if not info:
        raise ValueError(f"Project '{name}' not found")

    tmux_session = info.tmux_session
    tmux_pane = info.tmux_lead_pane

    # 1. Stop web terminal and Claude Code, kill tmux
    stop_ttyd(name)
    logger.info(f"Stopping Claude Code for {name}")
    stop_claude_code(tmux_pane)
    kill_tmux_session(tmux_session)

    # 2. Delete Discord channel
    if discord_bot and guild and info.discord_channel_id:
        try:
            channel = discord_bot.get_channel(int(info.discord_channel_id))
            if channel:
                await channel.delete(reason=f"Project {name} torn down")
                logger.info(f"Deleted Discord channel {info.discord_channel_id}")
        except Exception as e:
            logger.warning(f"Failed to delete Discord channel: {e}")

    # 3. Remove from registry
    registry.remove(name)

    # 4. Clean up project files
    if info.linux_user and not LOCAL_MODE:
        # Server mode: delete Linux user (removes /home/proj-{name})
        try:
            from delta.isolation import delete_user
            delete_user(info.linux_user)
        except RuntimeError as e:
            logger.warning(f"Failed to delete user {info.linux_user}: {e}")
    elif LOCAL_MODE and info.project_dir:
        # Local mode: remove project directory if it's under LOCAL_PROJECTS_DIR
        import shutil
        project_path = Path(info.project_dir).resolve()
        sandbox = Path(LOCAL_PROJECTS_DIR).resolve()
        if project_path != sandbox and sandbox in project_path.parents:
            try:
                shutil.rmtree(project_path)
                logger.info(f"Deleted local project dir {project_path}")
            except OSError as e:
                logger.warning(f"Failed to delete project dir {project_path}: {e}")
        else:
            logger.warning(
                f"Refusing to delete {project_path} -- not under {sandbox}"
            )

    logger.info(f"Project {name} torn down")
    return True


async def _create_project_channel(discord_bot, guild, project_name: str,
                                   owner_discord_id: str,
                                   target_user_id: str = ""):
    """Create a private Discord channel visible only to bot + owner + target user."""
    import discord

    # Find or create "Delta Projects" category
    category = None
    for cat in guild.categories:
        if cat.name == "Delta Projects":
            category = cat
            break

    if not category:
        category = await guild.create_category("Delta Projects")

    # Permission overwrites: deny @everyone, allow bot + owner
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(
            read_messages=True, send_messages=True, manage_channels=True,
        ),
    }

    # Add owner permissions if we can find the member
    try:
        member = await guild.fetch_member(int(owner_discord_id))
        overwrites[member] = discord.PermissionOverwrite(
            read_messages=True, send_messages=True,
        )
    except Exception:
        logger.warning(f"Could not find member {owner_discord_id} for channel permissions")

    # Add target user permissions (e.g. person being onboarded)
    if target_user_id and target_user_id != owner_discord_id:
        try:
            target_member = await guild.fetch_member(int(target_user_id))
            overwrites[target_member] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True,
            )
        except Exception:
            logger.warning(f"Could not find target member {target_user_id} for channel permissions")

    channel = await guild.create_text_channel(
        name=f"proj-{project_name}",
        category=category,
        overwrites=overwrites,
        topic=f"Project: {project_name}",
    )
    return channel
