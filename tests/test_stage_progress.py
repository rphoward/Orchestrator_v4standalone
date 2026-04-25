"""Pure stage tracking settings and gate tests."""

from orchestrator_v4.core.entities.interview_turn import TurnConversationLine
from orchestrator_v4.core.entities.stage_progress import (
    StageTrackingSettings,
    advance_stage_progress_json,
    is_meaningful_stage_evidence,
    is_short_or_test_like_stage_input,
    normalize_stage_tracking_settings,
    read_stage_progress,
    should_run_stage_tracking_judge,
)


def _msg(agent_id: int, text: str) -> TurnConversationLine:
    return TurnConversationLine(
        agent_id=agent_id,
        role="user",
        content=text,
        message_type="chat",
        timestamp="",
    )


def test_stage_tracking_settings_defaults() -> None:
    settings = normalize_stage_tracking_settings(None, None)
    assert settings == StageTrackingSettings(mode="hybrid", judge_interval=4)


def test_stage_tracking_settings_invalid_values_fall_back() -> None:
    settings = normalize_stage_tracking_settings("nonsense", "bad")
    assert settings == StageTrackingSettings(mode="hybrid", judge_interval=4)


def test_short_or_test_like_input_is_not_meaningful_evidence() -> None:
    assert is_short_or_test_like_stage_input("test")
    assert is_short_or_test_like_stage_input("ok")
    assert not is_meaningful_stage_evidence("test")


def test_meaningful_stage_evidence_is_counted() -> None:
    text = "The strongest buyer evidence is repeated founder-led onboarding pain."
    assert not is_short_or_test_like_stage_input(text)
    assert is_meaningful_stage_evidence(text)


def test_stage_progress_marks_candidate_complete_without_flipping_flags() -> None:
    messages = (
        _msg(1, "The brand promise is fast, plain English planning for founders."),
        _msg(1, "The proof is that teams keep using it after failed agencies."),
    )
    serialized, progress = advance_stage_progress_json("", 1, messages, messages[-1].content)
    assert progress.user_message_count == 2
    assert progress.meaningful_evidence_count == 2
    assert progress.candidate_complete is True
    assert read_stage_progress(serialized, 1).candidate_complete is True


def test_hybrid_interval_expiry_runs_after_hard_gates_pass() -> None:
    messages = (
        _msg(2, "The founder will not accept vague claims without source notes."),
        _msg(2, "The invariant is that every recommendation must trace to transcript evidence."),
        _msg(2, "The product must keep manual control because review happens live."),
        _msg(2, "The team wants stage movement to be earned by the same transcript."),
    )
    serialized = ""
    for message in messages:
        serialized, progress = advance_stage_progress_json(
            serialized, 2, messages, message.content
        )
    decision = should_run_stage_tracking_judge(
        StageTrackingSettings(mode="hybrid", judge_interval=4),
        2,
        messages,
        messages[-1].content,
        progress,
        trigger="turn",
    )
    assert decision.run_judge is True
    assert decision.reason == "candidate_complete"


def test_explicit_stage_change_is_not_treated_as_test_like() -> None:
    assert not is_short_or_test_like_stage_input("next stage")
    messages = (
        _msg(1, "The brand promise is fast, plain English planning for founders."),
        _msg(1, "The proof is that teams keep using it after failed agencies."),
    )
    serialized, progress = advance_stage_progress_json("", 1, messages, "next stage")
    decision = should_run_stage_tracking_judge(
        StageTrackingSettings(mode="hybrid", judge_interval=4),
        1,
        messages,
        "next stage",
        progress,
        trigger="turn",
    )
    assert decision.run_judge is True


def test_semantic_mode_runs_for_eligible_agent_and_off_mode_does_not() -> None:
    messages = (_msg(3, "ok"),)
    progress = read_stage_progress("", 3)
    semantic = should_run_stage_tracking_judge(
        StageTrackingSettings(mode="semantic", judge_interval=4),
        3,
        messages,
        "ok",
        progress,
        trigger="turn",
    )
    off = should_run_stage_tracking_judge(
        StageTrackingSettings(mode="off", judge_interval=4),
        3,
        messages,
        "ok",
        progress,
        trigger="turn",
    )
    assert semantic.run_judge is True
    assert off.run_judge is False


def test_agent_five_is_ignored_by_stage_tracking_gate() -> None:
    messages = (
        _msg(5, "Please synthesize the final architecture from the session."),
        _msg(5, "Include the major decisions and risks in the report."),
    )
    progress = read_stage_progress("", 5)
    decision = should_run_stage_tracking_judge(
        StageTrackingSettings(mode="hybrid", judge_interval=4),
        5,
        messages,
        messages[-1].content,
        progress,
        trigger="turn",
    )
    assert decision.run_judge is False
