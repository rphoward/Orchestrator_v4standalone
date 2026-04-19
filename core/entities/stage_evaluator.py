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
