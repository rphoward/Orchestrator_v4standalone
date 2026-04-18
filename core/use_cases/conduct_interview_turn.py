"""Orchestrates a single interview turn (routing, ethos, LLM reply, persistence via ports)."""

from __future__ import annotations

from orchestrator_v4.core.entities.agent_roster_helpers import (
    agent_entry_for_id,
    count_user_chat,
    roster_agent_name,
    system_prompt_for_agent,
)
from orchestrator_v4.core.entities.interview_turn import (
    ConversationAppend,
    InterviewTurnResult,
    RoutingLogAppend,
    TurnConversationLine,
)
from orchestrator_v4.core.entities.pierce_holt_engine import (
    get_tone_directive,
    psychological_phase_value,
)
from orchestrator_v4.core.entities.stage_evaluator import (
    apply_routing_veto,
    evaluate_stage_completion,
)
from orchestrator_v4.core.ports.interview_llm_gateway import InterviewLlmGateway
from orchestrator_v4.core.ports.interview_session_turn_store import InterviewSessionTurnStore


class ConductInterviewTurn:
    def __init__(
        self,
        turn_store: InterviewSessionTurnStore,
        llm_gateway: InterviewLlmGateway,
    ) -> None:
        self._turn_store = turn_store
        self._llm_gateway = llm_gateway

    def execute(self, session_id: int, user_input: str) -> InterviewTurnResult:
        text = user_input.strip()
        if not text:
            raise ValueError("message is required")

        ctx = self._turn_store.load_turn_context(session_id)

        agent_hints = {a.id: a.router_hint for a in ctx.agents}
        raw = self._llm_gateway.route_intent(text, ctx.current_agent_id, agent_hints)
        decision = apply_routing_veto(raw, ctx.current_agent_id, ctx.stage_flags())

        target_agent_id = decision.target_agent_id
        agent_name = roster_agent_name(ctx.agents, target_agent_id)

        self._turn_store.append_routing_log(
            session_id,
            RoutingLogAppend(
                input_text=text,
                agent_id=target_agent_id,
                agent_name=agent_name,
                reason=decision.reason,
            ),
        )

        self._turn_store.append_messages(
            session_id,
            [
                ConversationAppend(
                    role="user",
                    content=text,
                    agent_id=target_agent_id,
                    message_type="chat",
                )
            ],
        )

        messages_after_user: list[TurnConversationLine] = list(ctx.messages)
        messages_after_user.append(
            TurnConversationLine(
                agent_id=target_agent_id,
                role="user",
                content=text,
                message_type="chat",
                timestamp="",
            )
        )
        total_user = count_user_chat(tuple(messages_after_user))
        tone = get_tone_directive(target_agent_id, total_user)
        phase = psychological_phase_value(target_agent_id, total_user)

        history = [
            ConversationAppend(
                role=m.role,
                content=m.content,
                agent_id=m.agent_id,
                message_type=m.message_type,
            )
            for m in ctx.messages
            if m.agent_id == target_agent_id
        ]
        history.append(
            ConversationAppend(
                role="user",
                content=text,
                agent_id=target_agent_id,
                message_type="chat",
            )
        )

        cross_lines = [
            m
            for m in ctx.messages
            if m.agent_id != target_agent_id and m.message_type == "chat"
        ][-6:]
        cross_context = [
            ConversationAppend(
                role=m.role,
                content=m.content,
                agent_id=m.agent_id,
                message_type=m.message_type,
                source_agent_name=roster_agent_name(ctx.agents, m.agent_id),
            )
            for m in cross_lines
        ]

        system_prompt = system_prompt_for_agent(ctx.agents, target_agent_id)
        agent_entry = agent_entry_for_id(ctx.agents, target_agent_id)
        reply = self._llm_gateway.get_response(
            user_input=text,
            agent_id=target_agent_id,
            system_prompt=system_prompt,
            model=agent_entry.model if agent_entry else "",
            thinking_level=agent_entry.thinking_level if agent_entry else "",
            temperature=agent_entry.temperature if agent_entry else "",
            include_thoughts=agent_entry.include_thoughts if agent_entry else False,
            history=history,
            cross_context=cross_context,
            psychological_phase=tone,
        )

        self._turn_store.append_messages(
            session_id,
            [
                ConversationAppend(
                    role="assistant",
                    content=reply,
                    agent_id=target_agent_id,
                    message_type="chat",
                )
            ],
        )

        messages_full: list[TurnConversationLine] = list(messages_after_user)
        messages_full.append(
            TurnConversationLine(
                agent_id=target_agent_id,
                role="assistant",
                content=reply,
                message_type="chat",
                timestamp="",
            )
        )

        new_flags = evaluate_stage_completion(
            target_agent_id,
            tuple(messages_full),
            ctx.stage_flags(),
        )

        # Current agent must match who handled this turn (messages + reply are on target_agent_id).
        # workflow_status is semantic only; STAY can still route to another agent (e.g. backward hop).
        next_current = target_agent_id

        session_renamed: str | None = None
        new_name = ctx.name
        if ctx.name == "New Session":
            new_name = text[:25] + ("..." if len(text) > 25 else "")
            session_renamed = new_name

        self._turn_store.update_session_state(
            session_id,
            current_agent_id=next_current,
            stage_flags=new_flags,
            name=new_name if session_renamed else None,
        )

        return InterviewTurnResult(
            agent_id=target_agent_id,
            agent_name=agent_name,
            routing_reason=decision.reason,
            workflow_status=decision.workflow_status,
            response=reply,
            psychological_phase=phase,
            session_renamed=session_renamed,
        )
