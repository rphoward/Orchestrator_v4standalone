"""Gemini API key path and display helpers (presentation; filesystem via dotenv)."""

from __future__ import annotations

import os
import pathlib

from dotenv import dotenv_values

from orchestrator_v4 import bootstrap
from orchestrator_v4.infrastructure.runtime_executable_layout import (
    executable_directory,
    is_frozen_bundle,
)


def orchestrator_dotenv_path() -> pathlib.Path:
    if is_frozen_bundle():
        return pathlib.Path(executable_directory()) / ".env"
    return pathlib.Path(bootstrap.__file__).resolve().parent / ".env"


def mask_gemini_key_display(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if len(raw) < 12:
        return "••••••••"
    return "••••••••…" + raw[-4:]


def gemini_key_for_display() -> str:
    path = orchestrator_dotenv_path()
    if path.is_file():
        values = dotenv_values(path)
        file_key = (values.get("GEMINI_API_KEY") or "").strip()
        if file_key:
            return file_key
    return (os.environ.get("GEMINI_API_KEY") or "").strip()
