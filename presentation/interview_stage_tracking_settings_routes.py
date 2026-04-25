"""HTTP for interview stage-tracking settings (GET/PUT /api/config/stage-tracking)."""

from __future__ import annotations

from flask import Flask, jsonify, request

from orchestrator_v4 import bootstrap
from orchestrator_v4.presentation.http_helpers import json_body_dict, validation_error_response


def _stage_tracking_settings_payload(settings) -> dict[str, object]:
    return {
        "stage_tracking_mode": settings.mode,
        "stage_tracking_judge_interval": settings.judge_interval,
        "mode": settings.mode,
        "judge_interval_turns": settings.judge_interval,
    }


def _stage_tracking_request_value(
    data: dict[str, object],
    preferred_key: str,
    fallback_key: str,
) -> object | None:
    preferred = data.get(preferred_key)
    return preferred if preferred is not None else data.get(fallback_key)


def register_interview_stage_tracking_settings_routes(app: Flask) -> None:
    @app.route("/api/config/stage-tracking", methods=["GET", "PUT"])
    def api_config_stage_tracking():
        if request.method == "GET":
            settings = bootstrap.read_stage_tracking_settings.execute()
            return jsonify(_stage_tracking_settings_payload(settings))
        data = json_body_dict()
        settings = bootstrap.update_stage_tracking_settings.execute(
            _stage_tracking_request_value(data, "stage_tracking_mode", "mode"),
            _stage_tracking_request_value(
                data,
                "stage_tracking_judge_interval",
                "judge_interval_turns",
            ),
        )
        return jsonify(_stage_tracking_settings_payload(settings))
