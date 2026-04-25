"""One interview turn to a caller-chosen agent (no router)."""

from __future__ import annotations

import logging

from orchestrator_v4.core.entities.agent_roster_helpers import (
    agent_entry_for_id,
    count_user_chat,
    roster_agent_name,
    system_prompt_for_agent,
)
from orchestrator_v4.core.entities.interview_turn import (
    ConversationAppend,
    ManualInterviewTurnResult,
    RoutingLogAppend,
    TurnConversationLine,
)
from orchestrator_v4.core.entities.pierce_holt_engine import get_tone_directive
from orchestrator_v4.core.entities.stage_evaluator import (
    earliest_unfinished_stage,
)
from orchestrator_v4.core.entities.stage_progress import (
    advance_stage_progress_json,
    read_stage_progress,
    record_stage_judge_attempt_json,
    should_run_stage_tracking_judge,
)
from orchestrator_v4.core.entities.stage_tracking_turn_snapshot import (
    JudgeApplicationOutcome,
    StageTrackingTurnSnapshot,
    append_capped_stage_tracking_log,
    compact_evaluated_progress,
)
from orchestrator_v4.core.ports.interview_llm_gateway import InterviewLlmGateway
from orchestrator_v4.core.ports.interview_session_turn_store import InterviewSessionTurnStore
from orchestrator_v4.core.ports.interview_stage_completion_judge import (
    InterviewStageCompletionJudge,
)
from orchestrator_v4.core.ports.stage_tracking_settings_store import (
    StageTrackingSettingsStore,
)
from orchestrator_v4.core.use_cases.stage_tracking_judge_runner import (
    apply_stage_completion_judge_detailed,
    verdict_to_view,
)

MANUAL_ROUTING_REASON = "Manual override"

_LOG = logging.getLogger(__name__)


class ConductManualInterviewTurn:
    def __init__(
        self,
        turn_store: InterviewSessionTurnStore,
        llm_gateway: InterviewLlmGateway,
        stage_completion_judge: InterviewStageCompletionJudge,
        stage_tracking_settings_store: StageTrackingSettingsStore,
    ) -> None:
        self._turn_store = turn_store
        self._llm_gateway = llm_gateway
        self._stage_completion_judge = stage_completion_judge
        self._stage_tracking_settings_store = stage_tracking_settings_store

    def execute(
        self, session_id: int, agent_id: int, user_input: str
    ) -> ManualInterviewTurnResult:
        text = user_input.strip()
        if not text:
            raise ValueError("message is required")

        ctx = self._turn_store.load_turn_context(session_id)
        agent_entry = agent_entry_for_id(ctx.agents, agent_id)
        if agent_entry is None:
            raise ValueError(f"Agent {agent_id} not found")

        agent_name = roster_agent_name(ctx.agents, agent_id)

        self._turn_store.append_routing_log(
            session_id,
            RoutingLogAppend(
                input_text=text,
                agent_id=agent_id,
                agent_name=agent_name,
                reason=MANUAL_ROUTING_REASON,
            ),
        )

        self._turn_store.append_messages(
            session_id,
            [
                ConversationAppend(
                    role="user",
                    content=text,
                    agent_id=agent_id,
                    message_type="chat",
                )
            ],
        )

        messages_after_user: list[TurnConversationLine] = list(ctx.messages)
        messages_after_user.append(
            TurnConversationLine(
                agent_id=agent_id,
                role="user",
                content=text,
                message_type="chat",
                timestamp="",
            )
        )
        total_user = count_user_chat(tuple(messages_after_user))
        tone = get_tone_directive(agent_id, total_user)

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
        history.append(
            ConversationAppend(
                role="user",
                content=text,
                agent_id=agent_id,
                message_type="chat",
            )
        )

        cross_lines = [
            m
            for m in ctx.messages
            if m.agent_id != agent_id and m.message_type == "chat"
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

        system_prompt = system_prompt_for_agent(ctx.agents, agent_id)
        reply = self._llm_gateway.get_response(
            user_input=text,
            agent_id=agent_id,
            system_prompt=system_prompt,
            model=agent_entry.model,
            thinking_level=agent_entry.thinking_level,
            temperature=agent_entry.temperature,
            include_thoughts=agent_entry.include_thoughts,
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
                    agent_id=agent_id,
                    message_type="chat",
                )
            ],
        )

        messages_full: list[TurnConversationLine] = list(messages_after_user)
        messages_full.append(
            TurnConversationLine(
                agent_id=agent_id,
                role="assistant",
                content=reply,
                message_type="chat",
                timestamp="",
            )
        )

        settings = self._stage_tracking_settings_store.read()
        flags_before = dict(ctx.stage_flags())
        new_flags = flags_before
        stage_progress_json = ctx.stage_progress_json
        progress = read_stage_progress(stage_progress_json, agent_id)
        if settings.mode == "hybrid":
            stage_progress_json, progress = advance_stage_progress_json(
                stage_progress_json,
                agent_id,
                tuple(messages_full),
                text,
            )

        stage_tracking_decision = should_run_stage_tracking_judge(
            settings,
            agent_id,
            tuple(messages_full),
            text,
            progress,
            trigger="turn",
        )
        judge_apply: JudgeApplicationOutcome = "none"
        verdict_view = None
        if stage_tracking_decision.run_judge:
            detail = apply_stage_completion_judge_detailed(
                stage_id=agent_id,
                messages=tuple(messages_full),
                stage_flags_before=ctx.stage_flags(),
                stage_completion_judge=self._stage_completion_judge,
                logger=_LOG,
            )
            new_flags = detail.stage_flags
            judge_apply = detail.outcome
            if detail.verdict is not None:
                verdict_view = verdict_to_view(detail.verdict)
            if settings.mode == "hybrid":
                stage_progress_json = record_stage_judge_attempt_json(
                    stage_progress_json,
                    agent_id,
                    tuple(messages_full),
                )

        # session.current_agent_id holds the active stage pointer (earliest
        # unfinished stage 1..4). A manual turn can still flip the targeted
        # agent's stage flag, which may move the pointer; otherwise it stays
        # where it was. Who handled THIS turn is still `agent_id` in the result.
        next_current = earliest_unfinished_stage(new_flags)

        session_renamed: str | None = None
        new_name = ctx.name
        if ctx.name == "New Session":
            new_name = text[:25] + ("..." if len(text) > 25 else "")
            session_renamed = new_name

        ep = read_stage_progress(stage_progress_json, agent_id)
        progress_json_updated = (ctx.stage_progress_json or "") != (
            stage_progress_json or ""
        )
        stage_snapshot = StageTrackingTurnSnapshot(
            turn_endpoint="manual",
            stage_tracking_mode=settings.mode,
            routed_stage_id=agent_id,
            active_stage_pointer_before=ctx.current_agent_id,
            active_stage_pointer_after=next_current,
            progress_json_updated=progress_json_updated,
            evaluated_progress=compact_evaluated_progress(ep),
            gate_reason=stage_tracking_decision.reason,
            judge_ran=bool(stage_tracking_decision.run_judge),
            judge_outcome=judge_apply,
            verdict=verdict_view,
            stage_flags_before=flags_before,
            stage_flags_after=new_flags,
        )
        st_log = append_capped_stage_tracking_log(
            ctx.stage_tracking_log_json,
            stage_snapshot.to_public_dict(),
        )

        self._turn_store.update_session_state(
            session_id,
            current_agent_id=next_current,
            stage_flags=new_flags,
            name=new_name if session_renamed else None,
            stage_progress_json=stage_progress_json
            if stage_progress_json != ctx.stage_progress_json
            else None,
            stage_tracking_log_json=st_log,
        )

        return ManualInterviewTurnResult(
            agent_id=agent_id,
            agent_name=agent_name,
            response=reply,
            routing_reason=MANUAL_ROUTING_REASON,
            session_renamed=session_renamed,
            active_stage_pointer=next_current,
            stage_tracking=stage_snapshot.to_public_dict(),
        )
