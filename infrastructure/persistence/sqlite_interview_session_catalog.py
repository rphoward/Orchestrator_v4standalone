"""
SQLite adapter: interview session headlines (`sessions` table only).

Parity with legacy list/create/update/delete metadata; does not load messages.
"""

from __future__ import annotations

import sqlite3

from orchestrator_v4.core.entities.interview_session_summary import InterviewSessionSummary
from orchestrator_v4.infrastructure.persistence.sqlite_orchestrator_connection import (
    open_orchestrator_db,
)


def _row_to_summary(row: sqlite3.Row) -> InterviewSessionSummary:
    return InterviewSessionSummary(
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


class SqliteInterviewSessionCatalog:
    """Implements InterviewSessionCatalog for the legacy `orchestrator.db`."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def list_summaries(self) -> list[InterviewSessionSummary]:
        with open_orchestrator_db(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, name, client_name, summary, current_agent_id,
                       stage1_complete, stage2_complete, stage3_complete, stage4_complete,
                       created_at, updated_at
                FROM sessions
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [_row_to_summary(r) for r in rows]

    def create(self, name: str, client_name: str) -> InterviewSessionSummary:
        with open_orchestrator_db(self._db_path) as conn:
            cur = conn.execute(
                "INSERT INTO sessions (name, client_name) VALUES (?, ?)",
                (name, client_name),
            )
            new_id = int(cur.lastrowid)
            conn.commit()
        return self._get_by_id_required(new_id)

    def get_summary(self, session_id: int) -> InterviewSessionSummary | None:
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
        return _row_to_summary(row)

    def update(
        self, session_id: int, name: str, client_name: str, summary: str
    ) -> InterviewSessionSummary:
        with open_orchestrator_db(self._db_path) as conn:
            cur = conn.execute(
                """
                UPDATE sessions
                SET name = ?, client_name = ?, summary = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (name, client_name, summary, session_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                raise ValueError(f"Session {session_id} not found.")
        return self._get_by_id_required(session_id)

    def delete(self, session_id: int) -> None:
        with open_orchestrator_db(self._db_path) as conn:
            cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
            if cur.rowcount == 0:
                raise ValueError(f"Session {session_id} not found.")

    def _get_by_id_required(self, session_id: int) -> InterviewSessionSummary:
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
            raise ValueError(f"Session {session_id} not found.")
        return _row_to_summary(row)
