"""opencode agent lifecycle management via supervisord.

Each project runs `opencode serve` as a supervisord-managed process
with HTTP health checks and per-project isolation.
Sole runtime after Phase 5 migration. No tmux/Claude Code paths remain.
"""

import json
import logging
import os
import subprocess
import time

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
DEFAULT_MODEL = "openrouter/deepseek/deepseek-v4-pro"


def _run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def is_agent_running(serve_port: int) -> bool:
    try:
        resp = requests.get(f"http://127.0.0.1:{serve_port}/global/health", timeout=5)
        return resp.status_code == 200 and resp.json().get("healthy", False)
    except requests.RequestException:
        return False


def is_agent_responding(serve_port: int) -> bool:
    """Check if agent can actually process sessions (not just port open)."""
    if not is_agent_running(serve_port):
        return False
    try:
        resp = requests.post(
            f"http://127.0.0.1:{serve_port}/session",
            json={}, timeout=5)
        if resp.status_code in (200, 201):
            data = resp.json()
            sid = data.get("id", "")
            if sid:
                requests.delete(
                    f"http://127.0.0.1:{serve_port}/session/{sid}",
                    timeout=3)
            return True
    except Exception:
        pass
    return False


def _wait_for_healthy(serve_port: int, timeout: int = DEFAULT_TIMEOUT) -> bool:
    for _ in range(timeout):
        if is_agent_running(serve_port):
            return True
        time.sleep(1)
    return False


def _write_opencode_project_config(project_dir: str, linux_user: str) -> None:
    """Write a valid opencode.jsonc for the project directory."""
    config = {
        "$schema": "https://opencode.ai/config.json",
        "model": DEFAULT_MODEL,
        "permission": {"*": "allow"},
    }
    cfg_path = os.path.join(project_dir, "opencode.jsonc")
    with open(cfg_path, "w") as f:
        json.dump(config, f, indent=2)
    uid = int(subprocess.run(["id", "-u", linux_user], capture_output=True, text=True).stdout.strip())
    gid = int(subprocess.run(["id", "-g", linux_user], capture_output=True, text=True).stdout.strip())
    os.chown(cfg_path, uid, gid)


def _write_user_opencode_config(linux_user: str) -> None:
    """Write a valid user-level opencode.jsonc so serve doesn't pick up stale configs."""
    user_info = subprocess.run(
        ["id", "-u", linux_user], capture_output=True, text=True, check=True)
    uid = int(user_info.stdout.strip())
    gid = int(subprocess.run(
        ["id", "-g", linux_user], capture_output=True, text=True, check=True).stdout.strip())

    cfg_dir = f"/home/{linux_user}/.config/opencode"
    os.makedirs(cfg_dir, exist_ok=True)
    os.chown(cfg_dir, uid, gid)

    cfg_path = f"{cfg_dir}/opencode.jsonc"
    config = {
        "$schema": "https://opencode.ai/config.json",
        "model": DEFAULT_MODEL,
        "permission": {"*": "allow"},
    }
    with open(cfg_path, "w") as f:
        json.dump(config, f, indent=2)
    os.chown(cfg_path, uid, gid)


def _set_autostart(project_name: str, value: bool) -> None:
    config_path = f"/etc/supervisor/conf.d/proj-{project_name}.conf"
    if not os.path.exists(config_path):
        return
    val_str = "true" if value else "false"
    subprocess.run(
        ["sed", "-i", f"s/autostart=.*/autostart={val_str}/", config_path],
        capture_output=True, text=True)
    _run(["supervisorctl", "update"])


def _write_supervisor_config(project_name: str, serve_port: int, project_dir: str,
                             linux_user: str, extra_env: dict) -> None:
    env_vars = {
        "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY", ""),
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
        "RUBE_BEARER_TOKEN": os.environ.get("RUBE_BEARER_TOKEN", ""),
        "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", ""),
        "VERCEL_TOKEN": os.environ.get("VERCEL_TOKEN", ""),
        "UNIPILE_DSN": os.environ.get("UNIPILE_DSN", ""),
        "UNIPILE_API_KEY": os.environ.get("UNIPILE_API_KEY", ""),
        "COMPOSIO_API_KEY": os.environ.get("COMPOSIO_API_KEY", ""),
        "MYCELIUM_TARGET": os.environ.get("MYCELIUM_TARGET", "dev"),
    }
    if extra_env:
        env_vars.update(extra_env)

    env_entries = ",".join(f'{k}="{v}"' for k, v in env_vars.items() if v)
    env_str = f'PATH="/usr/local/bin:/usr/bin:/bin",{env_entries}' if env_entries else 'PATH="/usr/local/bin:/usr/bin:/bin"'

    config = (
        f"[program:proj-{project_name}]\n"
        f"command=opencode serve --port {serve_port}\n"
        f"user={linux_user}\n"
        f"directory={project_dir}\n"
        f"environment={env_str}\n"
        f"autostart=false\n"
        f"autorestart=true\n"
        f"startsecs=5\n"
        f"stopwaitsecs=10\n"
        f"MemoryMax=512M\n"
        f"stdout_logfile={project_dir}/delta-config/logs/opencode-stdout.log\n"
        f"stderr_logfile={project_dir}/delta-config/logs/opencode-stderr.log\n"
        f"redirect_stderr=false\n"
    )

    config_path = f"/etc/supervisor/conf.d/proj-{project_name}.conf"
    with open(config_path, "w") as f:
        f.write(config)
    logger.info(f"Wrote supervisor config: {config_path}")

    _write_opencode_project_config(project_dir, linux_user)
    _write_user_opencode_config(linux_user)


def start_agent_serve(project_name: str, serve_port: int, project_dir: str,
                      linux_user: str | None = None,
                      extra_env: dict | None = None) -> bool:
    user = linux_user or f"proj-{project_name}"
    env = extra_env or {}
    config_path = f"/etc/supervisor/conf.d/proj-{project_name}.conf"
    if not os.path.exists(config_path):
        _write_supervisor_config(project_name, serve_port, project_dir, user, env)
    _set_autostart(project_name, True)
    _run(["supervisorctl", "start", f"proj-{project_name}"], check=True)
    return _wait_for_healthy(serve_port)


def stop_agent_serve(project_name: str, keep_config: bool = True) -> bool:
    _run(["supervisorctl", "stop", f"proj-{project_name}"])
    if keep_config:
        _set_autostart(project_name, False)
    else:
        config_path = f"/etc/supervisor/conf.d/proj-{project_name}.conf"
        try:
            os.unlink(config_path)
        except FileNotFoundError:
            pass
        _run(["supervisorctl", "update"])
    return True


def nudge_agent(project_name: str, serve_port: int) -> None:
    nudge_file = f"/home/proj-{project_name}/{project_name}/delta-config/.nudge"
    open(nudge_file, "a").close()
    try:
        requests.get(f"http://127.0.0.1:{serve_port}/global/health", timeout=5)
    except requests.RequestException:
        pass


def get_agent_health(serve_port: int) -> dict:
    try:
        resp = requests.get(f"http://127.0.0.1:{serve_port}/global/health", timeout=5)
        return {"agent_running": True, "response_ms": resp.elapsed.total_seconds() * 1000}
    except requests.RequestException:
        return {"agent_running": False, "response_ms": 0}