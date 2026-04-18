"""Port: create a session from a v3-compatible ``orchestrator_export`` JSON dict."""

from __future__ import annotations

from typing import Any, Protocol


class InterviewSessionImporter(Protocol):
    def execute(self, data: dict[str, Any]) -> int:
        """
        Insert session + conversations + routing logs; return new session id.

        Expected v3-style export shape (top level): ``session`` (object),
        ``conversations`` (list of objects with ``agent_id`` and ``messages``),
        ``routing_logs`` (list). Nested message/session fields stay loosely typed;
        see ``SqliteInterviewSessionImporter`` for the fields read at import time.
        """
        ...
