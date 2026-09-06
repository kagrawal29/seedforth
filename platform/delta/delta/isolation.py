"""Linux user isolation -- create/delete OS users for project sandboxing."""

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_ROOT_OPENCODE_CONFIG_DIR = Path("/root/.config/opencode")
_ROOT_OPENCODE_JSONC = _ROOT_OPENCODE_CONFIG_DIR / "opencode.jsonc"
_AUTH_TEMPLATE = Path("/opt/delta/auth.json.template")


def linux_username(project_name: str) -> str:
    """Return the Linux username for a project."""
    return f"proj-{project_name}"


def ensure_opencode_config_shared() -> None:
    """Make /root/.config/opencode traversable and readable by project users.

    Called once during server setup. Allows project users to read the shared
    opencode config via symlink from their home dirs.
    Single-tenant server -- all users are Delta-managed sandboxes.
    """
    if not _ROOT_OPENCODE_CONFIG_DIR.exists():
        logger.warning("/root/.config/opencode does not exist -- run opencode setup first")
        return

    subprocess.run(["chmod", "711", "/root"], capture_output=True, text=True)
    subprocess.run(["chmod", "711", "/root/.config"], capture_output=True, text=True)
    subprocess.run(["chmod", "755", str(_ROOT_OPENCODE_CONFIG_DIR)],
                   capture_output=True, text=True)
    subprocess.run(["chmod", "644", str(_ROOT_OPENCODE_JSONC)],
                   capture_output=True, text=True)
    logger.info("opencode config dir permissions set for sharing")


def create_user(project_name: str) -> str:
    """Create a Linux user for a project. Returns username.

    Creates /home/proj-{name} with 2770 permissions (setgid delta group).
    Sets up opencode config symlink and per-user auth.json.
    Raises RuntimeError on failure.
    """
    username = linux_username(project_name)
    home = f"/home/{username}"

    result = subprocess.run(
        ["sudo", "useradd", "-m", "-d", home, "-s", "/bin/bash", username],
        capture_output=True, text=True,
    )
    if result.returncode == 9:
        logger.info(f"User {username} already exists, reusing")
    elif result.returncode != 0:
        raise RuntimeError(f"useradd failed: {result.stderr.strip()}")

    subprocess.run(["sudo", "chown", f"{username}:delta", home],
                   capture_output=True, text=True)
    subprocess.run(["sudo", "chmod", "2770", home], capture_output=True, text=True)

    user_opencode_config_dir = f"{home}/.config/opencode"
    subprocess.run(["sudo", "-u", username, "mkdir", "-p", user_opencode_config_dir],
                   capture_output=True, text=True)
    if _ROOT_OPENCODE_JSONC.exists():
        user_opencode_jsonc = f"{user_opencode_config_dir}/opencode.jsonc"
        subprocess.run(
            ["sudo", "-u", username, "ln", "-sf",
             str(_ROOT_OPENCODE_JSONC), user_opencode_jsonc],
            capture_output=True, text=True)
        ensure_opencode_config_shared()

    user_opencode_data_dir = f"{home}/.local/share/opencode"
    subprocess.run(["sudo", "-u", username, "mkdir", "-p", user_opencode_data_dir],
                   capture_output=True, text=True)
    user_auth_json = f"{user_opencode_data_dir}/auth.json"
    if _AUTH_TEMPLATE.exists():
        shutil.copy(str(_AUTH_TEMPLATE), user_auth_json)
        subprocess.run(["sudo", "chmod", "600", user_auth_json],
                       capture_output=True, text=True)
        subprocess.run(["sudo", "chown", f"{username}:{username}", user_auth_json],
                       capture_output=True, text=True)

    logger.info(f"Created user {username} with home {home}")
    return username


def delete_user(username: str) -> bool:
    """Delete a Linux user and their home directory. Returns True on success."""
    result = subprocess.run(
        ["userdel", "-r", username],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        if "does not exist" in result.stderr:
            logger.warning(f"User {username} does not exist")
            return False
        raise RuntimeError(f"userdel failed: {result.stderr.strip()}")

    logger.info(f"Deleted user {username}")
    return True


def user_exists(username: str) -> bool:
    """Check if a Linux user exists."""
    result = subprocess.run(
        ["id", username],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def run_as_user(username: str, command: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run a command as a specific Linux user.

    Uses sudo -u to switch user context.
    """
    cmd = ["sudo", "-u", username, "bash", "-c", command]
    kwargs = {"capture_output": True, "text": True}
    if cwd:
        kwargs["cwd"] = cwd
    return subprocess.run(cmd, **kwargs)
