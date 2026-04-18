"""SQLite adapter for ``prompt_templates`` (parity with v3 ``SQLitePromptRepository``)."""

from __future__ import annotations

import sqlite3
from typing import Any

from orchestrator_v4.core.entities.prompt_template_row import (
    PromptTemplateRow,
    PromptTemplateUpdateFields,
)
from orchestrator_v4.core.ports.prompt_template_store import PromptTemplateStore
from orchestrator_v4.infrastructure.persistence.sqlite_orchestrator_connection import (
    open_orchestrator_db,
)


def _row_to_prompt_template(row: sqlite3.Row) -> PromptTemplateRow:
    d = dict(row)
    tid = d.get("target_agent_id")
    return {
        "id": int(d["id"]),
        "name": str(d["name"] or ""),
        "description": str(d.get("description") or ""),
        "target_agent_id": int(tid) if tid is not None else None,
        "content": str(d["content"] or ""),
        "is_system": int(d["is_system"] if d.get("is_system") is not None else 0),
        "created_at": str(d["created_at"] or ""),
        "updated_at": str(d["updated_at"] or ""),
    }


class SqlitePromptTemplateStore(PromptTemplateStore):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def list_templates(self) -> list[PromptTemplateRow]:
        with open_orchestrator_db(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM prompt_templates ORDER BY created_at DESC"
            ).fetchall()
        return [_row_to_prompt_template(r) for r in rows]

    def create_template(
        self,
        name: str,
        content: str,
        *,
        description: str = "",
        target_agent_id: int | None = None,
    ) -> PromptTemplateRow:
        with open_orchestrator_db(self._db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO prompt_templates
                    (name, description, target_agent_id, content, is_system)
                VALUES (?, ?, ?, ?, 0)
                """,
                (name, description, target_agent_id, content),
            )
            tid = cur.lastrowid
            conn.commit()
        out = self.get_template(tid)
        if out is None:
            raise RuntimeError("prompt_templates row missing after insert")
        return out

    def get_template(self, template_id: int) -> PromptTemplateRow | None:
        with open_orchestrator_db(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM prompt_templates WHERE id = ?", (template_id,)
            ).fetchone()
        return _row_to_prompt_template(row) if row else None

    def update_template(
        self,
        template_id: int,
        fields: PromptTemplateUpdateFields,
    ) -> PromptTemplateRow | None:
        """
        Only keys present in ``fields`` are applied (v3-style partial PUT).
        ``target_agent_id`` may be ``None`` to clear the column.
        """
        updates: list[str] = []
        params: list[Any] = []
        if "name" in fields and fields["name"] is not None:
            updates.append("name = ?")
            params.append(fields["name"])
        if "description" in fields and fields["description"] is not None:
            updates.append("description = ?")
            params.append(fields["description"])
        if "content" in fields and fields["content"] is not None:
            updates.append("content = ?")
            params.append(fields["content"])
        if "target_agent_id" in fields:
            updates.append("target_agent_id = ?")
            params.append(fields["target_agent_id"])

        if not updates:
            return self.get_template(template_id)

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(template_id)
        sql = f"UPDATE prompt_templates SET {', '.join(updates)} WHERE id = ?"
        with open_orchestrator_db(self._db_path) as conn:
            conn.execute(sql, tuple(params))
            conn.commit()
        return self.get_template(template_id)

    def delete_template(self, template_id: int) -> None:
        with open_orchestrator_db(self._db_path) as conn:
            conn.execute(
                "DELETE FROM prompt_templates WHERE id = ? AND is_system = 0",
                (template_id,),
            )
            conn.commit()
