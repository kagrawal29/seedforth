"""Message router -- resolves Discord messages to projects.

In the Discord model, each project has its own channel (1:1 mapping).
DMs are resolved by project ownership.
"""

from typing import Optional

from delta.registry import Registry


class Router:
    """Routes Discord messages to the correct project."""

    def __init__(self, registry: Registry):
        self.registry = registry

    def resolve_channel(self, channel_id: str) -> Optional[str]:
        """Resolve a Discord channel to a project name.

        Returns the project name or None if no project is bound to this channel.
        """
        project = self.registry.find_by_discord_channel(channel_id)
        if project:
            return project.name
        return None

    def resolve_dm(self, discord_user_id: str) -> Optional[str] | list[str]:
        """Resolve a DM to a project.

        Returns:
            str -- project name (user owns exactly one project)
            None -- user owns no projects
            list[str] -- user owns multiple projects (ambiguous)
        """
        projects = self.registry.find_by_owner(discord_user_id)
        if len(projects) == 0:
            return None
        if len(projects) == 1:
            return projects[0].name
        return [p.name for p in projects]
