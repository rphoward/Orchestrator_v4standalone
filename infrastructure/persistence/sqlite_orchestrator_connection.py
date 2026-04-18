"""
Shared SQLite connection contract for the legacy ``orchestrator.db``.

v3 session, config, and prompt repositories use WAL + foreign_keys + Row factory;
v4 adapters that read the same file should match that discipline.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator

# Seconds to wait on SQLITE_BUSY when another connection holds the db (Flask + parallel readers).
_DEFAULT_BUSY_TIMEOUT_S = 5.0


def connect_orchestrator_db(
    path: str, *, timeout: float = _DEFAULT_BUSY_TIMEOUT_S
) -> sqlite3.Connection:
    """
    Open ``orchestrator.db`` with the same PRAGMA discipline as v3 persistence repos.

    - ``row_factory`` → ``sqlite3.Row``
    - ``PRAGMA journal_mode=WAL`` (aligns lock/file behavior with v3 writers)
    - ``PRAGMA foreign_keys = ON``
    """
    conn = sqlite3.connect(path, timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def open_orchestrator_db(
    path: str, *, timeout: float = _DEFAULT_BUSY_TIMEOUT_S
) -> Iterator[sqlite3.Connection]:
    """
    Context manager that guarantees orchestrator SQLite connections are closed.

    Note: ``sqlite3.Connection`` context manager does NOT close connections;
    this wrapper enforces close semantics for long-running app/test stability.
    """
    conn = connect_orchestrator_db(path, timeout=timeout)
    try:
        yield conn
    finally:
        conn.close()
