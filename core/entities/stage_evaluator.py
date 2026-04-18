"""Pure stage gating and completion heuristics (ported from v3 StageEvaluator)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from orchestrator_v4.core.entities.interview_turn import RoutingDecision, TurnConversationLine


def can_advance(
    current_agent_id: int,
    stage_flags: Mapping[int, bool],
    target_stage_id: int,
) -> bool:
    """
    Whether routing may move forward to target_stage_id.
    Same rules as v3: can always stay or go back; forward moves need prior stage complete.
    """
    if target_stage_id <= current_agent_id:
        return True

    if target_stage_id == 2 and stage_flags.get(1, False):
        return True
    if target_stage_id == 3 and stage_flags.get(2, False):
        return True
    if target_stage_id == 4 and stage_flags.get(3, False):
        return True

    return False


def apply_routing_veto(
    routing_decision: RoutingDecision,
    current_agent_id: int,
    stage_flags: Mapping[int, bool],
) -> RoutingDecision:
    """If router says ADVANCE but domain disallows, force STAY on current agent."""
    if routing_decision.workflow_status != "ADVANCE":
        return routing_decision

    if can_advance(current_agent_id, stage_flags, routing_decision.target_agent_id):
        return routing_decision

    return RoutingDecision(
        target_agent_id=current_agent_id,
        workflow_status="STAY",
        reason=routing_decision.reason,
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
