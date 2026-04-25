"""Post-reply stage progress, optional judge, snapshot, and capped log (auto + manual turns)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from orchestrator_v4.core.entities.interview_turn import TurnContext, TurnConversationLine
from orchestrator_v4.core.entities.stage_evaluator import earliest_unfinished_stage
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


@dataclass(frozen=True)
class FinalizeChatTurnStageTrackingResult:
    """Values needed for `update_session_state` and HTTP turn results after the assistant reply."""

    new_flags: dict[int, bool]
    stage_progress_json: str
    next_current: int
    new_name: str
    session_renamed: str | None
    st_log: str
    stage_tracking: dict[str, Any]


def finalize_chat_turn_stage_tracking(
    *,
    ctx: TurnContext,
    acting_agent_id: int,
    messages_full: list[TurnConversationLine],
    user_input: str,
    turn_endpoint: Literal["auto", "manual"],
    settings_store: StageTrackingSettingsStore,
    stage_completion_judge: InterviewStageCompletionJudge,
    logger: logging.Logger,
) -> FinalizeChatTurnStageTrackingResult:
    """
    After routing and LLM reply: hybrid progress, judge gate, pointer, New Session rename,
    snapshot, capped log. Manual vs auto only affects `turn_endpoint` and which agent id
    is used; agent 5 ineligibility is enforced inside `should_run_stage_tracking_judge`.
    """
    settings = settings_store.read()
    flags_before = dict(ctx.stage_flags())
    new_flags = flags_before
    stage_progress_json = ctx.stage_progress_json
    progress = read_stage_progress(stage_progress_json, acting_agent_id)
    if settings.mode == "hybrid":
        stage_progress_json, progress = advance_stage_progress_json(
            stage_progress_json,
            acting_agent_id,
            tuple(messages_full),
            user_input,
        )

    stage_tracking_decision = should_run_stage_tracking_judge(
        settings,
        acting_agent_id,
        tuple(messages_full),
        user_input,
        progress,
        trigger="turn",
    )
    judge_apply: JudgeApplicationOutcome = "none"
    verdict_view = None
    if stage_tracking_decision.run_judge:
        detail = apply_stage_completion_judge_detailed(
            stage_id=acting_agent_id,
            messages=tuple(messages_full),
            stage_flags_before=ctx.stage_flags(),
            stage_completion_judge=stage_completion_judge,
            logger=logger,
        )
        new_flags = detail.stage_flags
        judge_apply = detail.outcome
        if detail.verdict is not None:
            verdict_view = verdict_to_view(detail.verdict)
        if settings.mode == "hybrid":
            stage_progress_json = record_stage_judge_attempt_json(
                stage_progress_json,
                acting_agent_id,
                tuple(messages_full),
            )

    # `ctx.current_agent_id` is the active stage pointer; recompute from flags after this turn.
    next_current = earliest_unfinished_stage(new_flags)

    session_renamed: str | None = None
    new_name = ctx.name
    if ctx.name == "New Session":
        new_name = user_input[:25] + ("..." if len(user_input) > 25 else "")
        session_renamed = new_name

    ep = read_stage_progress(stage_progress_json, acting_agent_id)
    progress_json_updated = (ctx.stage_progress_json or "") != (stage_progress_json or "")
    stage_snapshot = StageTrackingTurnSnapshot(
        turn_endpoint=turn_endpoint,
        stage_tracking_mode=settings.mode,
        routed_stage_id=acting_agent_id,
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
    return FinalizeChatTurnStageTrackingResult(
        new_flags=new_flags,
        stage_progress_json=stage_progress_json,
        next_current=next_current,
        new_name=new_name,
        session_renamed=session_renamed,
        st_log=st_log,
        stage_tracking=stage_snapshot.to_public_dict(),
    )
