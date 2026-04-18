"""
SQLite + filesystem adapter: resolves `agents.prompt_file` and reads the spine Markdown.

Parity target: same path-safety and read semantics as Orchestrator v3 `load_prompt` /
`get_system_prompt_for_agent`, without the legacy module-level prompt cache (explicit read path).
"""

from __future__ import annotations

import os

from orchestrator_v4.infrastructure.persistence.cached_prompt_file_reader import (
    CachedPromptFileReader,
)
from orchestrator_v4.infrastructure.persistence.sqlite_orchestrator_connection import (
    open_orchestrator_db,
)


class SqliteFilesystemPromptBodySource:
    """
    Reads `prompt_file` from the legacy `agents` table, then loads UTF-8 text from
    `prompts_root` / prompt_file with traversal protection.
    """

    def __init__(
        self,
        db_path: str,
        prompts_root: str,
        *,
        prompt_cache: CachedPromptFileReader | None = None,
    ) -> None:
        self._db_path = db_path
        self._prompts_root = os.path.realpath(prompts_root)
        self._prompt_cache = prompt_cache or CachedPromptFileReader(self._prompts_root)

    def load_for_agent(self, agent_id: int) -> str:
        relative = self._prompt_file_for_agent(agent_id)
        return self._prompt_cache.read_or_raise(relative)

    def invalidate_prompt_cache(self, agent_id: int | None = None) -> None:
        if agent_id is None:
            self._prompt_cache.invalidate()
            return
        relative = self._prompt_file_for_agent(agent_id)
        self._prompt_cache.invalidate(relative)

    def _prompt_file_for_agent(self, agent_id: int) -> str:
        with open_orchestrator_db(self._db_path) as conn:
            row = conn.execute(
                "SELECT prompt_file FROM agents WHERE id = ?",
                (agent_id,),
            ).fetchone()
        if not row:
            raise ValueError(f"Agent {agent_id} not found.")
        return str(row["prompt_file"])

