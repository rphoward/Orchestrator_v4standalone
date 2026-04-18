"""
Path layout when the app is packaged with PyInstaller (or similar).

- **Bundled read-only assets** (e.g. spine prompts) live under ``sys._MEIPASS`` after extract.
- **Writable data** (SQLite) must not live inside the bundle; use a folder next to the ``.exe``.

Development (not frozen) uses ``orchestrator_v4/runtime/`` as today; see ``bootstrap.py``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen_bundle() -> bool:
    """True when running as a PyInstaller-built executable."""
    return bool(getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None))


def executable_directory() -> str:
    """Directory containing the running ``.exe`` (or the Python interpreter in dev)."""
    return str(Path(sys.executable).resolve().parent)


def bundle_extract_directory() -> str:
    """One-file extract dir (``_MEIPASS``); empty string if not frozen."""
    mei = getattr(sys, "_MEIPASS", None)
    return str(Path(mei)) if mei else ""
