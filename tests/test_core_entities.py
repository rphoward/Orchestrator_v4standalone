"""Core entity smoke tests — no Flask, DB, or network."""

from orchestrator_v4.core.entities.interview_turn import (
    RoutingDecision,
    TurnContext,
)
from orchestrator_v4.core.entities.stage_evaluator import (
    apply_sequential_stage_veto,
    earliest_unfinished_stage,
)


def test_turn_context_stage_flags() -> None:
    ctx = TurnContext(
        session_id=1,
        name="t",
        current_agent_id=1,
        stage1_complete=True,
        stage2_complete=False,
        stage3_complete=True,
        stage4_complete=False,
        messages=(),
        routing_logs=(),
        agents=(),
    )
    assert ctx.stage_flags() == {1: True, 2: False, 3: True, 4: False}


def test_routing_decision_immutable() -> None:
    r = RoutingDecision(target_agent_id=3, workflow_status="ok", reason="test")
    assert r.target_agent_id == 3
    assert r.workflow_status == "ok"


# ── Active stage pointer ─────────────────────────────────────────


def test_earliest_unfinished_stage_none_done() -> None:
    assert earliest_unfinished_stage({}) == 1
    assert earliest_unfinished_stage(
        {1: False, 2: False, 3: False, 4: False}
    ) == 1


def test_earliest_unfinished_stage_first_done() -> None:
    assert earliest_unfinished_stage({1: True}) == 2


def test_earliest_unfinished_stage_first_two_done() -> None:
    assert earliest_unfinished_stage({1: True, 2: True}) == 3


def test_earliest_unfinished_stage_three_done() -> None:
    assert earliest_unfinished_stage({1: True, 2: True, 3: True}) == 4


def test_earliest_unfinished_stage_all_done_stays_at_four() -> None:
    assert earliest_unfinished_stage(
        {1: True, 2: True, 3: True, 4: True}
    ) == 4


def test_earliest_unfinished_stage_non_monotonic_returns_earliest_gap() -> None:
    # Flags can be flipped out of order if a consultant manually drives an
    # advanced stage early; the pointer still points at the earliest gap.
    assert earliest_unfinished_stage({1: True, 3: True}) == 2


# ── Sequential stage veto ────────────────────────────────────────


def test_sequential_stage_veto_allows_pointer_target() -> None:
    decision = RoutingDecision(
        target_agent_id=1, workflow_status="STAY", reason="Routed by AI"
    )
    clamped = apply_sequential_stage_veto(decision, {})
    assert clamped is decision  # unchanged


def test_sequential_stage_veto_allows_back_drift_to_finished_stage() -> None:
    # pointer = 2 (stage 1 done, stage 2 not), router wants to drift back to agent 1
    decision = RoutingDecision(
        target_agent_id=1, workflow_status="DRIFT", reason="User still on brand"
    )
    clamped = apply_sequential_stage_veto(decision, {1: True})
    assert clamped is decision


def test_sequential_stage_veto_blocks_forward_jump_over_unfinished_stage() -> None:
    # pointer = 1 (nothing done), router wants agent 3
    decision = RoutingDecision(
        target_agent_id=3, workflow_status="STAY", reason="Customer talk"
    )
    clamped = apply_sequential_stage_veto(decision, {})
    assert clamped.target_agent_id == 1
    assert clamped.workflow_status == "STAY"
    assert "forced to stage 1" in clamped.reason
    assert "router wanted agent 3" in clamped.reason


def test_sequential_stage_veto_blocks_advance_past_pointer() -> None:
    # pointer = 2, router wants ADVANCE to agent 4
    decision = RoutingDecision(
        target_agent_id=4, workflow_status="ADVANCE", reason="Done with stage 2"
    )
    clamped = apply_sequential_stage_veto(decision, {1: True})
    assert clamped.target_agent_id == 2
    assert clamped.workflow_status == "STAY"
    assert "forced to stage 2" in clamped.reason
