"""
HTTP JSON contract for stage tracking settings.

Keeps `GET`/`PUT /api/config/stage-tracking` aligned with the plan and the
Settings UI.
"""

from flask import Flask

from orchestrator_v4.core.entities.stage_progress import StageTrackingSettings
from orchestrator_v4.presentation import gemini_connection_routes


class _ReadStageTrackingSettings:
    def execute(self) -> StageTrackingSettings:
        return StageTrackingSettings(mode="off", judge_interval=3)


class _UpdateStageTrackingSettings:
    def __init__(self) -> None:
        self.calls: list[tuple[object | None, object | None]] = []

    def execute(
        self,
        mode: object | None,
        judge_interval: object | None,
    ) -> StageTrackingSettings:
        self.calls.append((mode, judge_interval))
        return StageTrackingSettings(mode="semantic", judge_interval=2)


def test_stage_tracking_settings_payload_supports_plan_and_ui_names() -> None:
    payload = gemini_connection_routes._stage_tracking_settings_payload(
        StageTrackingSettings(mode="off", judge_interval=3)
    )
    assert payload == {
        "stage_tracking_mode": "off",
        "stage_tracking_judge_interval": 3,
        "mode": "off",
        "judge_interval_turns": 3,
    }


def test_stage_tracking_settings_route_accepts_plan_key_names(monkeypatch) -> None:
    update = _UpdateStageTrackingSettings()
    monkeypatch.setattr(
        gemini_connection_routes.bootstrap,
        "read_stage_tracking_settings",
        _ReadStageTrackingSettings(),
    )
    monkeypatch.setattr(
        gemini_connection_routes.bootstrap,
        "update_stage_tracking_settings",
        update,
    )
    app = Flask(__name__)
    gemini_connection_routes.register_gemini_connection_routes(app)

    response = app.test_client().put(
        "/api/config/stage-tracking",
        json={"mode": "semantic", "judge_interval_turns": 2},
    )

    assert response.status_code == 200
    assert update.calls == [("semantic", 2)]
    assert response.get_json() == {
        "stage_tracking_mode": "semantic",
        "stage_tracking_judge_interval": 2,
        "mode": "semantic",
        "judge_interval_turns": 2,
    }
