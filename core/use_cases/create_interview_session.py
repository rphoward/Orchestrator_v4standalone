"""Use case: create a new interview session row."""

from __future__ import annotations

from orchestrator_v4.core.entities.interview_session_summary import InterviewSessionSummary
from orchestrator_v4.core.ports.interview_session_catalog import InterviewSessionCatalog


class CreateInterviewSession:
    def __init__(self, catalog: InterviewSessionCatalog) -> None:
        self._catalog = catalog

    def execute(self, name: str, client_name: str = "") -> InterviewSessionSummary:
        n = (name or "").strip()
        if not n:
            raise ValueError("Session name must be non-empty.")
        c = client_name if client_name is not None else ""
        return self._catalog.create(n, c)
