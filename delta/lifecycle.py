"""Claude Code lifecycle management via tmux.

Adapted from conductor/lifecycle.py for per-project use.
Each project gets its own persistent Claude Code instance.
"""

import logging
import os
import subprocess
import time

logger = logging.getLogger(__name__)

DEFAULT_GRACE = 10


def _run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def is_session_alive(session: str) -> bool:
    """Check if a tmux session exists."""
    result = _run(["tmux", "has-session", "-t", session])
    return result.returncode == 0


def is_claude_running(tmux_pane: str) -> bool:
    """Check if Claude Code is running in a tmux pane."""
    session = tmux_pane.split(":")[0]
    if not is_session_alive(session):
        return False

    result = _run([
        "tmux", "list-panes", "-t", tmux_pane, "-F", "#{pane_pid}"
    ])
    if result.returncode != 0:
        return False

    pane_pid = result.stdout.strip()
    if not pane_pid:
        return False

    # Get child PIDs of the pane shell
    result = _run(["pgrep", "-P", pane_pid])
    if result.returncode != 0:
        return False

    # Check each child process command for "claude"
    for pid in result.stdout.strip().split("\n"):
        pid = pid.strip()
        if not pid:
            continue
        ps_result = _run(["ps", "-p", pid, "-o", "command="])
        if ps_result.returncode == 0 and "claude" in ps_result.stdout.lower():
            return True

    return False


def start_claude_code(project_dir: str, tmux_pane: str,
                      linux_user: str | None = None,
                      extra_env: dict | None = None) -> bool:
    """Start Claude Code in the given tmux pane.

    If linux_user is provided, runs as that user via sudo -u.
    Returns True if the command was sent.
    """
    if is_claude_running(tmux_pane):
        logger.info(f"Claude Code already running in {tmux_pane}")
        return True

    session = tmux_pane.split(":")[0]
    if not is_session_alive(session):
        logger.error(f"tmux session {session} does not exist")
        return False

    if linux_user:
        # Pass OAuth token + API keys via env file to avoid leaking in tmux scrollback
        token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
        composio_key = os.environ.get("COMPOSIO_API_KEY", "")
        vercel_token = os.environ.get("VERCEL_TOKEN", "")
        rube_token = os.environ.get("RUBE_BEARER_TOKEN", "")
        github_token = os.environ.get("GITHUB_TOKEN", "")
        unipile_dsn = os.environ.get("UNIPILE_DSN", "")
        unipile_key = os.environ.get("UNIPILE_API_KEY", "")
        if token or composio_key or vercel_token or rube_token or unipile_dsn:
            token_file = f"/tmp/.claude-token-{linux_user}"
            try:
                import stat
                # Remove old file first via sudo -- it may be owned by the project user
                subprocess.run(["sudo", "rm", "-f", token_file],
                               capture_output=True, text=True)
                with open(token_file, "w") as f:
                    if token:
                        f.write(f"export CLAUDE_CODE_OAUTH_TOKEN={token}\n")
                    if composio_key:
                        f.write(f"export COMPOSIO_API_KEY={composio_key}\n")
                    if vercel_token:
                        f.write(f"export VERCEL_TOKEN={vercel_token}\n")
                    if rube_token:
                        f.write(f"export RUBE_BEARER_TOKEN={rube_token}\n")
                    if github_token:
                        f.write(f"export GITHUB_TOKEN={github_token}\n")
                    if unipile_dsn:
                        f.write(f"export UNIPILE_DSN={unipile_dsn}\n")
                    if unipile_key:
                        f.write(f"export UNIPILE_API_KEY={unipile_key}\n")
                    if extra_env:
                        for k, v in extra_env.items():
                            f.write(f"export {k}={v}\n")
                os.chmod(token_file, stat.S_IRUSR | stat.S_IWUSR)
                subprocess.run(["sudo", "chown", f"{linux_user}:", token_file],
                               capture_output=True, text=True)
            except OSError as e:
                logger.warning(f"Failed to write token file {token_file}: {e}")
            # Source project-specific linkedin config if it exists
            linkedin_env = os.path.join(project_dir, "linkedin-config.env")
            linkedin_source = f"source {linkedin_env} 2>/dev/null; " if os.path.exists(linkedin_env) else ""
            cmd = (f"sudo -u {linux_user} bash -c "
                   f"'source {token_file} 2>/dev/null; {linkedin_source}"
                   f"cd \"{project_dir}\" && claude --dangerously-skip-permissions'")
        else:
            cmd = f"sudo -u {linux_user} bash -c 'cd \"{project_dir}\" && claude --dangerously-skip-permissions'"
    else:
        # Local mode: pass API keys in the command environment
        composio_key = os.environ.get("COMPOSIO_API_KEY", "")
        vercel_token = os.environ.get("VERCEL_TOKEN", "")
        rube_token = os.environ.get("RUBE_BEARER_TOKEN", "")
        unipile_dsn = os.environ.get("UNIPILE_DSN", "")
        unipile_key = os.environ.get("UNIPILE_API_KEY", "")
        env_parts = []
        if composio_key:
            env_parts.append(f'export COMPOSIO_API_KEY="{composio_key}"')
        if vercel_token:
            env_parts.append(f'export VERCEL_TOKEN="{vercel_token}"')
        if rube_token:
            env_parts.append(f'export RUBE_BEARER_TOKEN="{rube_token}"')
        if unipile_dsn:
            env_parts.append(f'export UNIPILE_DSN="{unipile_dsn}"')
        if unipile_key:
            env_parts.append(f'export UNIPILE_API_KEY="{unipile_key}"')
        if extra_env:
            for k, v in extra_env.items():
                env_parts.append(f'export {k}="{v}"')
        # Source project-specific linkedin config if it exists
        linkedin_env = os.path.join(project_dir, "linkedin-config.env")
        linkedin_source = f"source {linkedin_env} 2>/dev/null; " if os.path.exists(linkedin_env) else ""
        env_prefix = "; ".join(env_parts) + "; " if env_parts else ""
        cmd = f'{env_prefix}{linkedin_source}cd "{project_dir}" && claude --dangerously-skip-permissions'

    try:
        _run(["tmux", "send-keys", "-t", tmux_pane, "-l", cmd], check=True)
        time.sleep(0.3)
        _run(["tmux", "send-keys", "-t", tmux_pane, "Enter"], check=True)
        logger.info(f"Started Claude Code in {tmux_pane}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start Claude Code: {e}")
        return False


def stop_claude_code(tmux_pane: str, grace: int = DEFAULT_GRACE) -> bool:
    """Stop Claude Code in the given tmux pane.

    Sends Ctrl+C first, waits for grace period, then force-kills if needed.
    Never uses /exit (gets misinterpreted by TUI).
    """
    if not is_claude_running(tmux_pane):
        logger.info(f"Claude Code not running in {tmux_pane}")
        return True

    try:
        _run(["tmux", "send-keys", "-t", tmux_pane, "C-c"], check=True)
        logger.info(f"Sent Ctrl+C to {tmux_pane}, waiting {grace}s...")
    except subprocess.CalledProcessError:
        pass

    for _ in range(grace):
        time.sleep(1)
        if not is_claude_running(tmux_pane):
            logger.info(f"Claude Code stopped gracefully in {tmux_pane}")
            return True

    logger.warning(f"Grace period expired, force-killing claude in {tmux_pane}")
    result = _run([
        "tmux", "list-panes", "-t", tmux_pane, "-F", "#{pane_pid}"
    ])
    if result.returncode == 0:
        pane_pid = result.stdout.strip()
        if pane_pid:
            _run(["pkill", "-P", pane_pid, "-f", "claude"])

    time.sleep(1)
    stopped = not is_claude_running(tmux_pane)
    if stopped:
        logger.info(f"Claude Code force-killed in {tmux_pane}")
    else:
        logger.error(f"Failed to stop Claude Code in {tmux_pane}")
    return stopped


def nudge_lead(tmux_pane: str, message: str = "Check inbox for pending messages") -> None:
    """Send a text nudge to the lead's tmux pane."""
    try:
        _run(["tmux", "send-keys", "-t", tmux_pane, "-l", message], check=True)
        time.sleep(0.3)
        _run(["tmux", "send-keys", "-t", tmux_pane, "Enter"], check=True)
    except subprocess.CalledProcessError as e:
        logger.warning(f"Nudge failed: {e}")


def create_tmux_session(session_name: str) -> bool:
    """Create a new tmux session with a 'lead' window. Returns True on success."""
    if is_session_alive(session_name):
        logger.info(f"tmux session {session_name} already exists")
        return True

    result = _run([
        "tmux", "new-session", "-d", "-s", session_name, "-n", "lead"
    ])
    if result.returncode != 0:
        logger.error(f"Failed to create tmux session: {result.stderr.strip()}")
        return False

    logger.info(f"Created tmux session: {session_name}")
    return True


def kill_tmux_session(session_name: str) -> bool:
    """Kill a tmux session. Returns True if killed or already gone."""
    if not is_session_alive(session_name):
        return True

    result = _run(["tmux", "kill-session", "-t", session_name])
    killed = result.returncode == 0
    if killed:
        logger.info(f"Killed tmux session: {session_name}")
    else:
        logger.error(f"Failed to kill tmux session: {result.stderr.strip()}")
    return killed


def _allocate_port(registry) -> int:
    """Return the lowest unused ttyd port starting from 7700."""
    used = set()
    for name in registry.list_projects():
        info = registry.get(name)
        if info and info.ttyd_port:
            used.add(info.ttyd_port)
    port = 7700
    while port in used:
        port += 1
    return port


def start_ttyd(project_name: str, tmux_session: str, port: int) -> bool:
    """Start a ttyd process for a project on the given port.

    Skips in LOCAL_MODE (no ttyd on Mac).
    Writes PID to /tmp/ttyd-{project_name}.pid.
    """
    import os as _os
    if _os.getenv("LOCAL_MODE", "").lower() in ("true", "1", "yes"):
        logger.info(f"LOCAL_MODE: skipping ttyd for {project_name}")
        return False

    # Kill any existing ttyd on that port (safety)
    _run(["fuser", "-k", f"{port}/tcp"])

    try:
        proc = subprocess.Popen(
            [
                "ttyd", "-p", str(port), "-W",
                "--ping-interval", "30",
                "/usr/local/bin/project-attach", tmux_session,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        pid_file = f"/tmp/ttyd-{project_name}.pid"
        with open(pid_file, "w") as f:
            f.write(str(proc.pid))
        logger.info(f"Started ttyd for {project_name} on port {port} (pid {proc.pid})")
        return True
    except (OSError, FileNotFoundError) as e:
        logger.error(f"Failed to start ttyd for {project_name}: {e}")
        return False


def stop_ttyd(project_name: str) -> bool:
    """Stop the ttyd process for a project by reading its PID file."""
    import signal

    pid_file = f"/tmp/ttyd-{project_name}.pid"
    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        os.unlink(pid_file)
        logger.info(f"Stopped ttyd for {project_name} (pid {pid})")
        return True
    except FileNotFoundError:
        logger.debug(f"No ttyd PID file for {project_name}")
        return True
    except (ProcessLookupError, ValueError):
        # Process already gone or bad PID
        try:
            os.unlink(pid_file)
        except OSError:
            pass
        return True
    except OSError as e:
        logger.warning(f"Failed to stop ttyd for {project_name}: {e}")
        return False


def get_project_health(tmux_pane: str) -> dict:
    """Get health status for a project's Claude Code instance."""
    session = tmux_pane.split(":")[0]
    return {
        "session_alive": is_session_alive(session),
        "claude_running": is_claude_running(tmux_pane),
    }
