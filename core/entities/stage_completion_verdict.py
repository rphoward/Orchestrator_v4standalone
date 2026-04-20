"""Value type: outcome of an InterviewStageCompletionJudge call (no I/O).

`StageCompletionVerdict` is the structured answer returned by the judge port
after it grades whether a single interview stage (1..4) is complete based on
the transcript. The use case then passes the verdict through
`merge_stage_completion_verdict_into_flags` in
``core/entities/stage_evaluator.py`` to decide whether the stage's flag flips.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Minimum confidence for a verdict to flip a stage flag from False to True.
# Tuned conservatively for v1 — weak-evidence verdicts do not advance stages.
STAGE_COMPLETION_CONFIDENCE_THRESHOLD: float = 0.75


@dataclass(frozen=True)
class StageCompletionVerdict:
    """Structured verdict on whether a given stage (1..4) is complete.

    `stage_id` is the stage the judge graded; the use case must pass in the
    active agent id of the turn that triggered the judge, and the adapter
    echoes it back here.

    `confidence` is in 0.0..1.0. Callers must also check it against
    `STAGE_COMPLETION_CONFIDENCE_THRESHOLD` before flipping a flag from False
    to True — that check lives in `merge_stage_completion_verdict_into_flags`.

    When an adapter cannot produce a real verdict (API error, empty response,
    unparseable JSON), it must return a verdict with `stage_complete=False`,
    `confidence=0.0`, and `reason` prefixed `"judge_error: "` so the use case
    can route to its heuristic fallback.
    """

    stage_id: int
    stage_complete: bool
    confidence: float
    reason: str
    evidence_found: tuple[str, ...] = field(default_factory=tuple)
    missing_topics: tuple[str, ...] = field(default_factory=tuple)
