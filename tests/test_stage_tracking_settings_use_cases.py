"""Tests for stage tracking settings use cases (no Flask, no hidden-hint contracts)."""

from orchestrator_v4.core.entities.stage_progress import StageTrackingSettings
from orchestrator_v4.core.use_cases.stage_tracking_settings import (
    ReadStageTrackingSettings,
    UpdateStageTrackingSettings,
)


class _MemoryStageTrackingSettingsStore:
    """Minimal StageTrackingSettingsStore for tests."""

    def __init__(self, initial: StageTrackingSettings | None = None) -> None:
        self._settings = initial or StageTrackingSettings(mode="hybrid", judge_interval=4)

    def read(self) -> StageTrackingSettings:
        return self._settings

    def save(self, settings: StageTrackingSettings) -> StageTrackingSettings:
        self._settings = settings
        return settings


def test_read_stage_tracking_settings_returns_store_value() -> None:
    store = _MemoryStageTrackingSettingsStore(StageTrackingSettings(mode="semantic", judge_interval=6))
    got = ReadStageTrackingSettings(store).execute()
    assert got == StageTrackingSettings(mode="semantic", judge_interval=6)


def test_update_stage_tracking_settings_normalizes_and_persists() -> None:
    store = _MemoryStageTrackingSettingsStore()
    uc = UpdateStageTrackingSettings(store)

    out = uc.execute("semantic", "8")

    assert out == StageTrackingSettings(mode="semantic", judge_interval=8)
    assert store.read() == out


def test_update_stage_tracking_settings_invalid_interval_falls_back() -> None:
    store = _MemoryStageTrackingSettingsStore()
    uc = UpdateStageTrackingSettings(store)

    out = uc.execute("hybrid", "0")

    assert out.judge_interval == 4
    assert store.read().judge_interval == 4


def test_update_stage_tracking_settings_none_arguments_use_defaults() -> None:
    store = _MemoryStageTrackingSettingsStore(StageTrackingSettings(mode="semantic", judge_interval=9))
    uc = UpdateStageTrackingSettings(store)

    out = uc.execute(None, None)

    assert out == StageTrackingSettings(mode="hybrid", judge_interval=4)
