"""Use case: load conversation lines for a session (read-only, narrow read)."""

from __future__ import annotations

from orchestrator_v4.core.entities.interview_session_read_bundle import (
    InterviewConversationLine,
)
from orchestrator_v4.core.ports.interview_session_read_port import InterviewSessionReadPort


class LoadInterviewSessionConversations:
    def __init__(self, reader: InterviewSessionReadPort) -> None:
        self._reader = reader

    def execute(self, session_id: int) -> tuple[InterviewConversationLine, ...] | None:
        if session_id < 1:
            raise ValueError(f"session_id must be positive, got {session_id}")
        return self._reader.load_conversation_lines(session_id)
