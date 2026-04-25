"""Pure stage tracking settings, compact progress JSON, and judge gate rules."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from orchestrator_v4.core.entities.interview_turn import TurnConversationLine

STAGE_TRACKING_MODES = ("off", "hybrid", "semantic")
DEFAULT_STAGE_TRACKING_MODE = "hybrid"
DEFAULT_STAGE_TRACKING_JUDGE_INTERVAL = 4
ELIGIBLE_STAGE_IDS = (1, 2, 3, 4)

StageTrackingMode = Literal["off", "hybrid", "semantic"]
StageTrackingTrigger = Literal["turn", "final_report", "export"]

_TEST_LIKE_INPUTS = {
    "test",
    "testing",
    "ping",
    "pong",
    "hi",
    "hello",
    "hey",
    "ok",
    "okay",
    "k",
    "yes",
    "no",
    "sure",
}
_ADVANCE_RE = re.compile(
    r"\b(next stage|move on|advance|stage change|change stage|switch stage|"
    r"go to stage|continue to the next|final report|export)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class StageTrackingSettings:
    """Sanitized stage tracking settings read from config."""

    mode: StageTrackingMode = DEFAULT_STAGE_TRACKING_MODE
    judge_interval: int = DEFAULT_STAGE_TRACKING_JUDGE_INTERVAL


@dataclass(frozen=True)
class StageProgress:
    """Compact per-stage counters stored inside ``sessions.stage_progress`` JSON."""

    user_message_count: int = 0
    meaningful_evidence_count: int = 0
    turns_since_judge: int = 0
    candidate_complete: bool = False


@dataclass(frozen=True)
class StageTrackingJudgeDecision:
    """Gate result for deciding whether to call the semantic stage judge."""

    run_judge: bool
    reason: str


def normalize_stage_tracking_settings(
    mode: object | None,
    judge_interval: object | None,
) -> StageTrackingSettings:
    raw_mode = str(mode or DEFAULT_STAGE_TRACKING_MODE).strip().lower()
    if raw_mode not in STAGE_TRACKING_MODES:
        raw_mode = DEFAULT_STAGE_TRACKING_MODE

    try:
        interval = int(judge_interval) if judge_interval is not None else DEFAULT_STAGE_TRACKING_JUDGE_INTERVAL
    except (TypeError, ValueError):
        interval = DEFAULT_STAGE_TRACKING_JUDGE_INTERVAL
    if interval < 1:
        interval = 1

    return StageTrackingSettings(mode=raw_mode, judge_interval=interval)  # type: ignore[arg-type]


def is_stage_tracking_eligible_agent(agent_id: int) -> bool:
    return agent_id in ELIGIBLE_STAGE_IDS


def is_short_or_test_like_stage_input(text: str) -> bool:
    cleaned = " ".join((text or "").strip().lower().split())
    if not cleaned:
        return True
    if explicitly_requests_stage_change(cleaned):
        return False
    if cleaned in _TEST_LIKE_INPUTS:
        return True
    words = re.findall(r"[a-z0-9']+", cleaned)
    if len(words) <= 2 and len(cleaned) <= 18:
        return True
    return False


def is_meaningful_stage_evidence(text: str) -> bool:
    cleaned = " ".join((text or "").strip().split())
    if is_short_or_test_like_stage_input(cleaned):
        return False
    words = re.findall(r"[A-Za-z0-9']+", cleaned)
    return len(words) >= 6 and len(cleaned) >= 28


def explicitly_requests_stage_change(text: str) -> bool:
    return bool(_ADVANCE_RE.search(text or ""))


def stage_user_messages(
    stage_id: int,
    messages: Sequence[TurnConversationLine],
) -> tuple[TurnConversationLine, ...]:
    return tuple(
        m
        for m in messages
        if m.agent_id == stage_id and m.role == "user" and m.message_type == "chat"
    )


def read_stage_progress(serialized_stage_progress: str | None, stage_id: int) -> StageProgress:
    data = _load_progress_data(serialized_stage_progress)
    raw = data.get(str(stage_id), {})
    if not isinstance(raw, Mapping):
        return StageProgress()
    return _stage_progress_from_mapping(raw)


def advance_stage_progress_json(
    serialized_stage_progress: str | None,
    stage_id: int,
    messages: Sequence[TurnConversationLine],
    current_user_input: str,
) -> tuple[str, StageProgress]:
    """Update only ``stage_id`` counters after an eligible user turn."""

    if not is_stage_tracking_eligible_agent(stage_id):
        return serialized_stage_progress or "", StageProgress()

    data = _load_progress_data(serialized_stage_progress)
    prior = read_stage_progress(serialized_stage_progress, stage_id)
    updated = _progress_from_messages(
        stage_id,
        messages,
        turns_since_judge=prior.turns_since_judge + 1,
    )
    data[str(stage_id)] = _stage_progress_to_mapping(updated)
    return _dump_progress_data(data), updated


def record_stage_judge_attempt_json(
    serialized_stage_progress: str | None,
    stage_id: int,
    messages: Sequence[TurnConversationLine],
) -> str:
    if not is_stage_tracking_eligible_agent(stage_id):
        return serialized_stage_progress or ""
    data = _load_progress_data(serialized_stage_progress)
    updated = _progress_from_messages(stage_id, messages, turns_since_judge=0)
    data[str(stage_id)] = _stage_progress_to_mapping(updated)
    return _dump_progress_data(data)


def should_run_stage_tracking_judge(
    settings: StageTrackingSettings,
    stage_id: int,
    messages: Sequence[TurnConversationLine],
    current_user_input: str,
    progress: StageProgress,
    *,
    trigger: StageTrackingTrigger,
) -> StageTrackingJudgeDecision:
    if not is_stage_tracking_eligible_agent(stage_id):
        return StageTrackingJudgeDecision(False, "ineligible_agent")

    normalized = normalize_stage_tracking_settings(settings.mode, settings.judge_interval)
    if normalized.mode == "off":
        return StageTrackingJudgeDecision(False, "off")
    if normalized.mode == "semantic":
        return StageTrackingJudgeDecision(True, "semantic_mode")

    user_messages = stage_user_messages(stage_id, messages)
    if trigger == "turn" and is_short_or_test_like_stage_input(current_user_input):
        return StageTrackingJudgeDecision(False, "short_or_test_like")
    if len(user_messages) < 2:
        return StageTrackingJudgeDecision(False, "fewer_than_two_user_messages")
    if not _has_meaningful_evidence(user_messages, progress):
        return StageTrackingJudgeDecision(False, "no_meaningful_evidence")

    if trigger in ("final_report", "export"):
        return StageTrackingJudgeDecision(True, trigger)
    if explicitly_requests_stage_change(current_user_input):
        return StageTrackingJudgeDecision(True, "explicit_stage_change")
    if progress.candidate_complete:
        return StageTrackingJudgeDecision(True, "candidate_complete")
    if progress.turns_since_judge >= normalized.judge_interval:
        return StageTrackingJudgeDecision(True, "interval_expired")
    return StageTrackingJudgeDecision(False, "waiting")


def _progress_from_messages(
    stage_id: int,
    messages: Sequence[TurnConversationLine],
    *,
    turns_since_judge: int,
) -> StageProgress:
    user_messages = stage_user_messages(stage_id, messages)
    meaningful_count = sum(
        1 for message in user_messages if is_meaningful_stage_evidence(message.content)
    )
    user_count = len(user_messages)
    return StageProgress(
        user_message_count=user_count,
        meaningful_evidence_count=meaningful_count,
        turns_since_judge=max(0, turns_since_judge),
        candidate_complete=user_count >= 2 and meaningful_count >= 2,
    )


def _has_meaningful_evidence(
    user_messages: Sequence[TurnConversationLine],
    progress: StageProgress,
) -> bool:
    if progress.meaningful_evidence_count > 0:
        return True
    return any(is_meaningful_stage_evidence(message.content) for message in user_messages)


def _load_progress_data(serialized_stage_progress: str | None) -> dict[str, dict[str, object]]:
    if not serialized_stage_progress:
        return {}
    try:
        decoded = json.loads(serialized_stage_progress)
    except (TypeError, ValueError):
        return {}
    if not isinstance(decoded, Mapping):
        return {}
    if isinstance(decoded.get("stages"), Mapping):
        decoded = decoded["stages"]  # type: ignore[assignment]

    data: dict[str, dict[str, object]] = {}
    for stage_id, raw in decoded.items():
        if str(stage_id) not in {"1", "2", "3", "4"} or not isinstance(raw, Mapping):
            continue
        data[str(stage_id)] = dict(raw)
    return data


def _dump_progress_data(data: Mapping[str, Mapping[str, object]]) -> str:
    compact = {
        str(stage_id): dict(values)
        for stage_id, values in data.items()
        if str(stage_id) in {"1", "2", "3", "4"}
    }
    return json.dumps(compact, sort_keys=True, separators=(",", ":"))


def _stage_progress_from_mapping(raw: Mapping[str, object]) -> StageProgress:
    return StageProgress(
        user_message_count=_int_from_mapping(raw, "u", "user_message_count"),
        meaningful_evidence_count=_int_from_mapping(raw, "e", "meaningful_evidence_count"),
        turns_since_judge=_int_from_mapping(raw, "t", "turns_since_judge"),
        candidate_complete=_bool_from_mapping(raw, "c", "candidate_complete"),
    )


def _stage_progress_to_mapping(progress: StageProgress) -> dict[str, object]:
    return {
        "u": progress.user_message_count,
        "e": progress.meaningful_evidence_count,
        "t": progress.turns_since_judge,
        "c": progress.candidate_complete,
    }


def _int_from_mapping(raw: Mapping[str, object], compact_key: str, long_key: str) -> int:
    value = raw.get(compact_key, raw.get(long_key, 0))
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _bool_from_mapping(raw: Mapping[str, object], compact_key: str, long_key: str) -> bool:
    value = raw.get(compact_key, raw.get(long_key, False))
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
