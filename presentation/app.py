"""
Orchestrator 4 - Main Application Entrypoint
════════════════════════════════════════════
This is the new "clean" web server for v4, completely decoupled from v3.
It uses the composition root (`orchestrator_v4.bootstrap`) to access use cases.
"""

from __future__ import annotations

import logging
import os
import pathlib

from flask import Flask, jsonify, send_from_directory

from orchestrator_v4 import bootstrap
from orchestrator_v4.infrastructure.runtime_executable_layout import is_frozen_bundle
from orchestrator_v4.presentation.agent_configuration_routes import (
    register_agent_configuration_routes,
)
from orchestrator_v4.presentation.gemini_connection_routes import (
    register_gemini_connection_routes,
)
from orchestrator_v4.presentation.interview_session_routes import (
    register_interview_session_routes,
)
from orchestrator_v4.presentation.prompt_template_routes import (
    register_prompt_template_routes,
)

_STATIC_DIR = pathlib.Path(__file__).resolve().parent / "static"

# Ensure our orchestrator_v4.* INFO lines reach the console in dev; basicConfig
# is a no-op if the root logger already has handlers (so this does not fight Flask).
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("orchestrator_v4").setLevel(logging.INFO)

app = Flask(__name__, static_folder=str(_STATIC_DIR), static_url_path="/static")
app.logger.setLevel(logging.INFO)

register_interview_session_routes(app)
register_prompt_template_routes(app)
register_gemini_connection_routes(app)
register_agent_configuration_routes(app)


@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    app.logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify(
        {
            "error": "An unexpected internal error occurred.",
            "error_type": "unknown_error",
        }
    ), 500


def main() -> None:
    """Run the API server (used by ``python -m orchestrator_v4.presentation.app`` and PyInstaller)."""
    port = int(os.environ.get("ORCHESTRATOR_PORT", "5001"))
    debug = (
        os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
        and not is_frozen_bundle()
    )
    if is_frozen_bundle() and not bootstrap.gemini_api_key_configured:
        app.logger.warning(
            "GEMINI_API_KEY is not set — interview turns use the offline stub. "
            "IT can place a .env file next to this executable with GEMINI_API_KEY=… "
            "(company key), or set the variable system-wide."
        )
    elif not bootstrap.gemini_api_key_configured:
        print(
            "\n⚠️  GEMINI_API_KEY is not set — interview turns use the offline stub "
            "(routing reason looks like stub-route; replies echo your text). "
            "Add GEMINI_API_KEY to .env in the project folder or paste a key in Settings, "
            "then restart this server.\n"
        )
    host = os.environ.get("ORCHESTRATOR_HOST", "127.0.0.1")
    print(f"\n🎙️  Orchestrator V4 -> http://{host}:{port}\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
