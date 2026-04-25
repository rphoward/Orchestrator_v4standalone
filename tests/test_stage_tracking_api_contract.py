"""
HTTP JSON contract for stage tracking settings.

Keeps `GET`/`PUT /api/config/stage-tracking` aligned with the plan and the
Settings UI.
"""

from flask import Flask

from orchestrator_v4.core.entities.stage_progress import StageTrackingSettings
from orchestrator_v4.presentation import (
    interview_session_routes,
    interview_stage_tracking_settings_routes,
)


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
    payload = interview_stage_tracking_settings_routes._stage_tracking_settings_payload(
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
        interview_stage_tracking_settings_routes.bootstrap,
        "read_stage_tracking_settings",
        _ReadStageTrackingSettings(),
    )
    monkeypatch.setattr(
        interview_stage_tracking_settings_routes.bootstrap,
        "update_stage_tracking_settings",
        update,
    )
    app = Flask(__name__)
    interview_stage_tracking_settings_routes.register_interview_stage_tracking_settings_routes(
        app
    )

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


def test_get_session_stage_tracking_json_shape(monkeypatch) -> None:
    """Route must see the stub: patch the module the handler resolves at request time.

    Importing ``presentation.app`` registers all routes first; patching a different
    import of ``bootstrap`` afterward is fragile. Patch ``interview_session_routes.bootstrap``
    (same object the GET handler's globals use), then register only session routes
    on a fresh Flask app — same pattern as ``test_stage_tracking_settings_route_accepts_plan_key_names``.
    """

    class _FakeReadLog:
        def execute(self, session_id: int) -> dict[str, object]:
            return {"entries": [{"turn_endpoint": "auto", "routed_stage_id": 1}]}

    monkeypatch.setattr(
        interview_session_routes.bootstrap,
        "read_session_stage_tracking_log",
        _FakeReadLog(),
    )
    app = Flask(__name__)
    interview_session_routes.register_interview_session_routes(app)
    response = app.test_client().get("/api/sessions/1/stage-tracking")
    assert response.status_code == 200
    data = response.get_json()
    assert "entries" in data
    assert data["entries"] == [
        {"turn_endpoint": "auto", "routed_stage_id": 1},
    ]
