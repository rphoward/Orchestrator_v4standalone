"""Port: read per-agent override rows from persistence."""

from __future__ import annotations

from typing import Protocol

from orchestrator_v4.core.entities.agent_override import AgentOverride


class AgentOverrideReader(Protocol):
    """Loads override snapshots for the given agent ids (order preserved)."""

    def read_overrides(self, agent_ids: list[int]) -> list[AgentOverride]:
        ...
