"""
SQLite adapter: turn-level session state for ``ConductInterviewTurn``.

Reads/writes the legacy ``orchestrator.db`` tables (sessions, conversations,
routing_logs, agents) using incremental INSERT/UPDATE rather than v3's
delete-and-rewrite pattern.  Agent roster includes system prompts loaded from
``prompts_root`` and router hints extracted from them (same convention as v3).
"""

from __future__ import annotations

import os
import re
import sqlite3
from collections.abc import Sequence
from datetime import datetime, timezone

from orchestrator_v4.core.entities.interview_turn import (
    ConversationAppend,
    InterviewTurnAgentRosterEntry,
    RoutingLogAppend,
    TurnContext,
    TurnConversationLine,
    TurnRoutingLogLine,
)
from orchestrator_v4.core.ports.prompt_body_source import PromptBodySource
from orchestrator_v4.infrastructure.persistence.cached_prompt_file_reader import (
    CachedPromptFileReader,
)
from orchestrator_v4.infrastructure.persistence.sqlite_agent_override_reader import (
    parse_agent_override,
)
from orchestrator_v4.infrastructure.persistence.sqlite_orchestrator_connection import (
    open_orchestrator_db,
)

_ROUTER_HINT_RE = re.compile(r"## ROUTER HINT\n(.*?)(?=\n##|$)", re.DOTALL)


def _extract_router_hint(system_prompt: str, agent_name: str) -> str:
    match = _ROUTER_HINT_RE.search(system_prompt)
    return match.group(1).strip() if match else agent_name


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class SqliteInterviewSessionTurnStore:
    """Implements ``InterviewSessionTurnStore`` against the legacy orchestrator.db."""

    def __init__(
        self,
        db_path: str,
        prompts_root: str,
        *,
        prompt_cache: CachedPromptFileReader | None = None,
        prompt_body_source: PromptBodySource | None = None,
    ) -> None:
        self._db_path = db_path
        self._prompts_root = os.path.realpath(prompts_root)
        self._prompt_cache = prompt_cache or CachedPromptFileReader(self._prompts_root)
        self._prompt_body_source = prompt_body_source

    # ── Port methods ──────────────────────────────────────────────

    def load_turn_context(self, session_id: int) -> TurnContext:
        with open_orchestrator_db(self._db_path) as conn:
            session_row = conn.execute(
                """
                SELECT id, name, current_agent_id,
                       stage1_complete, stage2_complete,
                       stage3_complete, stage4_complete,
                       stage_progress
                FROM sessions WHERE id = ?
                """,
                (session_id,),
            ).fetchone()
            if not session_row:
                raise ValueError(f"Session {session_id} not found")

            msg_rows = conn.execute(
                """
                SELECT agent_id, role, content, message_type, timestamp
                FROM conversations
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()

            log_rows = conn.execute(
                """
                SELECT input_text, agent_id, agent_name, reason, timestamp
                FROM routing_logs
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()

            agent_rows = conn.execute(
                "SELECT id, name, prompt_file, model, is_synthesizer FROM agents ORDER BY id"
            ).fetchall()

            config_rows: list[sqlite3.Row] = []
            if agent_rows:
                agent_ids = [int(r["id"]) for r in agent_rows]
                config_keys: list[str] = []
                for aid in agent_ids:
                    config_keys.extend(
                        [
                            f"thinking_level_{aid}",
                            f"temperature_{aid}",
                            f"include_thoughts_{aid}",
                        ]
                    )
                placeholders = ",".join("?" * len(config_keys))
                try:
                    config_rows = conn.execute(
                        f"SELECT key, value FROM config WHERE key IN ({placeholders})",
                        config_keys,
                    ).fetchall()
                except sqlite3.OperationalError:
                    # Older test DBs or partial setups may not have `config` yet.
                    config_rows = []

        messages = tuple(
            TurnConversationLine(
                agent_id=int(r["agent_id"]),
                role="assistant" if r["role"] == "model" else str(r["role"]),
                content=str(r["content"]),
                message_type=str(r["message_type"] or "chat"),
                timestamp=str(r["timestamp"] or ""),
            )
            for r in msg_rows
        )

        routing_logs = tuple(
            TurnRoutingLogLine(
                input_text=str(r["input_text"]),
                agent_id=int(r["agent_id"]),
                agent_name=str(r["agent_name"]),
                reason=str(r["reason"] or ""),
                timestamp=str(r["timestamp"] or ""),
            )
            for r in log_rows
        )

        by_key = {str(r["key"]): str(r["value"]) for r in config_rows}
        agents = self._build_roster(agent_rows, by_key)

        return TurnContext(
            session_id=int(session_row["id"]),
            name=str(session_row["name"]),
            current_agent_id=int(session_row["current_agent_id"] or 1),
            stage1_complete=bool(session_row["stage1_complete"]),
            stage2_complete=bool(session_row["stage2_complete"]),
            stage3_complete=bool(session_row["stage3_complete"]),
            stage4_complete=bool(session_row["stage4_complete"]),
            messages=messages,
            routing_logs=routing_logs,
            agents=agents,
            stage_progress_json=str(session_row["stage_progress"] or ""),
        )

    def append_messages(
        self, session_id: int, messages: Sequence[ConversationAppend]
    ) -> None:
        with open_orchestrator_db(self._db_path) as conn:
            for m in messages:
                ts = m.timestamp or _utc_timestamp()
                conn.execute(
                    """
                    INSERT INTO conversations
                        (session_id, agent_id, role, content, message_type, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, m.agent_id, m.role, m.content, m.message_type, ts),
                )
            conn.commit()

    def append_routing_log(
        self, session_id: int, log: RoutingLogAppend
    ) -> None:
        ts = log.timestamp or _utc_timestamp()
        with open_orchestrator_db(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO routing_logs
                    (session_id, input_text, agent_id, agent_name, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, log.input_text, log.agent_id, log.agent_name, log.reason, ts),
            )
            conn.commit()

    def update_session_state(
        self,
        session_id: int,
        *,
        current_agent_id: int | None = None,
        stage_flags: dict[int, bool] | None = None,
        name: str | None = None,
        stage_progress_json: str | None = None,
    ) -> None:
        sets: list[str] = []
        params: list[object] = []

        if current_agent_id is not None:
            sets.append("current_agent_id = ?")
            params.append(current_agent_id)
        if stage_flags is not None:
            for stage_num in (1, 2, 3, 4):
                if stage_num in stage_flags:
                    sets.append(f"stage{stage_num}_complete = ?")
                    params.append(int(stage_flags[stage_num]))
        if name is not None:
            sets.append("name = ?")
            params.append(name)
        if stage_progress_json is not None:
            sets.append("stage_progress = ?")
            params.append(stage_progress_json)

        if not sets:
            return

        sets.append("updated_at = CURRENT_TIMESTAMP")
        params.append(session_id)

        sql = f"UPDATE sessions SET {', '.join(sets)} WHERE id = ?"
        with open_orchestrator_db(self._db_path) as conn:
            cur = conn.execute(sql, params)
            conn.commit()
            if cur.rowcount == 0:
                raise ValueError(f"Session {session_id} not found")

    def invalidate_prompt_cache(self, agent_id: int | None = None) -> None:
        if self._prompt_body_source is not None:
            self._prompt_body_source.invalidate_prompt_cache(agent_id)
            return
        if agent_id is None:
            self._prompt_cache.invalidate()
            return
        relative = self._prompt_file_for_agent(agent_id)
        self._prompt_cache.invalidate(relative)

    # ── Roster loading ────────────────────────────────────────────

    def _build_roster(
        self, agent_rows: list[sqlite3.Row], by_key: dict[str, str]
    ) -> tuple[InterviewTurnAgentRosterEntry, ...]:
        entries: list[InterviewTurnAgentRosterEntry] = []
        for r in agent_rows:
            aid = int(r["id"])
            agent_name = str(r["name"])
            prompt_file = str(r["prompt_file"])
            model = str(r["model"] or "")
            if self._prompt_body_source is not None:
                system_prompt = self._prompt_body_source.load_for_agent(aid)
            else:
                system_prompt = self._load_prompt_file(prompt_file)
            router_hint = _extract_router_hint(system_prompt, agent_name)
            override = parse_agent_override(aid, by_key)

            entries.append(
                InterviewTurnAgentRosterEntry(
                    id=aid,
                    name=agent_name,
                    system_prompt=system_prompt,
                    router_hint=router_hint,
                    model=model,
                    thinking_level=override.thinking_level,
                    temperature=override.temperature,
                    include_thoughts=override.include_thoughts,
                    is_synthesizer=bool(r["is_synthesizer"]),
                )
            )
        return tuple(entries)

    def _load_prompt_file(self, relative: str) -> str:
        return self._prompt_cache.read_or_empty(relative)

    def _prompt_file_for_agent(self, agent_id: int) -> str:
        with open_orchestrator_db(self._db_path) as conn:
            row = conn.execute(
                "SELECT prompt_file FROM agents WHERE id = ?",
                (agent_id,),
            ).fetchone()
        if not row:
            raise ValueError(f"Agent {agent_id} not found")
        return str(row["prompt_file"])
