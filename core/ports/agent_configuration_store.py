"""Port: agent rows in SQLite plus per-agent config keys (thinking, temperature, thoughts)."""

from __future__ import annotations

import abc

from orchestrator_v4.core.entities.agent_settings_row import AgentSettingsRow


class AgentConfigurationStore(abc.ABC):
    """Read and write agent configuration (name, model, per-agent settings)."""

    @abc.abstractmethod
    def list_agents(self) -> list[AgentSettingsRow]:
        """
        Return all agents as dicts with id, name, model, prompt_file, is_synthesizer,
        and prompt (markdown body loaded for Settings UI; placeholder text if missing).
        """

    @abc.abstractmethod
    def update_agent(
        self, agent_id: int, name: str, model: str, prompt: str | None = None
    ) -> None:
        """Update agent name, model, and optionally prompt text."""

    @abc.abstractmethod
    def get_thinking_level(self, agent_id: int) -> str:
        """Return thinking level for agent (empty string if not set)."""

    @abc.abstractmethod
    def set_thinking_level(self, agent_id: int, level: str) -> None:
        """Set thinking level for agent."""

    @abc.abstractmethod
    def get_temperature(self, agent_id: int) -> str:
        """Return temperature for agent (empty string if not set)."""

    @abc.abstractmethod
    def set_temperature(self, agent_id: int, temp: str) -> None:
        """Set temperature for agent."""

    @abc.abstractmethod
    def get_include_thoughts(self, agent_id: int) -> bool:
        """Return include_thoughts flag for agent."""

    @abc.abstractmethod
    def set_include_thoughts(self, agent_id: int, value: bool) -> None:
        """Set include_thoughts flag for agent."""
