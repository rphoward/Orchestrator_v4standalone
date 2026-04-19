"""Value types for interview turn execution (routing, messages, turn result)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InterviewTurnAgentRosterEntry:
    """One agent as needed for routing and response (prompts loaded by the store)."""

    id: int
    name: str
    system_prompt: str
    router_hint: str
    model: str = ""
    thinking_level: str = ""
    temperature: str = ""
    include_thoughts: bool = False
    is_synthesizer: bool = False


@dataclass(frozen=True)
class TurnConversationLine:
    """One persisted conversation row shape used inside TurnContext."""

    agent_id: int
    role: str
    content: str
    message_type: str
    timestamp: str


@dataclass(frozen=True)
class TurnRoutingLogLine:
    """One routing log row inside TurnContext."""

    input_text: str
    agent_id: int
    agent_name: str
    reason: str
    timestamp: str


@dataclass(frozen=True)
class TurnContext:
    """Headline session state plus messages, routing history, and agent roster."""

    session_id: int
    name: str
    current_agent_id: int
    stage1_complete: bool
    stage2_complete: bool
    stage3_complete: bool
    stage4_complete: bool
    messages: tuple[TurnConversationLine, ...]
    routing_logs: tuple[TurnRoutingLogLine, ...]
    agents: tuple[InterviewTurnAgentRosterEntry, ...]

    def stage_flags(self) -> dict[int, bool]:
        return {
            1: self.stage1_complete,
            2: self.stage2_complete,
            3: self.stage3_complete,
            4: self.stage4_complete,
        }


@dataclass(frozen=True)
class ConversationAppend:
    """Append payload for conversations table (timestamp optional for test doubles)."""

    role: str
    content: str
    agent_id: int
    message_type: str = "chat"
    timestamp: str | None = None
    source_agent_name: str | None = None


@dataclass(frozen=True)
class RoutingLogAppend:
    """Append payload for routing_logs."""

    input_text: str
    agent_id: int
    agent_name: str
    reason: str
    timestamp: str | None = None


@dataclass(frozen=True)
class RoutingDecision:
    """LLM router output before domain veto."""

    target_agent_id: int
    workflow_status: str
    reason: str


@dataclass(frozen=True)
class InterviewTurnResult:
    """Structured result of ConductInterviewTurn.execute.

    `active_stage_pointer` is the earliest unfinished stage in 1..4 after this
    turn's stage flags were recomputed. The UI uses it to update the stage
    badge without an extra round-trip to /api/sessions.
    """

    agent_id: int
    agent_name: str
    routing_reason: str
    workflow_status: str
    response: str
    psychological_phase: str
    session_renamed: str | None
    active_stage_pointer: int = 0


@dataclass(frozen=True)
class ManualInterviewTurnResult:
    """Structured result of ConductManualInterviewTurn.execute (no router)."""

    agent_id: int
    agent_name: str
    response: str
    routing_reason: str = "Manual override"
    session_renamed: str | None = None
    active_stage_pointer: int = 0
