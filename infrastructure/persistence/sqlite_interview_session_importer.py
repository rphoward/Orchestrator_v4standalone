"""SQLite adapter: import a session from v3 export JSON."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from orchestrator_v4.core.ports.interview_session_importer import InterviewSessionImporter
from orchestrator_v4.infrastructure.persistence.sqlite_orchestrator_connection import (
    open_orchestrator_db,
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _coerce_ts(raw: object | None) -> str:
    if raw is None:
        return _utc_timestamp()
    s = str(raw).strip()
    return s if s else _utc_timestamp()


def _normalize_role(role: str) -> str:
    r = (role or "user").strip().lower()
    if r == "model":
        return "assistant"
    if r in ("user", "assistant", "system"):
        return r
    return "user"


class SqliteInterviewSessionImporter(InterviewSessionImporter):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def execute(self, data: dict[str, Any]) -> int:
        sess = data.get("session") or {}
        old_name = sess.get("name", "Imported Session")
        new_name = f"[Imported] {old_name}"

        with open_orchestrator_db(self._db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO sessions (
                    name, client_name, summary, current_agent_id,
                    stage1_complete, stage2_complete, stage3_complete, stage4_complete
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_name,
                    str(sess.get("client_name", "") or ""),
                    str(sess.get("summary", "") or ""),
                    int(sess.get("current_agent_id", 1) or 1),
                    int(bool(sess.get("stage1_complete", False))),
                    int(bool(sess.get("stage2_complete", False))),
                    int(bool(sess.get("stage3_complete", False))),
                    int(bool(sess.get("stage4_complete", False))),
                ),
            )
            new_id = int(cur.lastrowid)

            for conv in data.get("conversations") or []:
                agent_id = int(conv.get("agent_id", 0) or 0)
                if agent_id < 1:
                    continue
                for m in conv.get("messages") or []:
                    role = _normalize_role(str(m.get("role", "user")))
                    content = str(m.get("content", ""))
                    msg_type = str(m.get("message_type", "chat") or "chat")
                    ts = _coerce_ts(m.get("timestamp"))
                    conn.execute(
                        """
                        INSERT INTO conversations
                            (session_id, agent_id, role, content, message_type, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (new_id, agent_id, role, content, msg_type, ts),
                    )

            for log in data.get("routing_logs") or []:
                conn.execute(
                    """
                    INSERT INTO routing_logs
                        (session_id, input_text, agent_id, agent_name, reason, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_id,
                        str(log.get("input_text", "")),
                        int(log.get("agent_id", 1) or 1),
                        str(log.get("agent_name", "")),
                        str(log.get("reason", "")),
                        _coerce_ts(log.get("timestamp")),
                    ),
                )

            conn.commit()

        return new_id
