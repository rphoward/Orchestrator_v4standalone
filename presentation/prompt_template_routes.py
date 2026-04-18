"""Prompt template library + runtime prompt cache invalidation (vertical slice)."""

from __future__ import annotations

import sqlite3
from typing import cast

from flask import Flask, jsonify, request

from orchestrator_v4 import bootstrap
from orchestrator_v4.core.entities.prompt_template_row import PromptTemplateUpdateFields
from orchestrator_v4.presentation.http_helpers import (
    json_body_dict,
    parse_optional_positive_agent_id,
    parse_optional_target_agent_id,
    validation_error_response,
    value_error_http_response,
)


def _invalidate_prompt_cache_after_template_mutation() -> None:
    """Clear shared spine-file cache after template CRUD (C1 + C2 coherence)."""
    bootstrap.invalidate_prompt_runtime_cache(None)


def register_prompt_template_routes(app: Flask) -> None:
    @app.route("/api/prompt-templates", methods=["GET"])
    def api_list_prompt_templates():
        try:
            items = bootstrap.list_prompt_templates.execute()
            return jsonify(items)
        except sqlite3.OperationalError as e:
            return jsonify({"error": str(e), "error_type": "unknown_error"}), 500

    @app.route("/api/prompt-templates", methods=["POST"])
    def api_create_prompt_template():
        data = json_body_dict()
        name = (data.get("name") or "").strip()
        content = (data.get("content") or "").strip()
        if not name or not content:
            return validation_error_response("Missing name or content")
        description = (data.get("description") or "").strip()
        raw_target = data.get("target_agent_id")
        target_agent_id, terr = parse_optional_target_agent_id(raw_target)
        if terr:
            return validation_error_response(terr)
        try:
            template = bootstrap.create_prompt_template.execute(
                name,
                content,
                description=description,
                target_agent_id=target_agent_id,
            )
            _invalidate_prompt_cache_after_template_mutation()
            return jsonify(template), 200
        except ValueError as e:
            return validation_error_response(str(e))
        except sqlite3.OperationalError as e:
            return jsonify({"error": str(e), "error_type": "unknown_error"}), 500

    @app.route("/api/prompt-templates/<int:template_id>", methods=["PUT"])
    def api_update_prompt_template(template_id: int):
        data = json_body_dict()
        if not data:
            return validation_error_response("No data provided")
        patch: dict[str, object] = {}
        if "name" in data:
            patch["name"] = data.get("name")
        if "description" in data:
            patch["description"] = data.get("description")
        if "content" in data:
            patch["content"] = data.get("content")
        if "target_agent_id" in data:
            raw_target = data.get("target_agent_id")
            tid, terr = parse_optional_target_agent_id(raw_target)
            if terr:
                return validation_error_response(terr)
            patch["target_agent_id"] = tid
        fields = cast(PromptTemplateUpdateFields, patch)
        try:
            updated = bootstrap.update_prompt_template.execute(template_id, fields)
            _invalidate_prompt_cache_after_template_mutation()
            return jsonify(updated), 200
        except ValueError as e:
            return value_error_http_response(
                e,
                not_found_error_type="not_found",
                bad_request_error_type="validation_error",
            )
        except sqlite3.OperationalError as e:
            return jsonify({"error": str(e), "error_type": "unknown_error"}), 500

    @app.route("/api/prompt-templates/<int:template_id>", methods=["DELETE"])
    def api_delete_prompt_template(template_id: int):
        try:
            bootstrap.delete_prompt_template.execute(template_id)
            _invalidate_prompt_cache_after_template_mutation()
            return jsonify({"status": "ok"}), 200
        except ValueError as e:
            return validation_error_response(str(e))
        except sqlite3.OperationalError as e:
            return jsonify({"error": str(e), "error_type": "unknown_error"}), 500

    @app.route("/api/runtime/prompts/invalidate", methods=["POST"])
    def invalidate_prompt_runtime_cache():
        """Explicitly invalidate prompt/template runtime cache."""
        data = request.get_json(silent=True) or {}
        agent_id, err = parse_optional_positive_agent_id(data.get("agent_id"))
        if err:
            return jsonify({"error": err}), 400
        try:
            bootstrap.invalidate_prompt_runtime_cache(agent_id)
            return jsonify({"status": "ok", "agent_id": agent_id}), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 404
