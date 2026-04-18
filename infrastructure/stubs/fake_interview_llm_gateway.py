"""Deterministic InterviewLlmGateway for B1 tests and local wiring."""

from __future__ import annotations

from collections.abc import Sequence

from orchestrator_v4.core.entities.interview_turn import ConversationAppend, RoutingDecision
from orchestrator_v4.core.ports.interview_llm_gateway import InterviewLlmGateway


class FakeInterviewLlmGateway(InterviewLlmGateway):
    def __init__(
        self,
        *,
        route_to_agent_id: int | None = None,
        workflow_status: str = "STAY",
        route_reason: str = "stub-route",
        response_prefix: str = "echo:",
    ) -> None:
        self._route_to = route_to_agent_id
        self._workflow_status = workflow_status
        self._route_reason = route_reason
        self._response_prefix = response_prefix

    def route_intent(
        self,
        user_input: str,
        current_agent_id: int,
        agent_hints: dict[int, str],
    ) -> RoutingDecision:
        _ = user_input, agent_hints
        target = self._route_to if self._route_to is not None else current_agent_id
        return RoutingDecision(
            target_agent_id=target,
            workflow_status=self._workflow_status,
            reason=self._route_reason,
        )

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
        _ = (
            agent_id,
            system_prompt,
            model,
            thinking_level,
            temperature,
            include_thoughts,
            history,
            cross_context,
            psychological_phase,
        )
        return f"{self._response_prefix}{user_input}"
