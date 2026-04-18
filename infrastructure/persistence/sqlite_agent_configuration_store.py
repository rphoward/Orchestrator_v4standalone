"""SQLite adapter for agent rows and per-agent ``config`` keys (v3-compatible)."""

from __future__ import annotations

import os

from orchestrator_v4.core.entities.agent_settings_row import AgentSettingsRow
from orchestrator_v4.core.ports.agent_configuration_store import AgentConfigurationStore
from orchestrator_v4.infrastructure.persistence.sqlite_orchestrator_connection import (
    open_orchestrator_db,
)


class SqliteAgentConfigurationStore(AgentConfigurationStore):
    """Agents table + ``config`` keys ``thinking_level_{id}``, ``temperature_{id}``, ``include_thoughts_{id}``."""

    def __init__(self, db_path: str, prompts_root: str) -> None:
        self._db_path = db_path
        self._prompts_root = os.path.realpath(prompts_root)

    def list_agents(self) -> list[AgentSettingsRow]:
        with open_orchestrator_db(self._db_path) as conn:
            rows = conn.execute(
                "SELECT id, name, prompt_file, model, is_synthesizer FROM agents ORDER BY id"
            ).fetchall()
        agents: list[AgentSettingsRow] = []
        for row in rows:
            prompt_file = str(row["prompt_file"] or "")
            try:
                prompt_body = self._read_prompt_file(prompt_file)
            except OSError:
                prompt_body = "(Prompt file not found)"
            entry: AgentSettingsRow = {
                "id": int(row["id"]),
                "name": str(row["name"] or ""),
                "prompt_file": prompt_file,
                "model": str(row["model"] or ""),
                "is_synthesizer": bool(row["is_synthesizer"]),
                "prompt": prompt_body,
            }
            agents.append(entry)
        return agents

    def _read_prompt_file(self, prompt_file: str) -> str:
        path = os.path.realpath(os.path.join(self._prompts_root, prompt_file))
        if not path.startswith(self._prompts_root + os.sep):
            raise OSError("path outside prompts root")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def update_agent(
        self, agent_id: int, name: str, model: str, prompt: str | None = None
    ) -> None:
        with open_orchestrator_db(self._db_path) as conn:
            row = conn.execute(
                "SELECT id, prompt_file FROM agents WHERE id = ?", (agent_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"Agent {agent_id} not found.")
            conn.execute(
                "UPDATE agents SET name = ?, model = ? WHERE id = ?",
                (name, model, agent_id),
            )
            conn.commit()

        if prompt is not None:
            if not isinstance(prompt, str):
                raise ValueError("Prompt must be a string.")
            rel = row["prompt_file"]
            prompt_path = os.path.realpath(os.path.join(self._prompts_root, rel))
            if not prompt_path.startswith(self._prompts_root + os.sep):
                raise ValueError("Invalid prompt file path.")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(prompt)

    def get_thinking_level(self, agent_id: int) -> str:
        key = f"thinking_level_{agent_id}"
        with open_orchestrator_db(self._db_path) as conn:
            r = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
        if not r or r["value"] is None:
            return ""
        return str(r["value"])

    def set_thinking_level(self, agent_id: int, level: str) -> None:
        val = level.upper() if level else ""
        key = f"thinking_level_{agent_id}"
        with open_orchestrator_db(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                (key, val),
            )
            conn.commit()

    def get_temperature(self, agent_id: int) -> str:
        key = f"temperature_{agent_id}"
        with open_orchestrator_db(self._db_path) as conn:
            r = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
        if not r or r["value"] is None:
            return ""
        return str(r["value"])

    def set_temperature(self, agent_id: int, temp: str) -> None:
        val = str(temp) if temp is not None and temp != "" else ""
        key = f"temperature_{agent_id}"
        with open_orchestrator_db(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                (key, val),
            )
            conn.commit()

    def get_include_thoughts(self, agent_id: int) -> bool:
        key = f"include_thoughts_{agent_id}"
        with open_orchestrator_db(self._db_path) as conn:
            r = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
        if not r or r["value"] is None:
            return False
        return str(r["value"]).lower() == "true"

    def set_include_thoughts(self, agent_id: int, value: bool) -> None:
        key = f"include_thoughts_{agent_id}"
        val = "true" if value else "false"
        with open_orchestrator_db(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                (key, val),
            )
            conn.commit()
