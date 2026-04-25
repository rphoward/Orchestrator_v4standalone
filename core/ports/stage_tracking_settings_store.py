"""Port: read and write stage tracking settings."""

from __future__ import annotations

from typing import Protocol

from orchestrator_v4.core.entities.stage_progress import StageTrackingSettings


class StageTrackingSettingsStore(Protocol):
    def read(self) -> StageTrackingSettings:
        """Return sanitized stage tracking settings."""
        ...

    def save(self, settings: StageTrackingSettings) -> StageTrackingSettings:
        """Persist sanitized stage tracking settings and return what was saved."""
        ...
