"""
HTTP JSON contract for stage tracking settings.

Keeps `GET`/`PUT /api/config/stage-tracking` aligned with the Settings UI
(`stage_tracking_mode`, `stage_tracking_judge_interval`). Does not assert
browser behavior or hidden agent-response hints (not implemented).
"""

from orchestrator_v4.core.entities.stage_progress import StageTrackingSettings
from orchestrator_v4.presentation.gemini_connection_routes import (
    _stage_tracking_settings_payload,
)


def test_stage_tracking_settings_payload_uses_api_key_names() -> None:
    payload = _stage_tracking_settings_payload(StageTrackingSettings(mode="off", judge_interval=3))
    assert payload == {
        "stage_tracking_mode": "off",
        "stage_tracking_judge_interval": 3,
    }
    assert set(payload.keys()) == {"stage_tracking_mode", "stage_tracking_judge_interval"}
