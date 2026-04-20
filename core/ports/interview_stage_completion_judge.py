"""Port: grade whether an interview stage is complete from the transcript.

Adapters live under ``infrastructure/``. Use cases depend only on this
Protocol. The Gemini adapter `GeminiStageCompletionJudge` and the offline
`FakeStageCompletionJudge` both implement this contract.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from orchestrator_v4.core.entities.interview_turn import TurnConversationLine
from orchestrator_v4.core.entities.stage_completion_verdict import (
    StageCompletionVerdict,
)


class InterviewStageCompletionJudge(Protocol):
    """Decides whether stage N (1..4) is complete given the transcript so far."""

    def judge_stage_completion(
        self,
        stage_id: int,
        messages: Sequence[TurnConversationLine],
        stage_flags_before: Mapping[int, bool],
    ) -> StageCompletionVerdict:
        """Return a ``StageCompletionVerdict`` for ``stage_id``.

        Adapters should never raise for transient model errors (API timeouts,
        empty responses, unparseable JSON). Instead return a verdict with
        ``stage_complete=False``, ``confidence=0.0``, and a ``reason`` prefixed
        ``"judge_error: "`` so the use case can apply its heuristic fallback.

        The use case guarantees ``stage_id`` is the active agent for the turn;
        the adapter still validates it and returns a ``judge_error:`` verdict
        for stage ids outside 1..4, matching the domain-boundary defense
        documented in ``merge_stage_completion_verdict_into_flags``.
        """
        ...
