"""Wire shape for one model entry in the persisted Gemini model registry JSON."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class ModelRegistryEntry(TypedDict):
    """Keys optional except ``id``; matches validation in ``_validate_models`` and default seed rows."""

    id: str
    label: NotRequired[str]
    supports_thinking: NotRequired[bool]
    default_thinking: NotRequired[str]
    temperature_range: NotRequired[list[float | int]]
    default_temperature: NotRequired[float | int]
    max_output_tokens: NotRequired[int]
    context_window: NotRequired[int]
    requires_thought_signatures: NotRequired[bool]
    include_thoughts_supported: NotRequired[bool]
    media_resolution_supported: NotRequired[bool]
    output_modalities: NotRequired[list[str]]
    status: NotRequired[str]
    notes: NotRequired[str]
