"""Use cases for stage tracking settings."""

from __future__ import annotations

from orchestrator_v4.core.entities.stage_progress import (
    StageTrackingSettings,
    normalize_stage_tracking_settings,
)
from orchestrator_v4.core.ports.stage_tracking_settings_store import (
    StageTrackingSettingsStore,
)


class ReadStageTrackingSettings:
    def __init__(self, store: StageTrackingSettingsStore) -> None:
        self._store = store

    def execute(self) -> StageTrackingSettings:
        return self._store.read()


class UpdateStageTrackingSettings:
    def __init__(self, store: StageTrackingSettingsStore) -> None:
        self._store = store

    def execute(self, mode: object | None, judge_interval: object | None) -> StageTrackingSettings:
        settings = normalize_stage_tracking_settings(mode, judge_interval)
        return self._store.save(settings)
