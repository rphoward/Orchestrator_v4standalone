"""
Bootstrap wiring **smoke test** (CLI prints only — **no HTTP server**).

This module is intentionally **not** named ``main`` so it is not confused with the real
application entry (``orchestrator_v4.presentation.app`` or repo-root
``orchestrator4_entry.py`` for PyInstaller).

**Run:** ``python -m orchestrator_v4.bootstrap_smoke`` or ``python run_dev.py --smoke``
(from ``orchestrator_v4/``).

Composition and dependency injection live in ``orchestrator_v4/bootstrap.py``.
"""

from __future__ import annotations

from orchestrator_v4.bootstrap import (
    list_interview_sessions,
    load_interview_prompt_body,
    load_interview_session_for_export,
    read_agent_overrides,
)


def main() -> None:
    """Smoke-test Orchestrator4 wiring (overrides + prompt body + session catalog)."""
    overrides = read_agent_overrides.execute()
    print("Orchestrator4 — ReadAgentOverrides (default ids 1–4)")
    for o in overrides:
        print(
            f"  agent {o.agent_id}: "
            f"thinking={o.thinking_level!r} "
            f"temperature={o.temperature!r} "
            f"include_thoughts={o.include_thoughts}"
        )
    try:
        body = load_interview_prompt_body.execute(1)
        preview = body[:120].replace("\n", " ")
        print("Orchestrator4 — LoadInterviewPromptBody (agent 1, first 120 chars)")
        print(f"  {preview!r}…")
    except ValueError as e:
        print("Orchestrator4 — LoadInterviewPromptBody (agent 1)")
        print(f"  skipped: {e}")
    try:
        sessions = list_interview_sessions.execute()
        print(f"Orchestrator4 — ListInterviewSessions ({len(sessions)} in DB)")
        if sessions:
            s0 = sessions[0]
            print(f"  latest: id={s0.id} name={s0.name!r} client={s0.client_name!r}")
        sid = sessions[0].id if sessions else 1
        bundle = load_interview_session_for_export.execute(sid)
        if bundle:
            h = bundle.headline
            print(
                "Orchestrator4 — LoadInterviewSessionForExport "
                f"(id={h.id} messages={len(bundle.conversation_lines)} "
                f"routing_logs={len(bundle.routing_log_lines)})"
            )
        else:
            print(
                f"Orchestrator4 — LoadInterviewSessionForExport (no session id={sid})"
            )
    except Exception as e:
        print("Orchestrator4 — ListInterviewSessions / LoadInterviewSessionForExport")
        print(f"  skipped: {e}")


if __name__ == "__main__":
    main()
