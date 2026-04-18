"""Port: list and mutate interview session rows (metadata only)."""

from __future__ import annotations

from typing import Protocol

from orchestrator_v4.core.entities.interview_session_summary import InterviewSessionSummary


class InterviewSessionCatalog(Protocol):
    """SQLite-backed session headlines — same `sessions` table as Orchestrator v3."""

    def list_summaries(self) -> list[InterviewSessionSummary]:
        """Newest first (`ORDER BY updated_at DESC`)."""
        ...

    def create(self, name: str, client_name: str) -> InterviewSessionSummary:
        """Insert a session row; DB assigns id and defaults."""
        ...

    def get_summary(self, session_id: int) -> InterviewSessionSummary | None:
        """Return one session row by id, or None if missing."""
        ...

    def update(
        self, session_id: int, name: str, client_name: str, summary: str
    ) -> InterviewSessionSummary:
        """Replace name, client_name, and summary; touches `updated_at`."""
        ...

    def delete(self, session_id: int) -> None:
        """Delete session row; child rows cascade in legacy schema."""
        ...
