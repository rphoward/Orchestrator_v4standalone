"""Port: CRUD for legacy ``prompt_templates`` rows (library / staging workflow)."""

from __future__ import annotations

from typing import Protocol

from orchestrator_v4.core.entities.prompt_template_row import (
    PromptTemplateRow,
    PromptTemplateUpdateFields,
)


class PromptTemplateStore(Protocol):
    def list_templates(self) -> list[PromptTemplateRow]:
        """Return all templates, newest first (``created_at DESC`` like v3)."""
        ...

    def create_template(
        self,
        name: str,
        content: str,
        *,
        description: str = "",
        target_agent_id: int | None = None,
    ) -> PromptTemplateRow:
        ...

    def update_template(
        self,
        template_id: int,
        fields: PromptTemplateUpdateFields,
    ) -> PromptTemplateRow | None:
        ...

    def delete_template(self, template_id: int) -> None:
        ...
