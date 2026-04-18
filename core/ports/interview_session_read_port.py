"""Port: load session + messages + routing logs for export (read-only)."""

from __future__ import annotations

from typing import Protocol

from orchestrator_v4.core.entities.interview_session_read_bundle import (
    InterviewConversationLine,
    InterviewRoutingLogLine,
    InterviewSessionReadBundle,
)


class InterviewSessionReadPort(Protocol):
    """Load a persisted interview session bundle from the legacy DB."""

    def load_bundle(self, session_id: int) -> InterviewSessionReadBundle | None:
        """Return ``None`` if no session row exists for ``session_id``."""
        ...

    def load_conversation_lines(
        self, session_id: int
    ) -> tuple[InterviewConversationLine, ...] | None:
        """Return ``None`` if no session row exists; else conversation lines (possibly empty)."""
        ...

    def load_routing_log_lines(
        self, session_id: int
    ) -> tuple[InterviewRoutingLogLine, ...] | None:
        """Return ``None`` if no session row exists; else routing log lines (possibly empty)."""
        ...
