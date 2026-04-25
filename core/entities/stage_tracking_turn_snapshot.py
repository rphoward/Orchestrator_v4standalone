"""Per-turn observability for stage tracking (no I/O). JSON append + cap for session column."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from orchestrator_v4.core.entities.stage_progress import (
    StageProgress,
    StageTrackingMode,
)

STAGE_TRACKING_LOG_MAX = 32

StageTrackingTurnEndpoint = Literal["auto", "manual"]

JudgeApplicationOutcome = Literal["none", "verdict", "judge_error_heuristic", "exception_heuristic"]


@dataclass(frozen=True)
class StageTrackingVerdictView:
    """Verdict fields safe to echo to API after a real judge return (before flag merge)."""

    stage_id: int
    stage_complete: bool
    confidence: float
    reason: str


@dataclass(frozen=True)
class StageTrackingTurnSnapshot:
    """One turn's stage tracking decision for review (chat turns, not export refresh)."""

    turn_endpoint: StageTrackingTurnEndpoint
    stage_tracking_mode: StageTrackingMode
    routed_stage_id: int
    active_stage_pointer_before: int
    active_stage_pointer_after: int
    progress_json_updated: bool
    evaluated_progress: dict[str, object]
    gate_reason: str
    judge_ran: bool
    judge_outcome: JudgeApplicationOutcome
    verdict: StageTrackingVerdictView | None
    stage_flags_before: dict[int, bool] = field(
        default_factory=lambda: {1: False, 2: False, 3: False, 4: False}
    )
    stage_flags_after: dict[int, bool] = field(
        default_factory=lambda: {1: False, 2: False, 3: False, 4: False}
    )

    def to_public_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "turn_endpoint": self.turn_endpoint,
            "stage_tracking_mode": self.stage_tracking_mode,
            "routed_stage_id": self.routed_stage_id,
            "active_stage_pointer_before": self.active_stage_pointer_before,
            "active_stage_pointer_after": self.active_stage_pointer_after,
            "progress_json_updated": self.progress_json_updated,
            "evaluated_progress": dict(self.evaluated_progress),
            "gate_reason": self.gate_reason,
            "judge_ran": self.judge_ran,
            "judge_outcome": self.judge_outcome,
            "stage_flags_before": {str(k): v for k, v in self.stage_flags_before.items()},
            "stage_flags_after": {str(k): v for k, v in self.stage_flags_after.items()},
            "flags_changed": _flags_changed(
                self.stage_flags_before, self.stage_flags_after
            ),
        }
        d["verdict"] = asdict(self.verdict) if self.verdict is not None else None
        return d


def _flags_changed(before: Mapping[int, bool], after: Mapping[int, bool]) -> bool:
    for k in (1, 2, 3, 4):
        if bool(before.get(k)) != bool(after.get(k)):
            return True
    return False


def compact_evaluated_progress(progress: StageProgress) -> dict[str, object]:
    return {
        "user_message_count": progress.user_message_count,
        "meaningful_evidence_count": progress.meaningful_evidence_count,
        "turns_since_judge": progress.turns_since_judge,
        "candidate_complete": progress.candidate_complete,
        "summary": "candidate_complete" if progress.candidate_complete else "in_progress",
    }


def append_capped_stage_tracking_log(
    existing_json: str | None,
    entry: dict[str, Any],
) -> str:
    """Append one snapshot dict to a JSON array; cap at STAGE_TRACKING_LOG_MAX entries."""

    prior: list[dict[str, Any]] = []
    if existing_json and existing_json.strip():
        try:
            decoded = json.loads(existing_json)
        except (TypeError, ValueError):
            pass
        else:
            if isinstance(decoded, list):
                prior = [x for x in decoded if isinstance(x, dict)]
    prior.append(entry)
    if len(prior) > STAGE_TRACKING_LOG_MAX:
        prior = prior[-STAGE_TRACKING_LOG_MAX:]
    return json.dumps(prior, separators=(",", ":"))
