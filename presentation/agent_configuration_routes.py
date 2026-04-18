"""Agent roster, prompts, overrides, and per-agent generation settings (vertical slice)."""

from __future__ import annotations

import dataclasses

from flask import Flask, jsonify, request

from orchestrator_v4 import bootstrap
from orchestrator_v4.core.entities.agent_settings_row import AgentSettingsRow
from orchestrator_v4.presentation.http_helpers import (
    validation_error_response,
    value_error_http_response,
)


def register_agent_configuration_routes(app: Flask) -> None:
    @app.route("/api/agents", methods=["GET"])
    def list_agents():
        agents: list[AgentSettingsRow] = bootstrap.agent_config_store.list_agents()
        return jsonify(agents)

    @app.route("/api/agents/<int:agent_id>", methods=["PUT"])
    def update_agent(agent_id: int):
        data = request.get_json()
        if not data:
            return validation_error_response("No data provided")
        try:
            bootstrap.agent_config_store.update_agent(
                agent_id,
                data.get("name", ""),
                data.get("model", ""),
                prompt=data.get("prompt"),
            )
            if data.get("prompt") is not None:
                bootstrap.invalidate_prompt_runtime_cache(agent_id)
            return jsonify({"status": "ok"})
        except ValueError as e:
            return validation_error_response(str(e))
        except OSError as e:
            return (
                jsonify(
                    {
                        "error": f"Failed to save prompt: {str(e)}",
                        "error_type": "unknown_error",
                    }
                ),
                500,
            )

    @app.route("/api/config/thinking-level/<int:agent_id>", methods=["GET", "PUT"])
    def agent_thinking_level(agent_id: int):
        if request.method == "GET":
            return jsonify(
                {
                    "thinking_level": bootstrap.agent_config_store.get_thinking_level(
                        agent_id
                    )
                    or ""
                }
            )
        data = request.get_json()
        if not data:
            return validation_error_response("No data provided")
        level = data.get("thinking_level", "")
        if level and not isinstance(level, str):
            return validation_error_response(
                "Invalid thinking level type. Must be a string."
            )
        if level and level.upper() not in ("MINIMAL", "LOW", "MEDIUM", "HIGH", ""):
            return validation_error_response(
                "Invalid thinking level. Use MINIMAL, LOW, MEDIUM, HIGH, or empty."
            )
        bootstrap.agent_config_store.set_thinking_level(agent_id, level)
        return jsonify({"status": "ok", "agent_id": agent_id, "thinking_level": level})

    @app.route("/api/config/temperature/<int:agent_id>", methods=["GET", "PUT"])
    def agent_temperature(agent_id: int):
        if request.method == "GET":
            return jsonify(
                {
                    "temperature": bootstrap.agent_config_store.get_temperature(
                        agent_id
                    )
                    or ""
                }
            )
        data = request.get_json()
        if not data:
            return validation_error_response("No data provided")
        temp = data.get("temperature", "")
        if temp != "" and temp is not None:
            try:
                temp_float = float(temp)
                if temp_float < 0.0 or temp_float > 2.0:
                    return validation_error_response(
                        "Temperature must be between 0.0 and 2.0"
                    )
            except (ValueError, TypeError):
                return validation_error_response("Temperature must be a number")
        bootstrap.agent_config_store.set_temperature(agent_id, temp)
        return jsonify({"status": "ok", "agent_id": agent_id, "temperature": temp})

    @app.route("/api/config/include-thoughts/<int:agent_id>", methods=["GET", "PUT"])
    def agent_include_thoughts(agent_id: int):
        if request.method == "GET":
            return jsonify(
                {
                    "include_thoughts": bootstrap.agent_config_store.get_include_thoughts(
                        agent_id
                    )
                }
            )
        data = request.get_json()
        if not data or "include_thoughts" not in data:
            return validation_error_response("Missing 'include_thoughts' field")
        value = data["include_thoughts"]
        if not isinstance(value, bool):
            return validation_error_response("'include_thoughts' must be a boolean")
        bootstrap.agent_config_store.set_include_thoughts(agent_id, value)
        return jsonify({"status": "ok", "agent_id": agent_id, "include_thoughts": value})

    @app.route("/api/config/agent-overrides", methods=["GET"])
    def get_config_agent_overrides():
        """v3-compatible agent overrides batch endpoint."""
        ids_param = (request.args.get("ids") or "").strip()
        if ids_param:
            try:
                agent_ids = [int(x.strip()) for x in ids_param.split(",") if x.strip()]
            except ValueError:
                return validation_error_response("Invalid ids query")
        else:
            agent_ids = [1, 2, 3, 4]

        overrides = bootstrap.read_agent_overrides.execute(agent_ids)
        agents_out: dict[str, dict[str, object]] = {}
        for o in overrides:
            agents_out[str(o.agent_id)] = {
                "thinking_level": o.thinking_level or "",
                "temperature": o.temperature or "",
                "include_thoughts": bool(o.include_thoughts),
            }
        return jsonify({"agents": agents_out})

    @app.route("/api/agents/<int:agent_id>/prompt", methods=["GET"])
    def get_agent_prompt(agent_id: int):
        """Load the prompt body for an agent."""
        try:
            prompt_body = bootstrap.load_interview_prompt_body.execute(agent_id)
            return jsonify({"agent_id": agent_id, "prompt_body": prompt_body})
        except ValueError as e:
            return value_error_http_response(e)

    @app.route("/api/agents/overrides", methods=["GET"])
    def get_agent_overrides():
        """Read overrides for multiple agents. Pass ?ids=1,2,3"""
        ids_param = request.args.get("ids", "")
        if not ids_param:
            return jsonify([])

        try:
            agent_ids = [int(x.strip()) for x in ids_param.split(",") if x.strip()]
        except ValueError:
            return jsonify({"error": "Invalid agent IDs"}), 400

        overrides = bootstrap.read_agent_overrides.execute(agent_ids)
        return jsonify([dataclasses.asdict(o) for o in overrides])
