"""Send opening prompts to muscle agents (1–4) for a new session."""

from __future__ import annotations

from orchestrator_v4.core.entities.agent_roster_helpers import (
    agent_entry_for_id,
    system_prompt_for_agent,
)
from orchestrator_v4.core.entities.interview_turn import ConversationAppend
from orchestrator_v4.core.entities.pierce_holt_engine import get_tone_directive
from orchestrator_v4.core.ports.interview_llm_gateway import InterviewLlmGateway
from orchestrator_v4.core.ports.interview_session_turn_store import InterviewSessionTurnStore

_COACH_PERSONA = (
    "You are helping a friendly, approachable business consultant who "
    "works with small business owners — not corporate executives. Keep "
    "the vibe warm, professional, and encouraging."
)

_INIT_MESSAGE = (
    f"{_COACH_PERSONA}\n\n"
    "Begin the session. Provide your opening output using your "
    "required format, including your first suggested question "
    "for the consultant to ask the founder."
)

_MUSCLE_AGENT_IDS = (1, 2, 3, 4)


class InitializeInterviewSession:
    def __init__(
        self,
        turn_store: InterviewSessionTurnStore,
        llm_gateway: InterviewLlmGateway,
    ) -> None:
        self._turn_store = turn_store
        self._llm_gateway = llm_gateway

    def execute(self, session_id: int) -> dict[int, str]:
        results: dict[int, str] = {}

        for agent_id in _MUSCLE_AGENT_IDS:
            ctx = self._turn_store.load_turn_context(session_id)
            agent_entry = agent_entry_for_id(ctx.agents, agent_id)
            if agent_entry is None:
                results[agent_id] = f"⚠️ Error: Agent {agent_id} not in roster"
                continue

            try:
                self._turn_store.append_messages(
                    session_id,
                    [
                        ConversationAppend(
                            role="user",
                            content=_INIT_MESSAGE,
                            agent_id=agent_id,
                            message_type="init",
                        )
                    ],
                )
                ctx = self._turn_store.load_turn_context(session_id)
                history = [
                    ConversationAppend(
                        role=m.role,
                        content=m.content,
                        agent_id=m.agent_id,
                        message_type=m.message_type,
                    )
                    for m in ctx.messages
                    if m.agent_id == agent_id
                ]
                tone = get_tone_directive(agent_id, 0)
                reply = self._llm_gateway.get_response(
                    user_input=_INIT_MESSAGE,
                    agent_id=agent_id,
                    system_prompt=system_prompt_for_agent(ctx.agents, agent_id),
                    model=agent_entry.model,
                    thinking_level=agent_entry.thinking_level,
                    temperature=agent_entry.temperature,
                    include_thoughts=agent_entry.include_thoughts,
                    history=history,
                    cross_context=[],
                    psychological_phase=tone,
                )
                self._turn_store.append_messages(
                    session_id,
                    [
                        ConversationAppend(
                            role="assistant",
                            content=reply,
                            agent_id=agent_id,
                            message_type="init",
                        )
                    ],
                )
                results[agent_id] = reply
            except Exception as e:
                results[agent_id] = f"⚠️ Error: {e!s}"

        return results
