"""Build v3-compatible ``orchestrator_export`` JSON from a read bundle."""

from __future__ import annotations

from datetime import datetime, timezone

from orchestrator_v4.core.entities.interview_session_read_bundle import (
    InterviewSessionReadBundle,
)


def build_v3_session_export_document(bundle: InterviewSessionReadBundle) -> dict:
    """Shape matches v3 ``SessionManagementUseCase.export_session`` for import round-trip."""
    h = bundle.headline
    agents_dict: dict[int, dict] = {}
    for line in bundle.conversation_lines:
        aid = line.agent_id
        if aid not in agents_dict:
            agents_dict[aid] = {
                "agent_id": aid,
                "agent_name": f"Agent {aid}",
                "messages": [],
            }
        agents_dict[aid]["messages"].append(
            {
                "agent_id": aid,
                "role": line.role,
                "content": line.content,
                "message_type": line.message_type,
                "timestamp": line.timestamp,
            }
        )

    session_payload = {
        "id": h.id,
        "name": h.name,
        "client_name": h.client_name,
        "summary": h.summary,
        "current_agent_id": h.current_agent_id,
        "stage1_complete": h.stage1_complete,
        "stage2_complete": h.stage2_complete,
        "stage3_complete": h.stage3_complete,
        "stage4_complete": h.stage4_complete,
        "created_at": h.created_at,
        "updated_at": h.updated_at,
        "messages": [],
        "routing_logs": [],
    }

    routing_logs = [
        {
            "input_text": ln.input_text,
            "agent_id": ln.agent_id,
            "agent_name": ln.agent_name,
            "reason": ln.reason,
            "timestamp": ln.timestamp,
        }
        for ln in bundle.routing_log_lines
    ]

    return {
        "orchestrator_export": {
            "version": "1.0",
            "type": "session",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "exported_from": "Interview Orchestrator V4",
        },
        "session": session_payload,
        "conversations": list(agents_dict.values()),
        "routing_logs": routing_logs,
    }
