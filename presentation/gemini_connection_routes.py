"""API key, model registry, router model, and model-id verify (vertical slice)."""

from __future__ import annotations
from typing import cast

from dotenv import set_key
from flask import Flask, jsonify, request

from orchestrator_v4 import bootstrap
from orchestrator_v4.core.entities.model_registry_entry import ModelRegistryEntry
from orchestrator_v4.presentation.gemini_env import (
    gemini_key_for_display,
    mask_gemini_key_display,
    orchestrator_dotenv_path,
)
from orchestrator_v4.presentation.http_helpers import json_body_dict, validation_error_response


def register_gemini_connection_routes(app: Flask) -> None:
    @app.route("/api/config/api-key", methods=["GET", "PUT"])
    def api_config_api_key():
        if request.method == "GET":
            return jsonify(
                {"masked_key": mask_gemini_key_display(gemini_key_for_display())}
            )
        data = json_body_dict()
        api_key = (data.get("api_key") or "").strip()
        if not api_key:
            return validation_error_response("api_key is required")
        path = orchestrator_dotenv_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            set_key(str(path), "GEMINI_API_KEY", api_key)
        except OSError as e:
            app.logger.exception("Failed to write GEMINI_API_KEY to .env")
            return jsonify({"error": str(e), "error_type": "unknown_error"}), 500
        bootstrap.apply_gemini_api_key(api_key)
        return jsonify({"masked_key": mask_gemini_key_display(api_key)})

    @app.route("/api/config/verify-model-ids", methods=["POST"])
    def api_config_verify_model_ids():
        if not bootstrap.gemini_api_key_configured:
            return validation_error_response(
                "GEMINI_API_KEY is not configured",
                status=401,
            )
        result = bootstrap.execute_model_id_verify()
        return jsonify(result)

    @app.route("/api/models", methods=["GET"])
    def get_models():
        models: list[ModelRegistryEntry] = bootstrap.model_registry_store.get_models()
        return jsonify(models)

    @app.route("/api/models", methods=["PUT"])
    def save_models():
        data = request.get_json()
        if not data or "models" not in data:
            return validation_error_response('Expected {"models": [...]}')
        raw_models = data["models"]
        if not isinstance(raw_models, list):
            return validation_error_response("'models' must be a JSON array")
        for i, item in enumerate(raw_models):
            if not isinstance(item, dict):
                return validation_error_response(
                    f"models[{i}] must be a JSON object"
                )
        models: list[ModelRegistryEntry] = cast(list[ModelRegistryEntry], raw_models)
        try:
            bootstrap.model_registry_store.save_models(models)
            bootstrap.rebind_llm_gateway()
            return jsonify({"status": "ok", "count": len(models)})
        except ValueError as e:
            return validation_error_response(str(e))
        except Exception as e:
            return jsonify({"error": str(e), "error_type": "unknown_error"}), 500

    @app.route("/api/config/router-model", methods=["GET", "PUT"])
    def router_model():
        if request.method == "GET":
            return jsonify({"model": bootstrap.model_registry_store.get_router_model()})
        data = request.get_json()
        if not data or "model" not in data:
            return validation_error_response("Missing 'model' field")
        if not isinstance(data["model"], str) or not data["model"].strip():
            return validation_error_response(
                "'model' field must be a valid non-empty string"
            )
        model_id = data["model"].strip()
        bootstrap.model_registry_store.set_router_model(model_id)
        bootstrap.rebind_llm_gateway()
        return jsonify({"status": "ok", "model": model_id})
