"""SQLite adapter: reads per-agent override keys from legacy `config` table."""

from __future__ import annotations

import sqlite3
from typing import Mapping

from orchestrator_v4.core.entities.agent_override import AgentOverride
from orchestrator_v4.infrastructure.persistence.sqlite_orchestrator_connection import (
    open_orchestrator_db,
)


class SqliteAgentOverrideReader:
    """
    Reads keys `thinking_level_{id}`, `temperature_{id}`, `include_thoughts_{id}`
    from the same `config` table layout used by Orchestrator v3.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def read_overrides(self, agent_ids: list[int]) -> list[AgentOverride]:
        if not agent_ids:
            return []

        keys: list[str] = []
        for aid in agent_ids:
            keys.extend(
                [
                    f"thinking_level_{aid}",
                    f"temperature_{aid}",
                    f"include_thoughts_{aid}",
                ]
            )

        placeholders = ",".join("?" * len(keys))
        query = f"SELECT key, value FROM config WHERE key IN ({placeholders})"

        with open_orchestrator_db(self._db_path) as conn:
            rows = conn.execute(query, keys).fetchall()

        by_key: dict[str, str] = {row["key"]: row["value"] for row in rows}

        out: list[AgentOverride] = []
        for aid in agent_ids:
            out.append(parse_agent_override(aid, by_key))
        return out


def parse_agent_override(agent_id: int, by_key: Mapping[str, str]) -> AgentOverride:
    thinking = by_key.get(f"thinking_level_{agent_id}")
    temp = by_key.get(f"temperature_{agent_id}")
    inc_raw = by_key.get(f"include_thoughts_{agent_id}", "false")

    thinking_s = thinking if thinking is not None else ""
    temp_s = temp if temp is not None else ""
    include_thoughts = str(inc_raw).lower() == "true"

    return AgentOverride(
        agent_id=agent_id,
        thinking_level=thinking_s,
        temperature=temp_s,
        include_thoughts=include_thoughts,
    )
