"""Use case: update session headline fields (name, client_name, summary)."""

from __future__ import annotations

from orchestrator_v4.core.entities.interview_session_summary import InterviewSessionSummary
from orchestrator_v4.core.ports.interview_session_catalog import InterviewSessionCatalog


class UpdateInterviewSession:
    def __init__(self, catalog: InterviewSessionCatalog) -> None:
        self._catalog = catalog

    def execute(
        self,
        session_id: int,
        name: str | None,
        client_name: str | None = None,
        summary_text: str | None = None,
    ) -> InterviewSessionSummary:
        if not isinstance(session_id, int) or session_id < 1:
            raise ValueError(
                f"Invalid session id (positive integers only): {session_id!r}"
            )
        if name is not None and not isinstance(name, str):
            raise ValueError("Session name must be a string when provided.")
        if client_name is not None and not isinstance(client_name, str):
            raise ValueError("Client name must be a string when provided.")
        if summary_text is not None and not isinstance(summary_text, str):
            raise ValueError("Session summary must be a string when provided.")
        current = self._catalog.get_summary(session_id)
        if current is None:
            raise ValueError(f"Session {session_id} not found.")

        merged_name = (name.strip() if name is not None else current.name)
        if not merged_name:
            raise ValueError("Session name must be non-empty.")
        merged_client = (
            client_name if client_name is not None else current.client_name
        )
        merged_summary = (
            summary_text if summary_text is not None else current.summary
        )
        return self._catalog.update(
            session_id, merged_name, merged_client, merged_summary
        )
