"""Linux user isolation -- create/delete OS users for project sandboxing."""

import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Root's Claude auth dir and config -- shared with project users via symlink
_ROOT_CLAUDE_DIR = Path("/root/.claude")
_ROOT_CLAUDE_JSON = Path("/root/.claude.json")


def linux_username(project_name: str) -> str:
    """Return the Linux username for a project."""
    return f"proj-{project_name}"


def ensure_claude_auth_shared() -> None:
    """Make /root/.claude traversable by project users.

    Called once during server setup. Allows project users to read
    Claude Code auth via symlink from their home dirs.
    Single-tenant server -- all users are Delta-managed sandboxes.
    """
    if not _ROOT_CLAUDE_DIR.exists():
        logger.warning("/root/.claude does not exist -- Claude Code not authenticated yet")
        return

    # Allow traversal into /root (not listing, just path resolution)
    subprocess.run(["chmod", "711", "/root"], capture_output=True, text=True)
    # Make .claude dir and contents readable/writable by project users
    subprocess.run(["chmod", "-R", "a+rwX", str(_ROOT_CLAUDE_DIR)],
                   capture_output=True, text=True)
    logger.info("Claude auth dir permissions set for sharing")


def create_user(project_name: str) -> str:
    """Create a Linux user for a project. Returns username.

    Creates /home/proj-{name} with 750 permissions.
    Symlinks ~/.claude -> /root/.claude so Claude Code finds auth.
    Raises RuntimeError on failure.
    """
    username = linux_username(project_name)
    home = f"/home/{username}"

    result = subprocess.run(
        ["useradd", "-m", "-d", home, "-s", "/bin/bash", username],
        capture_output=True, text=True,
    )
    if result.returncode == 9:
        # User already exists (exit code 9) -- idempotent, continue
        logger.info(f"User {username} already exists, reusing")
    elif result.returncode != 0:
        raise RuntimeError(f"useradd failed: {result.stderr.strip()}")

    subprocess.run(["chmod", "750", home], capture_output=True, text=True)

    # Symlink Claude auth so project user inherits root's Max subscription
    user_claude = Path(home) / ".claude"
    if _ROOT_CLAUDE_DIR.exists() and not user_claude.exists():
        subprocess.run(["ln", "-s", str(_ROOT_CLAUDE_DIR), str(user_claude)],
                       capture_output=True, text=True)
        ensure_claude_auth_shared()

    # Write a concrete .claude.json with theme and onboarding flags.
    # Can't symlink because Claude Code overwrites it on first boot.
    # Merge with root's .claude.json if it exists, then add required keys.
    user_claude_json = Path(home) / ".claude.json"
    if Path(home).exists() and not user_claude_json.exists():
        base_config = {}
        if _ROOT_CLAUDE_JSON.exists():
            try:
                base_config = json.loads(_ROOT_CLAUDE_JSON.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        base_config.setdefault("theme", "dark")
        base_config.setdefault("hasCompletedOnboarding", True)
        user_claude_json.write_text(json.dumps(base_config, indent=2))
        subprocess.run(["chown", f"{username}:", str(user_claude_json)],
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
