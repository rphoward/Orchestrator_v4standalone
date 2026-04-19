"""Core entity smoke tests — no Flask, DB, or network."""

from orchestrator_v4.core.entities.interview_turn import (
    RoutingDecision,
    TurnContext,
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
