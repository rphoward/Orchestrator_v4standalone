"""Use case: load interview session data for export (read-only)."""

from __future__ import annotations

from orchestrator_v4.core.entities.interview_session_read_bundle import InterviewSessionReadBundle
from orchestrator_v4.core.ports.interview_session_read_port import InterviewSessionReadPort
from orchestrator_v4.core.use_cases.refresh_stage_tracking_before_report import (
    RefreshStageTrackingBeforeReport,
)


class LoadInterviewSessionForExport:
    def __init__(
        self,
        reader: InterviewSessionReadPort,
        stage_tracking_refresh: RefreshStageTrackingBeforeReport | None = None,
    ) -> None:
        self._reader = reader
        self._stage_tracking_refresh = stage_tracking_refresh

    def execute(self, session_id: int) -> InterviewSessionReadBundle | None:
        if session_id < 1:
            raise ValueError(f"session_id must be positive, got {session_id}")
        if self._stage_tracking_refresh is not None:
            try:
                self._stage_tracking_refresh.execute(session_id, trigger="export")
            except ValueError:
                return None
        return self._reader.load_bundle(session_id)
