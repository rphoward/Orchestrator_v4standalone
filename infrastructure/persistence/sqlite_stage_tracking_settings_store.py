"""SQLite adapter for stage tracking settings stored in ``config``."""

from __future__ import annotations

from orchestrator_v4.core.entities.stage_progress import (
    StageTrackingSettings,
    normalize_stage_tracking_settings,
)
from orchestrator_v4.core.ports.stage_tracking_settings_store import (
    StageTrackingSettingsStore,
)
from orchestrator_v4.infrastructure.persistence.sqlite_orchestrator_connection import (
    open_orchestrator_db,
)

_MODE_KEY = "stage_tracking_mode"
_INTERVAL_KEY = "stage_tracking_judge_interval"


class SqliteStageTrackingSettingsStore(StageTrackingSettingsStore):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def read(self) -> StageTrackingSettings:
        with open_orchestrator_db(self._db_path) as conn:
            rows = conn.execute(
                "SELECT key, value FROM config WHERE key IN (?, ?)",
                (_MODE_KEY, _INTERVAL_KEY),
            ).fetchall()
        by_key = {str(row["key"]): row["value"] for row in rows}
        return normalize_stage_tracking_settings(
            by_key.get(_MODE_KEY),
            by_key.get(_INTERVAL_KEY),
        )

    def save(self, settings: StageTrackingSettings) -> StageTrackingSettings:
        sanitized = normalize_stage_tracking_settings(
            settings.mode,
            settings.judge_interval,
        )
        with open_orchestrator_db(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                (_MODE_KEY, sanitized.mode),
            )
            conn.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                (_INTERVAL_KEY, str(sanitized.judge_interval)),
            )
            conn.commit()
        return sanitized
