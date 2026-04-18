"""Port: run opening prompts for discovery agents on a new session."""

from __future__ import annotations

from typing import Protocol


class InterviewSessionInitializer(Protocol):
    def execute(self, session_id: int) -> dict[int, str]:
        """Return map of agent_id -> opening assistant text (or error placeholder)."""
        ...
