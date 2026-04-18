"""Use cases: list/create/update/delete prompt template rows (v3 parity)."""

from __future__ import annotations

from orchestrator_v4.core.entities.prompt_template_row import (
    PromptTemplateRow,
    PromptTemplateUpdateFields,
)
from orchestrator_v4.core.ports.prompt_template_store import PromptTemplateStore


class ListPromptTemplates:
    def __init__(self, store: PromptTemplateStore) -> None:
        self._store = store

    def execute(self) -> list[PromptTemplateRow]:
        return self._store.list_templates()


class CreatePromptTemplate:
    def __init__(self, store: PromptTemplateStore) -> None:
        self._store = store

    def execute(
        self,
        name: str,
        content: str,
        *,
        description: str = "",
        target_agent_id: int | None = None,
    ) -> PromptTemplateRow:
        name = (name or "").strip()
        content = (content or "").strip()
        if not name or not content:
            raise ValueError("name and content are required")
        return self._store.create_template(
            name,
            content,
            description=(description or "").strip(),
            target_agent_id=target_agent_id,
        )


class UpdatePromptTemplate:
    def __init__(self, store: PromptTemplateStore) -> None:
        self._store = store

    def execute(
        self, template_id: int, fields: PromptTemplateUpdateFields
    ) -> PromptTemplateRow:
        if not isinstance(template_id, int) or template_id < 1:
            raise ValueError(
                f"Invalid template id (positive integers only): {template_id!r}"
            )
        updated = self._store.update_template(template_id, fields)
        if updated is None:
            raise ValueError(f"Template {template_id} not found")
        return updated


class DeletePromptTemplate:
    def __init__(self, store: PromptTemplateStore) -> None:
        self._store = store

    def execute(self, template_id: int) -> None:
        if not isinstance(template_id, int) or template_id < 1:
            raise ValueError(
                f"Invalid template id (positive integers only): {template_id!r}"
            )
        self._store.delete_template(template_id)
