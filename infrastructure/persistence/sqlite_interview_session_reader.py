"""
SQLite adapter: read session headline + conversations + routing_logs (export path).

Parity with legacy `get_by_id` read shape; does not import v3 application code.
"""

from __future__ import annotations

import sqlite3

from orchestrator_v4.core.entities.interview_session_read_bundle import (
    InterviewConversationLine,
    InterviewRoutingLogLine,
    InterviewSessionReadBundle,
    InterviewSessionReadHeadline,
)
from orchestrator_v4.core.ports.interview_session_read_port import InterviewSessionReadPort
from orchestrator_v4.infrastructure.persistence.sqlite_orchestrator_connection import (
    open_orchestrator_db,
)


def _normalize_role(stored: str) -> str:
    """Match v3 rehydration: ``model`` → ``assistant``."""
    if stored == "model":
        return "assistant"
    return stored


class SqliteInterviewSessionReader(InterviewSessionReadPort):
    """Loads `InterviewSessionReadBundle` from the legacy `orchestrator.db` schema."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def _session_exists(self, conn: sqlite3.Connection, session_id: int) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        return row is not None

    def _fetch_conversation_lines(
        self, conn: sqlite3.Connection, session_id: int
    ) -> list[InterviewConversationLine]:
        msg_rows = conn.execute(
            """
            SELECT agent_id, role, content, message_type, timestamp
            FROM conversations
            WHERE session_id = ?
            ORDER BY timestamp ASC
            """,
            (session_id,),
        ).fetchall()
        lines: list[InterviewConversationLine] = []
        for m in msg_rows:
            lines.append(
                InterviewConversationLine(
                    agent_id=int(m["agent_id"]),
                    role=_normalize_role(str(m["role"])),
                    content=str(m["content"]),
                    message_type=str(m["message_type"] or "chat"),
                    timestamp=str(m["timestamp"] or ""),
                )
            )
        return lines

    def _fetch_routing_log_lines(
        self, conn: sqlite3.Connection, session_id: int
    ) -> list[InterviewRoutingLogLine]:
        log_rows = conn.execute(
            """
            SELECT input_text, agent_id, agent_name, reason, timestamp
            FROM routing_logs
            WHERE session_id = ?
            ORDER BY timestamp ASC
            """,
            (session_id,),
        ).fetchall()
        logs: list[InterviewRoutingLogLine] = []
        for lg in log_rows:
            logs.append(
                InterviewRoutingLogLine(
                    input_text=str(lg["input_text"]),
                    agent_id=int(lg["agent_id"]),
                    agent_name=str(lg["agent_name"]),
                    reason=str(lg["reason"] or ""),
                    timestamp=str(lg["timestamp"] or ""),
                )
            )
        return logs

    def load_conversation_lines(
        self, session_id: int
    ) -> tuple[InterviewConversationLine, ...] | None:
        with open_orchestrator_db(self._db_path) as conn:
            if not self._session_exists(conn, session_id):
                return None
            return tuple(self._fetch_conversation_lines(conn, session_id))

    def load_routing_log_lines(
        self, session_id: int
    ) -> tuple[InterviewRoutingLogLine, ...] | None:
        with open_orchestrator_db(self._db_path) as conn:
            if not self._session_exists(conn, session_id):
                return None
            return tuple(self._fetch_routing_log_lines(conn, session_id))

    def load_bundle(self, session_id: int) -> InterviewSessionReadBundle | None:
        with open_orchestrator_db(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT id, name, client_name, summary, current_agent_id,
                       stage1_complete, stage2_complete, stage3_complete, stage4_complete,
                       created_at, updated_at
                FROM sessions WHERE id = ?
                """,
                (session_id,),
            ).fetchone()
            if not row:
                return None

            headline = InterviewSessionReadHeadline(
                id=int(row["id"]),
                name=str(row["name"]),
                client_name=str(row["client_name"] or ""),
                summary=str(row["summary"] or ""),
                current_agent_id=int(row["current_agent_id"] or 1),
                stage1_complete=bool(row["stage1_complete"]),
                stage2_complete=bool(row["stage2_complete"]),
                stage3_complete=bool(row["stage3_complete"]),
                stage4_complete=bool(row["stage4_complete"]),
                created_at=str(row["created_at"] or ""),
                updated_at=str(row["updated_at"] or ""),
            )

            lines = self._fetch_conversation_lines(conn, session_id)
            logs = self._fetch_routing_log_lines(conn, session_id)

        return InterviewSessionReadBundle(
            headline=headline,
            conversation_lines=tuple(lines),
            routing_log_lines=tuple(logs),
        )
