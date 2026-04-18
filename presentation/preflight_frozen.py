"""
Optional stdin API-key prompt **before** ``bootstrap`` imports (PyInstaller builds only).

Corporate installs normally ship a ``.env`` next to the ``.exe`` (or set a system env var).
Enable the prompt only when you intentionally set ``ORCHESTRATOR_PROMPT_FOR_API_KEY=1``.
"""

from __future__ import annotations

import getpass
import os
import sys

from orchestrator_v4.infrastructure.runtime_executable_layout import is_frozen_bundle


def run_optional_api_key_prompt() -> None:
    if not is_frozen_bundle():
        return
    if os.environ.get("GEMINI_API_KEY", "").strip():
        return
    flag = os.environ.get("ORCHESTRATOR_PROMPT_FOR_API_KEY", "").lower()
    if flag not in ("1", "true", "yes"):
        return
    if not sys.stdin.isatty():
        return
    print(
        "No GEMINI_API_KEY in environment or .env next to this app.\n"
        "Enter a Gemini API key now (input hidden), or press Enter to run offline:\n",
        file=sys.stderr,
    )
    key = getpass.getpass("GEMINI_API_KEY> ").strip()
    if key:
        os.environ["GEMINI_API_KEY"] = key
