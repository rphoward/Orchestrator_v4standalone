"""Use case: delete an interview session (cascades to conversations/routing_logs in DB)."""

from __future__ import annotations

from orchestrator_v4.core.ports.interview_session_catalog import InterviewSessionCatalog


class DeleteInterviewSession:
    def __init__(self, catalog: InterviewSessionCatalog) -> None:
        self._catalog = catalog

    def execute(self, session_id: int) -> None:
        if not isinstance(session_id, int) or session_id < 1:
            raise ValueError(
                f"Invalid session id (positive integers only): {session_id!r}"
            )
        self._catalog.delete(session_id)
