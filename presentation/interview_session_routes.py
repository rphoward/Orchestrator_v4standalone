"""Interview session lifecycle, transcripts, and export/import (vertical slice)."""

from __future__ import annotations

import dataclasses

from flask import Flask, jsonify, request

from orchestrator_v4 import bootstrap
from orchestrator_v4.core.use_cases.session_export_v3_format import (
    build_v3_session_export_document,
)
from orchestrator_v4.presentation.http_helpers import (
    non_empty_strip,
    value_error_http_response,
)


def register_interview_session_routes(app: Flask) -> None:
    @app.route("/api/sessions", methods=["GET"])
    def list_sessions():
        """List all interview sessions."""
        summaries = bootstrap.list_interview_sessions.execute()
        return jsonify([dataclasses.asdict(s) for s in summaries])

    @app.route("/api/sessions", methods=["POST"])
    def create_session():
        """Create a new interview session."""
        data = request.get_json() or {}
        name = data.get("name", "New Session")
        client_name = data.get("client_name", "")

        summary = bootstrap.create_interview_session.execute(name, client_name)
        return jsonify(dataclasses.asdict(summary)), 201

    @app.route("/api/sessions/<int:session_id>", methods=["PATCH", "PUT"])
    def update_session(session_id: int):
        """Update a session's headline metadata."""
        data = request.get_json() or {}
        name = data.get("name")
        client_name = data.get("client_name")
        summary_text = data.get("summary")

        try:
            updated = bootstrap.update_interview_session.execute(
                session_id, name, client_name, summary_text
            )
            return jsonify(dataclasses.asdict(updated)), 200
        except ValueError as e:
            return value_error_http_response(e)

    @app.route("/api/sessions/<int:session_id>", methods=["DELETE"])
    def delete_session(session_id: int):
        """Delete an interview session."""
        try:
            bootstrap.delete_interview_session.execute(session_id)
            return "", 204
        except ValueError as e:
            return value_error_http_response(e)

    @app.route("/api/sessions/<int:session_id>/turn", methods=["POST"])
    def conduct_turn(session_id: int):
        """Run one interview turn (SQLite persistence + Gemini when API key set)."""
        data = request.get_json() or {}
        user_input = non_empty_strip(data, "message")
        if not user_input:
            return jsonify({"error": "message is required"}), 400
        try:
            result = bootstrap.conduct_interview_turn.execute(session_id, user_input)
            return jsonify(dataclasses.asdict(result)), 200
        except ValueError as e:
            return value_error_http_response(e)

    @app.route("/api/sessions/<int:session_id>/send", methods=["POST"])
    def send_message(session_id: int):
        """Alias for /turn — the static UI calls this path."""
        return conduct_turn(session_id)

    @app.route("/api/sessions/<int:session_id>/initialize", methods=["POST"])
    def initialize_session(session_id: int):
        try:
            results = bootstrap.initialize_session.execute(session_id)
            return jsonify({"status": "ok", "agents": results})
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": str(e), "error_type": "unknown_error"}), 500

    @app.route("/api/sessions/<int:session_id>/send-manual", methods=["POST"])
    def send_manual(session_id: int):
        data = request.get_json() or {}
        message = (data.get("message") or "").strip()
        raw_agent = data.get("agent_id")
        if not message or raw_agent is None:
            return jsonify(
                {"error": "Missing message or agent_id", "error_type": "validation_error"}
            ), 400
        try:
            agent_id = int(raw_agent)
        except (TypeError, ValueError):
            return jsonify(
                {"error": "Missing message or agent_id", "error_type": "validation_error"}
            ), 400
        try:
            result = bootstrap.conduct_manual_turn.execute(session_id, agent_id, message)
            return jsonify(dataclasses.asdict(result)), 200
        except ValueError as e:
            return value_error_http_response(e)
        except Exception as e:
            return jsonify({"error": str(e), "error_type": "unknown_error"}), 500

    @app.route("/api/sessions/<int:session_id>/finalize", methods=["POST"])
    def finalize_session_route(session_id: int):
        data = request.get_json() or {}
        force = bool(data.get("force", False))
        try:
            result = bootstrap.finalize_session.execute(session_id, force=force)
            return jsonify(result)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": str(e), "error_type": "unknown_error"}), 500

    @app.route("/api/sessions/<int:session_id>/export", methods=["GET"])
    def export_session(session_id: int):
        try:
            bundle = bootstrap.load_interview_session_for_export.execute(session_id)
            if not bundle:
                return jsonify(
                    {"error": "Session not found", "error_type": "not_found"}
                ), 404
            export_doc = build_v3_session_export_document(bundle)
            return jsonify(export_doc)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/sessions/import", methods=["POST"])
    def import_session():
        data = request.get_json()
        if not data or "orchestrator_export" not in data:
            return jsonify(
                {"error": "Invalid session export file.", "error_type": "validation_error"}
            ), 400
        if data["orchestrator_export"].get("type") != "session":
            return jsonify(
                {"error": "Invalid session export file.", "error_type": "validation_error"}
            ), 400
        try:
            new_id = bootstrap.import_session.execute(data)
            return jsonify({"status": "ok", "new_session_id": new_id})
        except Exception as e:
            return jsonify({"error": str(e), "error_type": "unknown_error"}), 500

    @app.route("/api/sessions/<int:session_id>/conversations", methods=["GET"])
    def get_conversations(session_id: int):
        """Return conversation messages for a session, optionally filtered by agent_id."""
        try:
            lines = bootstrap.load_interview_session_conversations.execute(session_id)
            if lines is None:
                return jsonify([])
            agent_id = request.args.get("agent_id", type=int)
            if agent_id is not None:
                lines = tuple(ln for ln in lines if ln.agent_id == agent_id)
            return jsonify([dataclasses.asdict(ln) for ln in lines])
        except ValueError:
            return jsonify([])

    @app.route("/api/sessions/<int:session_id>/stage-tracking", methods=["GET"])
    def get_session_stage_tracking(session_id: int):
        """Read-only: last N persisted turn snapshots (no judge / no export refresh)."""
        try:
            return jsonify(bootstrap.read_session_stage_tracking_log.execute(session_id))
        except ValueError as e:
            if "must be positive" in str(e):
                return value_error_http_response(e)
            return jsonify({"error": str(e), "error_type": "not_found"}), 404

    @app.route("/api/sessions/<int:session_id>/routing-logs", methods=["GET"])
    def get_routing_logs(session_id: int):
        """Return routing log entries for a session."""
        try:
            logs = bootstrap.load_interview_session_routing_logs.execute(session_id)
            if logs is None:
                return jsonify([])
            limit = request.args.get("limit", 20, type=int)
            out = [dataclasses.asdict(ln) for ln in logs]
            out.reverse()
            return jsonify(out[:limit])
        except ValueError:
            return jsonify([])

    @app.route("/api/sessions/<int:session_id>/read-bundle", methods=["GET"])
    def get_session_bundle(session_id: int):
        """Read full session bundle (for export or deep view)."""
        try:
            bundle = bootstrap.load_interview_session_for_export.execute(session_id)
            if not bundle:
                return jsonify({"error": "Session not found"}), 404
            return jsonify(dataclasses.asdict(bundle))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
