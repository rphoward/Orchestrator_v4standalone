"""Use case: batch read of per-agent thinking / temperature / include-thoughts overrides."""

from __future__ import annotations

from orchestrator_v4.core.entities.agent_override import AgentOverride
from orchestrator_v4.core.ports.agent_override_reader import AgentOverrideReader

# Aligns with legacy GET /api/config/agent-overrides caps and defaults.
_DEFAULT_AGENT_IDS: tuple[int, ...] = (1, 2, 3, 4)
_MAX_BATCH_SIZE = 32


class ReadAgentOverrides:
    """Orchestrates validation and delegates persistence to AgentOverrideReader."""

    def __init__(self, reader: AgentOverrideReader) -> None:
        self._reader = reader

    def execute(self, agent_ids: list[int] | None = None) -> list[AgentOverride]:
        """
        When agent_ids is None, defaults to agents 1–4.
        When agent_ids is [], returns [] (no work), matching empty batch semantics.
        """
        if agent_ids is None:
            resolved = list(_DEFAULT_AGENT_IDS)
        else:
            resolved = list(agent_ids)

        if not resolved:
            return []

        if len(resolved) > _MAX_BATCH_SIZE:
            raise ValueError(
                f"Too many agent ids (max {_MAX_BATCH_SIZE}), got {len(resolved)}"
            )

        for aid in resolved:
            if not isinstance(aid, int) or aid < 1:
                raise ValueError(
                    f"Invalid agent id (positive integers only): {aid!r}"
                )

        return self._reader.read_overrides(resolved)
