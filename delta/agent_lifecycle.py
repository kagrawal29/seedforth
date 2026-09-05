"""opencode agent lifecycle management via supervisord.

Each project runs `opencode serve` as a supervisord-managed process
with HTTP health checks, file-based inbox/outbox, and per-project isolation.
Replaces the tmux-based lifecycle.py for opencode projects.
"""

import logging
import os
import subprocess
import time

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30


def _run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def is_agent_running(serve_port: int) -> bool:
    try:
        resp = requests.get(f"http://127.0.0.1:{serve_port}/global/health", timeout=5)
        return resp.status_code == 200 and resp.json().get("healthy", False)
    except requests.RequestException:
        return False


def _wait_for_healthy(serve_port: int, timeout: int = DEFAULT_TIMEOUT) -> bool:
    for _ in range(timeout):
        if is_agent_running(serve_port):
            return True
        time.sleep(1)
    return False


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
        "LOCAL_NEO4J_URI": os.environ.get("LOCAL_NEO4J_URI", "bolt://localhost:7687"),
        "LOCAL_NEO4J_USER": os.environ.get("LOCAL_NEO4J_USER", "neo4j"),
        "LOCAL_NEO4J_PASSWORD": os.environ.get("LOCAL_NEO4J_PASSWORD", ""),
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
        f"autostart=true\n"
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


def _set_autostart(project_name: str, value: bool) -> None:
    config_path = f"/etc/supervisor/conf.d/proj-{project_name}.conf"
    if not os.path.exists(config_path):
        return
    val_str = "true" if value else "false"
    subprocess.run(
        ["sed", "-i", f"s/autostart=.*/autostart={val_str}/", config_path],
        capture_output=True, text=True)
    _run(["supervisorctl", "update"])


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
