"""
SQLite + filesystem: effective interview prompt body with optional DB template override.

C2 precedence (documented contract, covered by tests):
- If ``prompt_templates`` has at least one row with ``target_agent_id = agent_id`` whose
  ``content`` is non-empty after Python ``str.strip()``, the **latest** row wins
  (by ``updated_at``, then ``id``).
  That row's ``content`` is the effective prompt — no spine file read (supports drafts
  that are not yet written to disk; v3 UI "apply" still writes the file separately).
- Otherwise the effective prompt is the spine file referenced by ``agents.prompt_file``,
  read through :class:`CachedPromptFileReader` (same path safety as
  :class:`SqliteFilesystemPromptBodySource`).

If the ``prompt_templates`` table is missing (older DBs), template resolution is skipped
and behavior matches file-only loading.
"""

from __future__ import annotations

import os
import sqlite3

from orchestrator_v4.infrastructure.persistence.cached_prompt_file_reader import (
    CachedPromptFileReader,
)
from orchestrator_v4.infrastructure.persistence.sqlite_filesystem_prompt_body_source import (
    SqliteFilesystemPromptBodySource,
)
from orchestrator_v4.infrastructure.persistence.sqlite_orchestrator_connection import (
    open_orchestrator_db,
)


class SqliteTemplateAwarePromptBodySource:
    """
    Resolves the effective system prompt for ``LoadInterviewPromptBody`` and shared
    turn-store wiring. Delegates file reads to :class:`SqliteFilesystemPromptBodySource`.
    """

    def __init__(
        self,
        db_path: str,
        prompts_root: str,
        *,
        prompt_cache: CachedPromptFileReader | None = None,
    ) -> None:
        self._db_path = db_path
        self._file_source = SqliteFilesystemPromptBodySource(
            db_path,
            prompts_root,
            prompt_cache=prompt_cache,
        )

    def load_for_agent(self, agent_id: int) -> str:
        content = self._targeted_template_content(agent_id)
        if content is not None:
            return content
        return self._file_source.load_for_agent(agent_id)

    def invalidate_prompt_cache(self, agent_id: int | None = None) -> None:
        self._file_source.invalidate_prompt_cache(agent_id)

    def _targeted_template_content(self, agent_id: int) -> str | None:
        try:
            with open_orchestrator_db(self._db_path) as conn:
                row = conn.execute(
                    """
                    SELECT content FROM prompt_templates
                    WHERE target_agent_id = ?
                    ORDER BY COALESCE(updated_at, created_at) DESC, id DESC
                    LIMIT 1
                    """,
                    (agent_id,),
                ).fetchone()
        except sqlite3.OperationalError:
            return None
        if not row:
            return None
        text = str(row["content"])
        if not text.strip():
            return None
        return text
