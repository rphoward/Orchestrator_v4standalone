"""Use case: list interview session summaries (newest first)."""

from __future__ import annotations

from orchestrator_v4.core.entities.interview_session_summary import InterviewSessionSummary
from orchestrator_v4.core.ports.interview_session_catalog import InterviewSessionCatalog


class ListInterviewSessions:
    def __init__(self, catalog: InterviewSessionCatalog) -> None:
        self._catalog = catalog

    def execute(self) -> list[InterviewSessionSummary]:
        return self._catalog.list_summaries()
