"""Wire shapes for ``prompt_templates`` rows and partial updates."""

from __future__ import annotations

from typing import TypedDict


class PromptTemplateRow(TypedDict):
    id: int
    name: str
    description: str
    target_agent_id: int | None
    content: str
    is_system: int
    created_at: str
    updated_at: str


class PromptTemplateUpdateFields(TypedDict, total=False):
    name: str | None
    description: str | None
    content: str | None
    target_agent_id: int | None
