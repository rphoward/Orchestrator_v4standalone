"""Pure stage gating and completion heuristics (ported from v3 StageEvaluator).

`session.current_agent_id` means the **active stage pointer**: the earliest
unfinished stage in 1..4, recomputed from the four `stageN_complete` flags
after every turn (auto or manual). When all four flags are true the pointer
stays at 4; agent 5 (Grand Synthesis) is the manual-only synthesizer and is
never the pointer.

Auto-routing may target any agent from 1 up to the pointer (so the router can
drift back to a finished stage when the consultant won't let go), but never
past the pointer. Manual routing can target any agent 1..5.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from orchestrator_v4.core.entities.interview_turn import RoutingDecision, TurnConversationLine
from orchestrator_v4.core.entities.stage_completion_verdict import (
    STAGE_COMPLETION_CONFIDENCE_THRESHOLD,
    StageCompletionVerdict,
)


def earliest_unfinished_stage(stage_flags: Mapping[int, bool]) -> int:
    """
    Earliest stage id in 1..4 whose completion flag is falsy.

    When all four are truthy, returns 4 (the pointer does not cross into the
    synthesizer; agent 5 is manual-only).
    """
    for stage_id in (1, 2, 3, 4):
        if not stage_flags.get(stage_id, False):
            return stage_id
    return 4


def apply_sequential_stage_veto(
    routing_decision: RoutingDecision,
    stage_flags: Mapping[int, bool],
) -> RoutingDecision:
    """
    Clamp an auto-routing decision so it can never jump past the active stage pointer.

    Allowed: any target from 1 up to and including the pointer (back-drift to a
    finished stage is fine; the router may want to follow the consultant there).

    Forbidden: any target higher than the pointer. The decision is rewritten to
    `STAY` on the pointer with a reason that preserves the router's original
    intent for audit in `routing_logs`.
    """
    pointer = earliest_unfinished_stage(stage_flags)
    target = routing_decision.target_agent_id
    if target <= pointer:
        return routing_decision

    return RoutingDecision(
        target_agent_id=pointer,
        workflow_status="STAY",
        reason=(
            f"Sequential stage veto: router wanted agent {target} "
            f"(status={routing_decision.workflow_status}), "
            f"forced to stage {pointer} (next unfinished)"
        ),
    )


def evaluate_stage_completion(
    active_agent_id: int,
    messages: Sequence[TurnConversationLine],
    prior_flags: Mapping[int, bool],
) -> dict[int, bool]:
    """
    User chat message count heuristic per stage (>= 2 user messages for active agent).
    Returns updated flags for stages 1–4 merged with prior_flags.

    Kept as the offline / fallback decision when the `InterviewStageCompletionJudge`
    port returns a ``judge_error:`` verdict or raises. Replaced in the happy path
    by ``merge_stage_completion_verdict_into_flags``.
    """
    flags = {k: bool(prior_flags.get(k, False)) for k in (1, 2, 3, 4)}
    user_msgs = sum(
        1
        for m in messages
        if m.agent_id == active_agent_id
        and m.role == "user"
        and m.message_type == "chat"
    )
    if user_msgs >= 2:
        if active_agent_id == 1:
            flags[1] = True
        elif active_agent_id == 2:
            flags[2] = True
        elif active_agent_id == 3:
            flags[3] = True
        elif active_agent_id == 4:
            flags[4] = True
    return flags


def merge_stage_completion_verdict_into_flags(
    verdict: StageCompletionVerdict,
    prior_flags: Mapping[int, bool],
) -> dict[int, bool]:
    """Flip a single stage flag True iff the verdict passes all guardrails.

    This is the junk-defense boundary for the ``InterviewStageCompletionJudge``
    port. Trust nothing about ``verdict`` beyond its type; validate every field
    here so a later coder cannot widen the rule by mistake.

    Rules (all must hold to flip a flag):
    - ``verdict.stage_id`` is in the set ``{1, 2, 3, 4}``. Any other stage_id
      (5 = synthesizer, 0, negatives, malformed) returns a copy of
      ``prior_flags`` with no changes.
    - ``verdict.stage_complete is True``.
    - ``verdict.confidence >= STAGE_COMPLETION_CONFIDENCE_THRESHOLD``.
    - the flag at ``verdict.stage_id`` is currently False. True -> False is
      never allowed; back-drift is the router's job, not the tracker's.

    Returns a new dict with the four stage keys 1..4 (all pulled from
    ``prior_flags``), never mutates ``prior_flags``.
    """
    flags = {k: bool(prior_flags.get(k, False)) for k in (1, 2, 3, 4)}

    stage_id = verdict.stage_id
    if stage_id not in (1, 2, 3, 4):
        return flags
    if not verdict.stage_complete:
        return flags
    if verdict.confidence < STAGE_COMPLETION_CONFIDENCE_THRESHOLD:
        return flags
    if flags[stage_id]:
        return flags

    flags[stage_id] = True
    return flags
