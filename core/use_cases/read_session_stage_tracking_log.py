"""Read persisted stage tracking observations (SQLite only; no judge calls)."""

from __future__ import annotations

import json

from orchestrator_v4.core.ports.interview_session_turn_store import (
    InterviewSessionTurnStore,
)


class ReadSessionStageTrackingLog:
    def __init__(self, turn_store: InterviewSessionTurnStore) -> None:
        self._turn_store = turn_store

    def execute(self, session_id: int) -> dict[str, object]:
        if session_id < 1:
            raise ValueError(f"session_id must be positive, got {session_id}")
        ctx = self._turn_store.load_turn_context(session_id)
        raw = (ctx.stage_tracking_log_json or "").strip()
        if not raw:
            return {"entries": ()}
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return {"entries": ()}
        if not isinstance(parsed, list):
            return {"entries": ()}
        return {"entries": tuple(parsed)}
