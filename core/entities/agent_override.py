"""Per-agent LLM override snapshot (thinking level, temperature, include-thoughts)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentOverride:
    """Effective per-agent overrides as stored in legacy config (string temps match v3)."""

    agent_id: int
    thinking_level: str
    temperature: str
    include_thoughts: bool

    def __post_init__(self) -> None:
        if self.agent_id < 1:
            raise ValueError(f"agent_id must be positive, got {self.agent_id}")
