"""Port: load full Markdown interview instructions for a runtime agent."""

from __future__ import annotations

from typing import Protocol


class PromptBodySource(Protocol):
    """
    Returns the prompt body (system instruction text) for the given agent id.
    Implementations resolve the spine file and read from storage — not part of this contract.
    """

    def load_for_agent(self, agent_id: int) -> str:
        """Load interview prompt text for this agent. Raises ValueError if missing or invalid."""
        ...
