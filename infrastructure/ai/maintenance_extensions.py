"""
Extension hooks for model-id verification / maintenance signals.

``merge_maintenance_signals`` is an identity placeholder today so later work can plug in:

- Vendored ``gemini_deprecation_schedule.json`` for offline or CI.
- Deprecation metadata from ``models.list`` when the API exposes it.
- Save-time warning cache keyed by last verify timestamp.

Vertex AI / Cloud model lists are out of scope for this app path unless requirements change.
"""

from __future__ import annotations

from typing import Any


def merge_maintenance_signals(result: dict[str, Any]) -> dict[str, Any]:
    """Last step in verify pipeline; default is no-op."""
    return result
