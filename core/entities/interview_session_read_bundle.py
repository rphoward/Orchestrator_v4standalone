"""Read-only bundle for export/tooling: session headline + conversations + routing logs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InterviewSessionReadHeadline:
    """One `sessions` row — fields needed for export (includes stage flags)."""

    id: int
    name: str
    client_name: str
    summary: str
    current_agent_id: int
    stage1_complete: bool
    stage2_complete: bool
    stage3_complete: bool
    stage4_complete: bool
    created_at: str
    updated_at: str

    def __post_init__(self) -> None:
        if self.id < 1:
            raise ValueError(f"id must be positive, got {self.id}")


@dataclass(frozen=True)
class InterviewConversationLine:
    """One row from `conversations` (ordered by timestamp ASC in the adapter)."""

    agent_id: int
    role: str
    content: str
    message_type: str
    timestamp: str


@dataclass(frozen=True)
class InterviewRoutingLogLine:
    """One row from `routing_logs` (ordered by timestamp ASC in the adapter)."""

    input_text: str
    agent_id: int
    agent_name: str
    reason: str
    timestamp: str


@dataclass(frozen=True)
class InterviewSessionReadBundle:
    """Aggregate read model for export — no routing or turn execution."""

    headline: InterviewSessionReadHeadline
    conversation_lines: tuple[InterviewConversationLine, ...]
    routing_log_lines: tuple[InterviewRoutingLogLine, ...]
