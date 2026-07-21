"""AgentRunner interface for dual-runtime dispatch.

OpencodeServeRunner delegates to agent_lifecycle.py (opencode + supervisord).
ClaudeCodeRunner delegates to the existing lifecycle.py (tmux + Claude Code).

During migration (Phases 1-5), both runtimes coexist. This interface lets the
provisioner and bridge code target either runtime without branching on runtime
type at every call site.
"""

from typing import Protocol

from delta.registry import ProjectInfo


class AgentRunner(Protocol):
    """Interface for agent process management.

    Implemented by OpencodeServeRunner and ClaudeCodeRunner.
    """

    def start(self, project: ProjectInfo) -> bool: ...

    def stop(self, project: ProjectInfo, keep_config: bool = True) -> bool: ...

    def is_running(self, project: ProjectInfo) -> bool: ...

    def health(self, project: ProjectInfo) -> dict: ...

    def nudge(self, project: ProjectInfo) -> None: ...


class OpencodeServeRunner:
    """Wraps agent_lifecycle.py functions. Primary runtime after Phase 5."""

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


class ClaudeCodeRunner:
    """Wraps existing lifecycle.py functions. Legacy, removed in Phase 5."""

    def start(self, project: ProjectInfo) -> bool:
        from delta.lifecycle import start_claude_code
        return start_claude_code(
            project.project_dir, project.tmux_lead_pane, project.linux_user
        )

    def stop(self, project: ProjectInfo, keep_config: bool = True) -> bool:
        from delta.lifecycle import stop_claude_code
        return stop_claude_code(project.tmux_lead_pane)

    def is_running(self, project: ProjectInfo) -> bool:
        from delta.lifecycle import is_claude_running
        return is_claude_running(project.tmux_lead_pane)

    def health(self, project: ProjectInfo) -> dict:
        from delta.lifecycle import get_project_health
        return get_project_health(project.tmux_lead_pane)

    def nudge(self, project: ProjectInfo) -> None:
        from delta.lifecycle import nudge_lead
        return nudge_lead(project.tmux_lead_pane)


_OPENCODE_RUNNER = OpencodeServeRunner()
_CLAUDE_RUNNER = ClaudeCodeRunner()


def get_runner(project: ProjectInfo) -> AgentRunner:
    return _OPENCODE_RUNNER if project.runtime == "opencode" else _CLAUDE_RUNNER
