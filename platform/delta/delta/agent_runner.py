"""AgentRunner interface -- opencode serve (sole runtime after Phase 5).

All legacy ClaudeCodeRunner and tmux dispatch has been removed.
"""

from typing import Protocol

from delta.registry import ProjectInfo


class AgentRunner(Protocol):
    """Interface for agent process management."""

    def start(self, project: ProjectInfo) -> bool: ...

    def stop(self, project: ProjectInfo, keep_config: bool = True) -> bool: ...

    def is_running(self, project: ProjectInfo) -> bool: ...

    def health(self, project: ProjectInfo) -> dict: ...

    def nudge(self, project: ProjectInfo) -> None: ...


class OpencodeServeRunner:
    """Wraps agent_lifecycle.py functions."""

    def start(self, project: ProjectInfo) -> bool:
        from delta.agent_lifecycle import start_agent_serve
        return start_agent_serve(
            project.name, project.serve_port,
            project.project_dir, project.linux_user, {}
        )

    def stop(self, project: ProjectInfo, keep_config: bool = True) -> bool:
        from delta.agent_lifecycle import stop_agent_serve
        return stop_agent_serve(project.name, keep_config=keep_config)

    def is_running(self, project: ProjectInfo) -> bool:
        from delta.agent_lifecycle import is_agent_running
        return is_agent_running(project.serve_port)

    def health(self, project: ProjectInfo) -> dict:
        from delta.agent_lifecycle import get_agent_health
        return get_agent_health(project.serve_port)

    def nudge(self, project: ProjectInfo) -> None:
        from delta.agent_lifecycle import nudge_agent
        return nudge_agent(project.name, project.serve_port)


_RUNNER = OpencodeServeRunner()


def get_runner(project: ProjectInfo) -> AgentRunner:
    return _RUNNER