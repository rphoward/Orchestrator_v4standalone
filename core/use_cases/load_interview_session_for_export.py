"""Use case: load interview session data for export (read-only)."""

from __future__ import annotations

from orchestrator_v4.core.entities.interview_session_read_bundle import InterviewSessionReadBundle
from orchestrator_v4.core.ports.interview_session_read_port import InterviewSessionReadPort


class LoadInterviewSessionForExport:
    def __init__(self, reader: InterviewSessionReadPort) -> None:
        self._reader = reader

    def execute(self, session_id: int) -> InterviewSessionReadBundle | None:
        if session_id < 1:
            raise ValueError(f"session_id must be positive, got {session_id}")
        return self._reader.load_bundle(session_id)
