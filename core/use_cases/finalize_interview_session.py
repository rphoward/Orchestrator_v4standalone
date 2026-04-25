"""Trigger per-agent summaries and grand synthesis (agent 5), matching v3 finalize."""

from __future__ import annotations

from orchestrator_v4.core.entities.agent_roster_helpers import (
    agent_entry_for_id,
    system_prompt_for_agent,
)
from orchestrator_v4.core.entities.interview_turn import ConversationAppend
from orchestrator_v4.core.ports.interview_llm_gateway import InterviewLlmGateway
from orchestrator_v4.core.ports.interview_session_turn_store import InterviewSessionTurnStore
from orchestrator_v4.core.use_cases.refresh_stage_tracking_before_report import (
    RefreshStageTrackingBeforeReport,
)

_MUSCLE_AGENTS = (1, 2, 3, 4)
_AGENT_NAMES = {
    1: "Brand Spine",
    2: "Founder Invariants",
    3: "Customer Reality",
    4: "Architecture Translation",
}

_SUMMARY_TRIGGER = (
    "Summarize the findings. Focus strictly on the data gathered so far."
)


class FinalizeInterviewSession:
    def __init__(
        self,
        turn_store: InterviewSessionTurnStore,
        llm_gateway: InterviewLlmGateway,
        stage_tracking_refresh: RefreshStageTrackingBeforeReport | None = None,
    ) -> None:
        self._turn_store = turn_store
        self._llm_gateway = llm_gateway
        self._stage_tracking_refresh = stage_tracking_refresh

    def execute(self, session_id: int, *, force: bool = False) -> dict:
        if self._stage_tracking_refresh is not None:
            self._stage_tracking_refresh.execute(session_id, trigger="final_report")
        ctx = self._turn_store.load_turn_context(session_id)

        if not force:
            sparse_agents: list[dict[str, object]] = []
            for agent_id in _MUSCLE_AGENTS:
                user_chats = [
                    m
                    for m in ctx.messages
                    if m.agent_id == agent_id
                    and m.message_type == "chat"
                    and m.role == "user"
                ]
                if len(user_chats) < 1:
                    sparse_agents.append(
                        {
                            "id": agent_id,
                            "name": _AGENT_NAMES.get(agent_id, f"Agent {agent_id}"),
                        }
                    )
            if sparse_agents:
                return {"status": "warning", "sparse_agents": sparse_agents}

        payloads: dict[int, str] = {}
        errors: list[str] = []

        for agent_id in _MUSCLE_AGENTS:
            ctx = self._turn_store.load_turn_context(session_id)
            user_chats = [
                m
                for m in ctx.messages
                if m.agent_id == agent_id
                and m.message_type == "chat"
                and m.role == "user"
            ]
            if len(user_chats) < 1:
                name = _AGENT_NAMES[agent_id]
                payloads[agent_id] = (
                    f"[{name.upper()} PAYLOAD]\nNo substantive conversation occurred."
                )
                continue

            agent_entry = agent_entry_for_id(ctx.agents, agent_id)
            if agent_entry is None:
                errors.append(f"{_AGENT_NAMES[agent_id]}: missing roster entry")
                payloads[agent_id] = (
                    f"[{_AGENT_NAMES[agent_id].upper()} PAYLOAD]\n⚠️ Agent not configured."
                )
                continue

            try:
                self._turn_store.append_messages(
                    session_id,
                    [
                        ConversationAppend(
                            role="user",
                            content=_SUMMARY_TRIGGER,
                            agent_id=agent_id,
                            message_type="summary",
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
                reply = self._llm_gateway.get_response(
                    user_input=_SUMMARY_TRIGGER,
                    agent_id=agent_id,
                    system_prompt=system_prompt_for_agent(ctx.agents, agent_id),
                    model=agent_entry.model,
                    thinking_level=agent_entry.thinking_level,
                    temperature=agent_entry.temperature,
                    include_thoughts=agent_entry.include_thoughts,
                    history=history,
                    cross_context=[],
                    psychological_phase="",
                )
                self._turn_store.append_messages(
                    session_id,
                    [
                        ConversationAppend(
                            role="assistant",
                            content=reply,
                            agent_id=agent_id,
                            message_type="summary",
                        )
                    ],
                )
                payloads[agent_id] = reply
            except Exception as e:
                name = _AGENT_NAMES[agent_id]
                errors.append(f"{name}: ⚠️ Error: {e!s}")
                payloads[agent_id] = (
                    f"[{name.upper()} PAYLOAD]\n⚠️ Error: {e!s}"
                )

        synthesis_agent_id = 5
        synthesis_input = (
            "Here are the four discovery payloads from the interview "
            "session. Some may contain insufficient data. Generate the "
            "complete Architecture Specification based on available "
            "information, degrading gracefully where data is missing.\n\n"
        )
        for agent_id in _MUSCLE_AGENTS:
            name = _AGENT_NAMES[agent_id]
            synthesis_input += (
                f"--- FROM {name.upper()} (Agent {agent_id}) ---\n"
                f"{payloads.get(agent_id, 'No data.')}\n\n"
            )

        synthesis = ""
        ctx = self._turn_store.load_turn_context(session_id)
        synth_entry = agent_entry_for_id(ctx.agents, synthesis_agent_id)
        if synth_entry is None:
            synthesis = "⚠️ Synthesis failed: synthesizer agent not in roster"
            errors.append("Grand Synthesis: synthesizer agent not in roster")
        else:
            try:
                self._turn_store.append_messages(
                    session_id,
                    [
                        ConversationAppend(
                            role="user",
                            content=synthesis_input,
                            agent_id=synthesis_agent_id,
                            message_type="summary",
                        )
                    ],
                )
                synthesis = self._llm_gateway.get_response(
                    user_input=synthesis_input,
                    agent_id=synthesis_agent_id,
                    system_prompt=system_prompt_for_agent(
                        ctx.agents, synthesis_agent_id
                    ),
                    model=synth_entry.model,
                    thinking_level=synth_entry.thinking_level,
                    temperature=synth_entry.temperature,
                    include_thoughts=synth_entry.include_thoughts,
                    history=[],
                    cross_context=[],
                    psychological_phase="",
                )
                self._turn_store.append_messages(
                    session_id,
                    [
                        ConversationAppend(
                            role="assistant",
                            content=synthesis,
                            agent_id=synthesis_agent_id,
                            message_type="summary",
                        )
                    ],
                )
            except Exception as e:
                synthesis = f"⚠️ Synthesis failed: {e}"
                errors.append(f"Grand Synthesis: {e}")

        return {
            "status": "success",
            "payloads": payloads,
            "synthesis": synthesis,
            "errors": errors,
        }
