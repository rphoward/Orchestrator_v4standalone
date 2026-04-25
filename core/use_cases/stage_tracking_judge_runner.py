"""Shared stage judge execution for turn and report-refresh use cases."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence

from orchestrator_v4.core.entities.interview_turn import TurnConversationLine
from orchestrator_v4.core.entities.stage_evaluator import (
    evaluate_stage_completion,
    merge_stage_completion_verdict_into_flags,
)
from orchestrator_v4.core.ports.interview_stage_completion_judge import (
    InterviewStageCompletionJudge,
)


def apply_stage_completion_judge(
    *,
    stage_id: int,
    messages: Sequence[TurnConversationLine],
    stage_flags_before: Mapping[int, bool],
    stage_completion_judge: InterviewStageCompletionJudge,
    logger: logging.Logger,
) -> dict[int, bool]:
    try:
        verdict = stage_completion_judge.judge_stage_completion(
            stage_id=stage_id,
            messages=tuple(messages),
            stage_flags_before=stage_flags_before,
        )
        if verdict.reason.startswith("judge_error:"):
            return evaluate_stage_completion(stage_id, tuple(messages), stage_flags_before)
        return merge_stage_completion_verdict_into_flags(verdict, stage_flags_before)
    except Exception:
        logger.warning(
            "stage_completion_judge raised; falling back to heuristic",
            exc_info=True,
        )
        return evaluate_stage_completion(stage_id, tuple(messages), stage_flags_before)
