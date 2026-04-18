"""Wire shape for Settings agent list rows (agents table + loaded prompt body)."""

from __future__ import annotations

from typing import TypedDict


class AgentSettingsRow(TypedDict):
    id: int
    name: str
    prompt_file: str
    model: str
    is_synthesizer: bool
    prompt: str
