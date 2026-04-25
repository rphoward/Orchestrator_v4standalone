"""
Create ``orchestrator.db`` and core tables if needed (parity with v3 app startup).

v3 runs ``init_db()`` + ``seed_agents()`` on every launch from
``orchestrator_v3/src/Infrastructure/Persistence/sqlite_config_repo.py``.
This module ports that behavior for v4's default ``orchestrator_v4/runtime/orchestrator.db`` path.

Schema source of truth: keep aligned with v3 ``sqlite_config_repo.init_db`` /
``seed_agents`` when the legacy schema changes.
"""

from __future__ import annotations

import os
import sqlite3

from orchestrator_v4.infrastructure.ai.gemini_policy_constants import (
    DEFAULT_FLASH_LITE_MODEL_ID,
    DEFAULT_PRO_MODEL_ID,
    THINKING_SEED_BY_AGENT_ID,
)
from orchestrator_v4.infrastructure.persistence.sqlite_orchestrator_connection import (
    open_orchestrator_db,
)


def ensure_orchestrator_database(db_path: str) -> None:
    """
    Ensure parent directory exists, then apply idempotent schema + default agent rows
    when the ``agents`` table is empty.
    """
    abs_path = os.path.abspath(db_path)
    parent = os.path.dirname(abs_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open_orchestrator_db(abs_path) as conn:
        _init_db_schema(conn)
        conn.commit()

    with open_orchestrator_db(abs_path) as conn:
        _seed_agents_if_empty(conn)
        conn.commit()

    with open_orchestrator_db(abs_path) as conn:
        _seed_default_agent_thinking_if_missing(conn)
        conn.commit()


def _init_db_schema(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM sessions LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("DROP TABLE IF EXISTS conversations")
        cursor.execute("DROP TABLE IF EXISTS routing_logs")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            client_name TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            current_agent_id INTEGER DEFAULT 1,
            stage1_complete INTEGER DEFAULT 0,
            stage2_complete INTEGER DEFAULT 0,
            stage3_complete INTEGER DEFAULT 0,
            stage4_complete INTEGER DEFAULT 0,
            stage_progress TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    for col_sql in (
        "ALTER TABLE sessions ADD COLUMN client_name TEXT DEFAULT ''",
        "ALTER TABLE sessions ADD COLUMN current_agent_id INTEGER DEFAULT 1",
        "ALTER TABLE sessions ADD COLUMN summary TEXT DEFAULT ''",
        "ALTER TABLE sessions ADD COLUMN stage_progress TEXT DEFAULT ''",
    ):
        try:
            cursor.execute(col_sql)
        except sqlite3.OperationalError:
            pass

    for i in range(1, 5):
        try:
            cursor.execute(
                f"ALTER TABLE sessions ADD COLUMN stage{i}_complete INTEGER DEFAULT 0"
            )
        except sqlite3.OperationalError:
            pass

    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            prompt_file TEXT NOT NULL,
            model TEXT DEFAULT '{DEFAULT_FLASH_LITE_MODEL_ID}',
            is_synthesizer INTEGER DEFAULT 0
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            agent_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            message_type TEXT DEFAULT 'chat',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (agent_id) REFERENCES agents(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS routing_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            input_text TEXT NOT NULL,
            agent_id INTEGER NOT NULL,
            agent_name TEXT NOT NULL,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS prompt_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            target_agent_id INTEGER,
            content TEXT NOT NULL,
            is_system INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )


def _seed_agents_if_empty(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    count = cursor.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    if count != 0:
        return
    agents = [
        (1, "Brand Spine", "1_brand_spine.md", DEFAULT_FLASH_LITE_MODEL_ID, 0),
        (2, "Founder Invariants", "2_founder_extraction.md", DEFAULT_FLASH_LITE_MODEL_ID, 0),
        (3, "Customer Reality", "3_customer_reality.md", DEFAULT_FLASH_LITE_MODEL_ID, 0),
        (4, "Architecture Translation", "4_architecture_translation.md", DEFAULT_FLASH_LITE_MODEL_ID, 0),
        (5, "Grand Synthesis", "5_grand_synthesis.md", DEFAULT_PRO_MODEL_ID, 1),
    ]
    cursor.executemany(
        "INSERT INTO agents (id, name, prompt_file, model, is_synthesizer) VALUES (?, ?, ?, ?, ?)",
        agents,
    )


def _seed_default_agent_thinking_if_missing(conn: sqlite3.Connection) -> None:
    """Insert thinking_level_{1..5} when absent; never overwrite existing config."""
    cursor = conn.cursor()
    for aid in range(1, 6):
        key = f"thinking_level_{aid}"
        row = cursor.execute("SELECT 1 FROM config WHERE key = ?", (key,)).fetchone()
        if row is not None:
            continue
        cursor.execute(
            "INSERT INTO config (key, value) VALUES (?, ?)",
            (key, THINKING_SEED_BY_AGENT_ID[aid]),
        )
