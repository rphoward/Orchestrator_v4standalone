"""Port: route user intent and generate assistant reply for one turn."""

from __future__ import annotations

from typing import Protocol, Sequence

from orchestrator_v4.core.entities.interview_turn import ConversationAppend, RoutingDecision


class InterviewLlmGateway(Protocol):
    def route_intent(
        self,
        user_input: str,
        current_agent_id: int,
        agent_hints: dict[int, str],
    ) -> RoutingDecision:
        ...

    def get_response(
        self,
        user_input: str,
        agent_id: int,
        system_prompt: str,
        model: str,
        thinking_level: str,
        temperature: str,
        include_thoughts: bool,
        history: Sequence[ConversationAppend],
        cross_context: Sequence[ConversationAppend],
        psychological_phase: str,
    ) -> str:
        ...
