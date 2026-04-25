"""Shared stage judge execution for turn and report-refresh use cases."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from orchestrator_v4.core.entities.interview_turn import TurnConversationLine
from orchestrator_v4.core.entities.stage_completion_verdict import StageCompletionVerdict
from orchestrator_v4.core.entities.stage_evaluator import (
    evaluate_stage_completion,
    merge_stage_completion_verdict_into_flags,
)
from orchestrator_v4.core.entities.stage_tracking_turn_snapshot import (
    JudgeApplicationOutcome,
    StageTrackingVerdictView,
)
from orchestrator_v4.core.ports.interview_stage_completion_judge import (
    InterviewStageCompletionJudge,
)


@dataclass(frozen=True)
class StageCompletionJudgeResult:
    """Result of a judge attempt, including new flags and how they were produced."""

    stage_flags: dict[int, bool]
    outcome: JudgeApplicationOutcome
    verdict: StageCompletionVerdict | None


def apply_stage_completion_judge(
    *,
    stage_id: int,
    messages: Sequence[TurnConversationLine],
    stage_flags_before: Mapping[int, bool],
    stage_completion_judge: InterviewStageCompletionJudge,
    logger: logging.Logger,
) -> dict[int, bool]:
    return apply_stage_completion_judge_detailed(
        stage_id=stage_id,
        messages=messages,
        stage_flags_before=stage_flags_before,
        stage_completion_judge=stage_completion_judge,
        logger=logger,
    ).stage_flags


def apply_stage_completion_judge_detailed(
    *,
    stage_id: int,
    messages: Sequence[TurnConversationLine],
    stage_flags_before: Mapping[int, bool],
    stage_completion_judge: InterviewStageCompletionJudge,
    logger: logging.Logger,
) -> StageCompletionJudgeResult:
    try:
        verdict = stage_completion_judge.judge_stage_completion(
            stage_id=stage_id,
            messages=tuple(messages),
            stage_flags_before=stage_flags_before,
        )
        if verdict.reason.startswith("judge_error:"):
            return StageCompletionJudgeResult(
                stage_flags=evaluate_stage_completion(
                    stage_id, tuple(messages), stage_flags_before
                ),
                outcome="judge_error_heuristic",
                verdict=verdict,
            )
        return StageCompletionJudgeResult(
            stage_flags=merge_stage_completion_verdict_into_flags(
                verdict, stage_flags_before
            ),
            outcome="verdict",
            verdict=verdict,
        )
    except Exception:
        logger.warning(
            "stage_completion_judge raised; falling back to heuristic",
            exc_info=True,
        )
        return StageCompletionJudgeResult(
            stage_flags=evaluate_stage_completion(
                stage_id, tuple(messages), stage_flags_before
            ),
            outcome="exception_heuristic",
            verdict=None,
        )


def verdict_to_view(verdict: StageCompletionVerdict) -> StageTrackingVerdictView:
    return StageTrackingVerdictView(
        stage_id=verdict.stage_id,
        stage_complete=verdict.stage_complete,
        confidence=verdict.confidence,
        reason=verdict.reason,
    )
