"""Use case: load routing log lines for a session (read-only, narrow read)."""

from __future__ import annotations

from orchestrator_v4.core.entities.interview_session_read_bundle import (
    InterviewRoutingLogLine,
)
from orchestrator_v4.core.ports.interview_session_read_port import InterviewSessionReadPort


class LoadInterviewSessionRoutingLogs:
    def __init__(self, reader: InterviewSessionReadPort) -> None:
        self._reader = reader

    def execute(self, session_id: int) -> tuple[InterviewRoutingLogLine, ...] | None:
        if session_id < 1:
            raise ValueError(f"session_id must be positive, got {session_id}")
        return self._reader.load_routing_log_lines(session_id)
