"""
Resolvable paths for Orchestrator v4 runtime data (SQLite, etc.).

Kept separate from ``bootstrap`` so callers can resolve ``ORCHESTRATOR_DB_PATH`` without
importing the composition root (no ``ensure_orchestrator_database`` side effects here).
"""

from __future__ import annotations

import os

from orchestrator_v4.infrastructure.runtime_executable_layout import (
    executable_directory,
    is_frozen_bundle,
)


def _package_root_dir() -> str:
    """Directory of the ``orchestrator_v4`` package (sibling of this file's parent)."""
    return os.path.dirname(os.path.abspath(__file__))


def _default_orchestrator_db_path() -> str:
    """Writable SQLite path: beside the .exe when frozen, else ``orchestrator_v4/runtime/``."""
    if is_frozen_bundle():
        data_dir = os.path.join(executable_directory(), "Orchestrator4_data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "orchestrator.db")
    return os.path.join(_package_root_dir(), "runtime", "orchestrator.db")


def resolve_orchestrator_db_path() -> str:
    """Optional override via ORCHESTRATOR_DB_PATH for tests or custom installs."""
    return os.environ.get("ORCHESTRATOR_DB_PATH", _default_orchestrator_db_path())
