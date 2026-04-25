"""Use-case tests for backend stage tracking modes."""

import json
from collections.abc import Mapping, Sequence

from orchestrator_v4.core.entities.interview_turn import (
    ConversationAppend,
    InterviewTurnAgentRosterEntry,
    RoutingDecision,
    RoutingLogAppend,
    TurnContext,
    TurnConversationLine,
)
from orchestrator_v4.core.entities.interview_session_read_bundle import (
    InterviewSessionReadBundle,
    InterviewSessionReadHeadline,
)
from orchestrator_v4.core.entities.stage_completion_verdict import StageCompletionVerdict
from orchestrator_v4.core.entities.stage_progress import StageTrackingSettings, read_stage_progress
from orchestrator_v4.core.use_cases.conduct_interview_turn import ConductInterviewTurn
from orchestrator_v4.core.use_cases.conduct_manual_interview_turn import (
    ConductManualInterviewTurn,
)
from orchestrator_v4.core.use_cases.load_interview_session_for_export import (
    LoadInterviewSessionForExport,
)
from orchestrator_v4.core.use_cases.read_session_stage_tracking_log import (
    ReadSessionStageTrackingLog,
)
from orchestrator_v4.core.use_cases.refresh_stage_tracking_before_report import (
    RefreshStageTrackingBeforeReport,
)


def _agents() -> tuple[InterviewTurnAgentRosterEntry, ...]:
    return tuple(
        InterviewTurnAgentRosterEntry(
            id=agent_id,
            name=f"Agent {agent_id}",
            system_prompt="prompt",
            router_hint=f"hint {agent_id}",
            is_synthesizer=(agent_id == 5),
        )
        for agent_id in range(1, 6)
    )


def _line(agent_id: int, role: str, content: str) -> TurnConversationLine:
    return TurnConversationLine(
        agent_id=agent_id,
        role=role,
        content=content,
        message_type="chat",
        timestamp="",
    )


class FakeStageTrackingSettingsStore:
    def __init__(self, settings: StageTrackingSettings) -> None:
        self.settings = settings

    def read(self) -> StageTrackingSettings:
        return self.settings

    def save(self, settings: StageTrackingSettings) -> StageTrackingSettings:
        self.settings = settings
        return settings


class InMemoryTurnStore:
    def __init__(
        self,
        *,
        messages: tuple[TurnConversationLine, ...] = (),
        current_agent_id: int = 1,
        stage_progress_json: str = "",
        stage_tracking_log_json: str = "[]",
    ) -> None:
        self.messages = list(messages)
        self.current_agent_id = current_agent_id
        self.stage_flags = {1: False, 2: False, 3: False, 4: False}
        self.stage_progress_json = stage_progress_json
        self.stage_tracking_log_json = stage_tracking_log_json
        self.routing_logs: list[RoutingLogAppend] = []

    def load_turn_context(self, session_id: int) -> TurnContext:
        return TurnContext(
            session_id=session_id,
            name="New Session",
            current_agent_id=self.current_agent_id,
            stage1_complete=self.stage_flags[1],
            stage2_complete=self.stage_flags[2],
            stage3_complete=self.stage_flags[3],
            stage4_complete=self.stage_flags[4],
            stage_progress_json=self.stage_progress_json,
            stage_tracking_log_json=self.stage_tracking_log_json,
            messages=tuple(self.messages),
            routing_logs=(),
            agents=_agents(),
        )

    def append_messages(
        self, session_id: int, messages: Sequence[ConversationAppend]
    ) -> None:
        for message in messages:
            self.messages.append(
                _line(message.agent_id, message.role, message.content)
            )

    def append_routing_log(self, session_id: int, log: RoutingLogAppend) -> None:
        self.routing_logs.append(log)

    def update_session_state(
        self,
        session_id: int,
        *,
        current_agent_id: int | None = None,
        stage_flags: dict[int, bool] | None = None,
        name: str | None = None,
        stage_progress_json: str | None = None,
        stage_tracking_log_json: str | None = None,
    ) -> None:
        if current_agent_id is not None:
            self.current_agent_id = current_agent_id
        if stage_flags is not None:
            self.stage_flags.update(stage_flags)
        if stage_progress_json is not None:
            self.stage_progress_json = stage_progress_json
        if stage_tracking_log_json is not None:
            self.stage_tracking_log_json = stage_tracking_log_json


class FakeLlmGateway:
    def __init__(self, target_agent_id: int = 1) -> None:
        self.target_agent_id = target_agent_id

    def route_intent(
        self,
        user_input: str,
        current_agent_id: int,
        agent_hints: dict[int, str],
    ) -> RoutingDecision:
        return RoutingDecision(
            target_agent_id=self.target_agent_id,
            workflow_status="STAY",
            reason="fake route",
        )

    def get_response(
        self,
        user_input: str,
        agent_id: int,
        system_prompt: str,
        model: str,
        thinking_level: str,
        temperature: str,
        include_thoughts: bool,
        history: Sequence[ConversationAppend],
        cross_context: Sequence[ConversationAppend],
        psychological_phase: str,
    ) -> str:
        return f"reply from {agent_id}"


class RecordingJudge:
    def __init__(self, *, complete: bool = False, confidence: float = 0.0) -> None:
        self.complete = complete
        self.confidence = confidence
        self.calls: list[int] = []

    def judge_stage_completion(
        self,
        stage_id: int,
        messages: Sequence[TurnConversationLine],
        stage_flags_before: Mapping[int, bool],
    ) -> StageCompletionVerdict:
        self.calls.append(stage_id)
        return StageCompletionVerdict(
            stage_id=stage_id,
            stage_complete=self.complete,
            confidence=self.confidence,
            reason="recorded",
        )


def test_auto_hybrid_early_turn_skips_judge() -> None:
    store = InMemoryTurnStore()
    judge = RecordingJudge(complete=True, confidence=1.0)
    use_case = ConductInterviewTurn(
        store,
        FakeLlmGateway(target_agent_id=1),
        judge,
        FakeStageTrackingSettingsStore(StageTrackingSettings("hybrid", 4)),
    )

    result = use_case.execute(1, "The first useful brand note is mostly about trust.")

    assert judge.calls == []
    assert read_stage_progress(store.stage_progress_json, 1).user_message_count == 1
    assert store.stage_flags[1] is False
    assert result.stage_tracking.get("turn_endpoint") == "auto"
    assert result.stage_tracking.get("judge_ran") is False
    assert result.stage_tracking.get("gate_reason") in (
        "fewer_than_two_user_messages",
        "no_meaningful_evidence",
    )
    assert "evaluated_progress" in result.stage_tracking


def test_manual_hybrid_turn_writes_progress_for_selected_agent() -> None:
    store = InMemoryTurnStore()
    judge = RecordingJudge()
    use_case = ConductManualInterviewTurn(
        store,
        FakeLlmGateway(),
        judge,
        FakeStageTrackingSettingsStore(StageTrackingSettings("hybrid", 4)),
    )

    r = use_case.execute(1, 2, "The founder keeps insisting that specificity matters.")

    assert judge.calls == []
    assert read_stage_progress(store.stage_progress_json, 2).user_message_count == 1
    assert r.stage_tracking.get("turn_endpoint") == "manual"
    assert r.stage_tracking.get("progress_json_updated") is True


def test_semantic_mode_calls_judge_for_eligible_turn() -> None:
    store = InMemoryTurnStore()
    store.stage_flags = {1: True, 2: True, 3: False, 4: False}
    judge = RecordingJudge()
    use_case = ConductInterviewTurn(
        store,
        FakeLlmGateway(target_agent_id=3),
        judge,
        FakeStageTrackingSettingsStore(StageTrackingSettings("semantic", 4)),
    )

    r = use_case.execute(1, "ok")

    assert judge.calls == [3]
    assert r.stage_tracking.get("gate_reason") == "semantic_mode"
    assert r.stage_tracking.get("judge_ran") is True
    assert r.stage_tracking.get("judge_outcome") == "verdict"


def test_manual_agent_five_skips_judge_progress_and_flags() -> None:
    store = InMemoryTurnStore()
    store.stage_flags = {1: True, 2: False, 3: False, 4: False}
    judge = RecordingJudge(complete=True, confidence=1.0)
    use_case = ConductManualInterviewTurn(
        store,
        FakeLlmGateway(),
        judge,
        FakeStageTrackingSettingsStore(StageTrackingSettings("hybrid", 4)),
    )

    r = use_case.execute(1, 5, "Please synthesize what we have so far.")

    assert judge.calls == []
    assert store.stage_progress_json == ""
    assert store.stage_flags == {1: True, 2: False, 3: False, 4: False}
    assert r.stage_tracking.get("gate_reason") == "ineligible_agent"
    assert r.stage_tracking.get("judge_ran") is False
    assert r.stage_tracking.get("flags_changed") is False


def test_compact_progress_alone_cannot_mark_stage_complete() -> None:
    store = InMemoryTurnStore(
        messages=(
            _line(1, "user", "The brand promise is plain-spoken planning for founders."),
            _line(1, "assistant", "Noted."),
        )
    )
    judge = RecordingJudge(complete=False, confidence=0.0)
    use_case = ConductInterviewTurn(
        store,
        FakeLlmGateway(target_agent_id=1),
        judge,
        FakeStageTrackingSettingsStore(StageTrackingSettings("hybrid", 4)),
    )

    r2 = use_case.execute(1, "The second evidence point is that teams return after failed agency work.")

    assert judge.calls == [1]
    assert read_stage_progress(store.stage_progress_json, 1).candidate_complete is True
    assert store.stage_flags[1] is False
    assert r2.stage_tracking.get("evaluated_progress", {}).get("summary") == "candidate_complete"
    assert r2.stage_tracking.get("flags_changed") is False


def test_final_report_refresh_calls_judge_only_when_gate_says_yes() -> None:
    store = InMemoryTurnStore(
        messages=(
            _line(1, "user", "The brand promise is plain-spoken planning for founders."),
            _line(1, "assistant", "Noted."),
            _line(1, "user", "The proof is that teams return after failed agency work."),
            _line(2, "user", "Only one founder invariant so far."),
        )
    )
    judge = RecordingJudge(complete=True, confidence=1.0)
    use_case = RefreshStageTrackingBeforeReport(
        store,
        judge,
        FakeStageTrackingSettingsStore(StageTrackingSettings("hybrid", 4)),
    )

    use_case.execute(1, trigger="final_report")

    assert judge.calls == [1]
    assert store.stage_flags[1] is True
    assert store.stage_flags[2] is False


def test_off_mode_auto_turn_skips_judge_and_leaves_progress_empty() -> None:
    store = InMemoryTurnStore()
    judge = RecordingJudge(complete=True, confidence=1.0)
    use_case = ConductInterviewTurn(
        store,
        FakeLlmGateway(target_agent_id=1),
        judge,
        FakeStageTrackingSettingsStore(StageTrackingSettings("off", 4)),
    )

    use_case.execute(1, "The first useful brand note is mostly about trust.")

    assert judge.calls == []
    assert store.stage_progress_json == ""
    assert store.stage_flags[1] is False


def test_export_refresh_trigger_runs_judge_like_final_report() -> None:
    store = InMemoryTurnStore(
        messages=(
            _line(1, "user", "The brand promise is plain-spoken planning for founders."),
            _line(1, "assistant", "Noted."),
            _line(1, "user", "The proof is that teams return after failed agency work."),
            _line(2, "user", "Only one founder invariant so far."),
        )
    )
    judge = RecordingJudge(complete=True, confidence=1.0)
    use_case = RefreshStageTrackingBeforeReport(
        store,
        judge,
        FakeStageTrackingSettingsStore(StageTrackingSettings("hybrid", 4)),
    )

    use_case.execute(1, trigger="export")

    assert judge.calls == [1]
    assert store.stage_flags[1] is True


def _minimal_export_bundle() -> InterviewSessionReadBundle:
    headline = InterviewSessionReadHeadline(
        id=1,
        name="Session",
        client_name="",
        summary="",
        current_agent_id=1,
        stage1_complete=False,
        stage2_complete=False,
        stage3_complete=False,
        stage4_complete=False,
        created_at="",
        updated_at="",
    )
    return InterviewSessionReadBundle(headline, (), ())


def test_load_interview_session_for_export_runs_refresh_before_reader() -> None:
    store = InMemoryTurnStore(
        messages=(
            _line(1, "user", "The brand promise is plain-spoken planning for founders."),
            _line(1, "assistant", "Noted."),
            _line(1, "user", "The proof is that teams return after failed agency work."),
        )
    )
    judge = RecordingJudge(complete=True, confidence=1.0)
    refresh = RefreshStageTrackingBeforeReport(
        store,
        judge,
        FakeStageTrackingSettingsStore(StageTrackingSettings("hybrid", 4)),
    )

    load_order: list[str] = []

    class _Reader:
        def load_bundle(self, session_id: int) -> InterviewSessionReadBundle | None:
            load_order.append("read")
            assert judge.calls == [1]
            assert store.stage_flags[1] is True
            return _minimal_export_bundle()

    load_uc = LoadInterviewSessionForExport(_Reader(), refresh)
    load_uc.execute(1)

    assert load_order == ["read"]
    assert judge.calls == [1]


def test_load_interview_session_for_export_returns_none_when_refresh_raises() -> None:
    class _MissingSessionTurnStore:
        def load_turn_context(self, session_id: int) -> TurnContext:
            raise ValueError(f"Session {session_id} not found")

    judge = RecordingJudge()
    refresh = RefreshStageTrackingBeforeReport(
        _MissingSessionTurnStore(),
        judge,
        FakeStageTrackingSettingsStore(StageTrackingSettings("hybrid", 4)),
    )

    reader_calls = 0

    class _Reader:
        def load_bundle(self, session_id: int) -> InterviewSessionReadBundle | None:
            nonlocal reader_calls
            reader_calls += 1
            return _minimal_export_bundle()

    load_uc = LoadInterviewSessionForExport(_Reader(), refresh)
    assert load_uc.execute(99) is None
    assert reader_calls == 0
    assert judge.calls == []


def test_read_session_stage_tracking_log_is_read_only() -> None:
    store = InMemoryTurnStore()
    judge = RecordingJudge(complete=True, confidence=1.0)
    use_case = ConductInterviewTurn(
        store,
        FakeLlmGateway(target_agent_id=1),
        judge,
        FakeStageTrackingSettingsStore(StageTrackingSettings("hybrid", 4)),
    )
    use_case.execute(1, "A long enough first user message to pass meaningful input gates.")
    read_log = ReadSessionStageTrackingLog(store)
    out = read_log.execute(1)
    assert "entries" in out
    assert len(out["entries"]) >= 1
    # Second call should not add entries (read-only)
    out2 = read_log.execute(1)
    assert len(out2["entries"]) == len(out["entries"])


def test_conduct_interview_persists_stage_tracking_log() -> None:
    store = InMemoryTurnStore()
    judge = RecordingJudge(complete=True, confidence=1.0)
    use_case = ConductInterviewTurn(
        store,
        FakeLlmGateway(target_agent_id=1),
        judge,
        FakeStageTrackingSettingsStore(StageTrackingSettings("hybrid", 4)),
    )
    use_case.execute(1, "The first useful brand note is mostly about trust.")
    log = json.loads(store.stage_tracking_log_json)
    assert len(log) == 1
    assert log[0].get("turn_endpoint") == "auto"
