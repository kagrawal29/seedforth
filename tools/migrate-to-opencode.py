"""System-level migration: convert all active Claude Code projects to opencode runtime.

Reads delta-registry.json, migrates each active project to opencode serve + supervisord.
Safe — skips already-migrated projects, backs up registry before touching anything.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REGISTRY_PATH = os.environ.get("DELTA_REGISTRY_PATH", "/opt/delta/delta-registry.json")
AUTH_TEMPLATE = "/opt/delta/auth.json.template"
GLOBAL_OP ENCODE_CONFIG = "/root/.config/opencode/opencode.jsonc"
SUPERVISOR_CONF_DIR = "/etc/supervisor/conf.d"

SERVE_PORT_RANGE = (7700, 7899)
WEB_PORT_RANGE = (7900, 8099)


def load_registry():
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def save_registry(registry):
    backup_path = f"{REGISTRY_PATH}.bak.{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    shutil.copy(REGISTRY_PATH, backup_path)
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)
    print(f"Registry saved (backup: {backup_path})")


def all_used_ports(registry):
    ports = set()
    for p in registry.get("projects", {}).values():
        for k in ("ttyd_port", "serve_port", "web_port"):
            if p.get(k):
                ports.add(int(p[k]))
    return ports


def allocate_port(used_ports, range_start, range_end):
    for port in range(range_start, range_end + 1):
        if port not in used_ports:
            used_ports.add(port)
            return port
    raise RuntimeError(f"No free ports in range {range_start}-{range_end}")


def stop_tmux_project(project):
    name = project["name"]
    session = project.get("tmux_session", f"proj-{name}")
    subprocess.run(["tmux", "send-keys", "-t", f"{session}:lead", "C-c"],
                   capture_output=True)
    time.sleep(2)
    subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)
    print(f"  Stopped tmux session: {session}")


def setup_user_config(project):
    linux_user = project["linux_user"]
    home = f"/home/{linux_user}"

    for d in [f"{home}/.config/opencode", f"{home}/.local/share/opencode"]:
        os.makedirs(d, exist_ok=True)

    subprocess.run(["ln", "-sf", GLOBAL_OP ENCODE_CONFIG,
                    f"{home}/.config/opencode/opencode.jsonc"], check=True)

    if os.path.exists(AUTH_TEMPLATE):
        shutil.copy(AUTH_TEMPLATE, f"{home}/.local/share/opencode/auth.json")
        os.chmod(f"{home}/.local/share/opencode/auth.json", 0o600)

    subprocess.run(["chown", "-R", f"{linux_user}:{linux_user}",
                    f"{home}/.config", f"{home}/.local"], check=True)
    print(f"  User config set up for {linux_user}")


def write_project_opencode_config(project):
    project_dir = project["project_dir"]
    config_path = os.path.join(project_dir, "opencode.jsonc")

    config = {
        "model": "deepseek/deepseek-v4-pro",
        "permission": {"*": "allow"},
        "mcp": {
            "rube": {
                "type": "remote",
                "url": "https://rube.app/mcp",
                "headers": {"Authorization": "Bearer {env:RUBE_BEARER_TOKEN}"}
            }
        }
    }

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    gitignore_path = os.path.join(project_dir, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path) as f:
            content = f.read()
        if "opencode.jsonc" not in content:
            with open(gitignore_path, "a") as f:
                f.write("\nopencode.jsonc\n.opencode/\n")
    else:
        with open(gitignore_path, "w") as f:
            f.write("opencode.jsonc\n.opencode/\n")

    linux_user = project["linux_user"]
    subprocess.run(["chown", f"{linux_user}:delta", config_path], check=True)
    print(f"  Wrote opencode.jsonc + .gitignore update")


def write_supervisor_config(project, serve_port):
    name = project["name"]
    project_dir = project["project_dir"]
    linux_user = project["linux_user"]

    env_vars = {
        "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY", ""),
        "RUBE_BEARER_TOKEN": os.environ.get("RUBE_BEARER_TOKEN", ""),
        "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", ""),
        "VERCEL_TOKEN": os.environ.get("VERCEL_TOKEN", ""),
        "UNIPILE_DSN": os.environ.get("UNIPILE_DSN", ""),
        "UNIPILE_API_KEY": os.environ.get("UNIPILE_API_KEY", ""),
        "COMPOSIO_API_KEY": os.environ.get("COMPOSIO_API_KEY", ""),
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
        "MYCELIUM_TARGET": os.environ.get("MYCELIUM_TARGET", "dev"),
    }
    env_str = ",".join(f'{k}="{v}"' for k, v in env_vars.items() if v)

    config = f"""[program:proj-{name}]
command=opencode serve --port {serve_port}
user={linux_user}
directory={project_dir}
environment=PATH="/usr/local/bin:/usr/bin:/bin",{env_str}
autostart=true
autorestart=true
startsecs=5
stopwaitsecs=10
memory_max=512M
stdout_logfile={project_dir}/delta-config/logs/opencode-stdout.log
stderr_logfile={project_dir}/delta-config/logs/opencode-stderr.log
"""

    conf_path = os.path.join(SUPERVISOR_CONF_DIR, f"proj-{name}.conf")
    with open(conf_path, "w") as f:
        f.write(config)
    print(f"  Wrote supervisor config: {conf_path}")


def start_agent(project_name, serve_port):
    subprocess.run(["supervisorctl", "update"], check=True)
    subprocess.run(["supervisorctl", "start", f"proj-{project_name}"], check=True)

    for _ in range(30):
        time.sleep(1)
        try:
            import urllib.request
            resp = urllib.request.urlopen(
                f"http://127.0.0.1:{serve_port}/global/health", timeout=2)
            if resp.status == 200:
                data = json.loads(resp.read())
                if data.get("healthy"):
                    print(f"  Agent healthy on port {serve_port}")
                    return True
        except Exception:
            pass

    print(f"  WARNING: Agent did not become healthy within 30s")
    return False


def migrate():
    registry = load_registry()
    projects = registry.get("projects", {})
    used_ports = all_used_ports(registry)
    migrated = 0
    skipped = 0
    failed = []

    for name, project in sorted(projects.items()):
        runtime = project.get("runtime", "claude")
        status = project.get("status", "active")

        if runtime == "opencode":
            print(f"\n{name}: already opencode, skipping")
            skipped += 1
            continue

        if status != "active" and status != "hibernated":
            print(f"\n{name}: status={status}, skipping")
            skipped += 1
            continue

        print(f"\n{'='*50}")
        print(f"Migrating: {name} (runtime: {runtime})")
        print(f"{'='*50}")

        try:
            if status == "active":
                stop_tmux_project(project)

            setup_user_config(project)

            serve_port = allocate_port(used_ports, *SERVE_PORT_RANGE)
            project["serve_port"] = serve_port
            if not project.get("web_port"):
                project["web_port"] = allocate_port(used_ports, *WEB_PORT_RANGE)

            write_project_opencode_config(project)
            write_supervisor_config(project, serve_port)
            project["supervisor_program"] = f"proj-{name}"
            project["runtime"] = "opencode"

            if status == "active":
                start_agent(name, serve_port)

            migrated += 1
            print(f"  SUCCESS: {name} migrated to opencode")

        except Exception as e:
            print(f"  FAILED: {name} — {e}")
            failed.append(name)

    save_registry(registry)

    print(f"\n{'='*50}")
    print(f"MIGRATION COMPLETE")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped:  {skipped}")
    print(f"  Failed:   {len(failed)}")
    if failed:
        print(f"  Failed projects: {', '.join(failed)}")


if __name__ == "__main__":
    migrate()
