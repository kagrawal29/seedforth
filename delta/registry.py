"""Project registry -- CRUD operations on a JSON file of registered projects."""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class ProjectInfo:
    """Data class for a registered project."""

    __slots__ = (
        "name", "project_dir", "data_dir", "tmux_session",
        "tmux_lead_pane", "nudge_prefix", "github_repo",
        "linux_user", "discord_channel_id", "owner_discord_id", "created_at",
        "is_dream_space", "status", "last_activity", "ttyd_port",
        "project_type", "unipile_account_id",
        "runtime", "serve_port", "web_port", "supervisor_program", "session_id",
        "role",
    )

    def __init__(self, name: str, project_dir: str, data_dir: str,
                 tmux_session: str, tmux_lead_pane: str,
                 nudge_prefix: str = "", github_repo: str = "",
                 linux_user: str = "", discord_channel_id: str = "",
                 owner_discord_id: str = "", created_at: str = "",
                 is_dream_space: bool = False, status: str = "active",
                 last_activity: str = "", ttyd_port: int = 0,
                 project_type: str = "standard",
                 unipile_account_id: str = "",
                 runtime: str = "opencode",
                  serve_port: int = 0,
                  web_port: int = 0,
                   supervisor_program: str = "",
                   session_id: str = "",
                   role: str = ""):
        self.name = name
        self.project_dir = project_dir
        self.data_dir = data_dir
        self.tmux_session = tmux_session
        self.tmux_lead_pane = tmux_lead_pane
        self.nudge_prefix = nudge_prefix or f"{data_dir}/inbox"
        self.github_repo = github_repo
        self.linux_user = linux_user
        self.discord_channel_id = discord_channel_id
        self.owner_discord_id = owner_discord_id
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.is_dream_space = is_dream_space
        self.status = status
        self.last_activity = last_activity or self.created_at
        self.ttyd_port = ttyd_port
        self.project_type = project_type
        self.unipile_account_id = unipile_account_id
        self.runtime = runtime
        self.serve_port = serve_port
        self.web_port = web_port
        self.supervisor_program = supervisor_program
        self.session_id = session_id
        self.role = role

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "project_dir": self.project_dir,
            "data_dir": self.data_dir,
            "tmux_session": self.tmux_session,
            "tmux_lead_pane": self.tmux_lead_pane,
            "nudge_prefix": self.nudge_prefix,
            "github_repo": self.github_repo,
            "linux_user": self.linux_user,
            "discord_channel_id": self.discord_channel_id,
            "owner_discord_id": self.owner_discord_id,
            "created_at": self.created_at,
            "is_dream_space": self.is_dream_space,
            "status": self.status,
            "last_activity": self.last_activity,
            "ttyd_port": self.ttyd_port,
            "project_type": self.project_type,
            "unipile_account_id": self.unipile_account_id,
            "runtime": self.runtime,
            "serve_port": self.serve_port,
            "web_port": self.web_port,
            "supervisor_program": self.supervisor_program,
            "session_id": self.session_id,
            "role": self.role,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProjectInfo":
        return cls(
            name=d["name"],
            project_dir=d["project_dir"],
            data_dir=d["data_dir"],
            tmux_session=d["tmux_session"],
            tmux_lead_pane=d["tmux_lead_pane"],
            nudge_prefix=d.get("nudge_prefix", ""),
            github_repo=d.get("github_repo", ""),
            linux_user=d.get("linux_user", ""),
            discord_channel_id=d.get("discord_channel_id", ""),
            owner_discord_id=d.get("owner_discord_id", ""),
            created_at=d.get("created_at", ""),
            is_dream_space=d.get("is_dream_space", False),
            status=d.get("status", "active"),
            last_activity=d.get("last_activity", ""),
            ttyd_port=d.get("ttyd_port", 0),
            project_type=d.get("project_type", "standard"),
            unipile_account_id=d.get("unipile_account_id", ""),
            runtime=d.get("runtime", "claude"),
            serve_port=d.get("serve_port", 0),
            web_port=d.get("web_port", 0),
            supervisor_program=d.get("supervisor_program", ""),
            session_id=d.get("session_id", ""),
            role=d.get("role", ""),
        )


class Registry:
    """Thread-safe project registry backed by a JSON file."""

    def __init__(self, path: str | Path = "delta-registry.json"):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._projects: dict[str, ProjectInfo] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
            for name, d in data.get("projects", {}).items():
                self._projects[name] = ProjectInfo.from_dict(d)
        except (json.JSONDecodeError, OSError, KeyError):
            pass

    def _save(self) -> None:
        data = {"projects": {n: p.to_dict() for n, p in self._projects.items()}}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2) + "\n")

    def add(self, project: ProjectInfo) -> None:
        with self._lock:
            self._projects[project.name] = project
            self._save()

    def remove(self, name: str) -> bool:
        with self._lock:
            if name not in self._projects:
                return False
            del self._projects[name]
            self._save()
            return True

    def get(self, name: str) -> Optional[ProjectInfo]:
        with self._lock:
            return self._projects.get(name)

    def list_projects(self) -> list[str]:
        with self._lock:
            return list(self._projects.keys())

    def find_by_discord_channel(self, channel_id: str) -> Optional[ProjectInfo]:
        """Find the project bound to a Discord channel."""
        with self._lock:
            for project in self._projects.values():
                if project.discord_channel_id == channel_id:
                    return project
            return None

    def find_by_owner(self, discord_user_id: str) -> list[ProjectInfo]:
        """Find all projects owned by a Discord user."""
        with self._lock:
            return [
                p for p in self._projects.values()
                if p.owner_discord_id == discord_user_id
            ]

    def find_persistent_by_owner(self, discord_user_id: str) -> "ProjectInfo | None":
        """Find the persistent agent for a Discord user, if any."""
        with self._lock:
            for p in self._projects.values():
                if (p.owner_discord_id == discord_user_id
                        and p.project_type == "persistent"
                        and p.status in ("active", "hibernated")):
                    return p
            return None

    def find_personal_by_owner(self, discord_user_id: str) -> "ProjectInfo | None":
        """Find the personal DM agent for a Discord user, if any."""
        with self._lock:
            for p in self._projects.values():
                if (p.owner_discord_id == discord_user_id
                        and p.project_type == "personal_dm"
                        and p.status in ("active", "hibernated")):
                    return p
            return None

    def find_linkedin_by_owner(self, discord_user_id: str) -> "ProjectInfo | None":
        """Find the linkedin agent for a Discord user, if any."""
        with self._lock:
            for p in self._projects.values():
                if (p.owner_discord_id == discord_user_id
                        and p.project_type == "linkedin"
                        and p.status in ("active", "hibernated")):
                    return p
            return None

    def find_hibernated_by_owner(self, discord_user_id: str) -> list[ProjectInfo]:
        """Find hibernated dream spaces owned by a Discord user."""
        with self._lock:
            return [
                p for p in self._projects.values()
                if p.owner_discord_id == discord_user_id
                and p.status == "hibernated"
            ]

    def update(self, name: str, **kwargs) -> bool:
        """Update individual fields on a project. Returns False if not found.

        Reloads from disk before applying so changes made by the steering
        executor (a separate process) are preserved, not clobbered. The
        resource manager calls this every 60s; without the reload its
        in-memory snapshot would revert external hibernations.
        """
        with self._lock:
            self._load()
            project = self._projects.get(name)
            if not project:
                return False
            for key, value in kwargs.items():
                if hasattr(project, key):
                    setattr(project, key, value)
            self._save()
            return True

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._projects)
