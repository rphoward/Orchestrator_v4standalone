"""Deterministic InterviewStageCompletionJudge for offline dev and tests.

Bootstrap wires this in when no ``GEMINI_API_KEY`` is configured. By default
the offline-wired instance uses ``default_reason="judge_error: offline stub"``
so the use-case heuristic fallback fires every turn — matching the repo's
prior offline behavior. Ad-hoc tests can instead construct this with
``default_reason="stub-verdict"`` (the class default) to assert the stub's own
identity without triggering the fallback branch.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from orchestrator_v4.core.entities.interview_turn import TurnConversationLine
from orchestrator_v4.core.entities.stage_completion_verdict import (
    StageCompletionVerdict,
)
from orchestrator_v4.core.ports.interview_stage_completion_judge import (
    InterviewStageCompletionJudge,
)


class FakeStageCompletionJudge(InterviewStageCompletionJudge):
    def __init__(
        self,
        *,
        default_complete: bool = False,
        default_confidence: float = 0.0,
        default_reason: str = "stub-verdict",
    ) -> None:
        self._default_complete = default_complete
        self._default_confidence = default_confidence
        self._default_reason = default_reason

    def judge_stage_completion(
        self,
        stage_id: int,
        messages: Sequence[TurnConversationLine],
        stage_flags_before: Mapping[int, bool],
    ) -> StageCompletionVerdict:
        _ = (messages, stage_flags_before)
        return StageCompletionVerdict(
            stage_id=stage_id,
            stage_complete=self._default_complete,
            confidence=self._default_confidence,
            reason=self._default_reason,
        )
