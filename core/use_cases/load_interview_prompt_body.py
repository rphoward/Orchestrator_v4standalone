"""Use case: load the interview prompt body for one runtime agent."""

from __future__ import annotations

from orchestrator_v4.core.ports.prompt_body_source import PromptBodySource


class LoadInterviewPromptBody:
    """Validates agent id and delegates to PromptBodySource."""

    def __init__(self, source: PromptBodySource) -> None:
        self._source = source

    def execute(self, agent_id: int) -> str:
        if not isinstance(agent_id, int) or agent_id < 1:
            raise ValueError(
                f"Invalid agent id (positive integers only): {agent_id!r}"
            )
        return self._source.load_for_agent(agent_id)
