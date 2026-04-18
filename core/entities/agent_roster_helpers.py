"""Pure roster lookups shared by interview use cases (no I/O)."""

from __future__ import annotations

from orchestrator_v4.core.entities.interview_turn import (
    InterviewTurnAgentRosterEntry,
    TurnConversationLine,
)


def roster_agent_name(
    agents: tuple[InterviewTurnAgentRosterEntry, ...], agent_id: int
) -> str:
    for a in agents:
        if a.id == agent_id:
            return a.name
    return f"Agent {agent_id}"


def system_prompt_for_agent(
    agents: tuple[InterviewTurnAgentRosterEntry, ...], agent_id: int
) -> str:
    for a in agents:
        if a.id == agent_id:
            return a.system_prompt
    return ""


def agent_entry_for_id(
    agents: tuple[InterviewTurnAgentRosterEntry, ...], agent_id: int
) -> InterviewTurnAgentRosterEntry | None:
    for a in agents:
        if a.id == agent_id:
            return a
    return None


def count_user_chat(messages: tuple[TurnConversationLine, ...]) -> int:
    return sum(1 for m in messages if m.role == "user" and m.message_type == "chat")
