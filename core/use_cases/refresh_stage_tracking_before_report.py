"""Refresh eligible stage flags before final report/export reads."""

from __future__ import annotations

import logging
from typing import Literal

from orchestrator_v4.core.entities.stage_evaluator import earliest_unfinished_stage
from orchestrator_v4.core.entities.stage_progress import (
    read_stage_progress,
    record_stage_judge_attempt_json,
    should_run_stage_tracking_judge,
)
from orchestrator_v4.core.ports.interview_session_turn_store import (
    InterviewSessionTurnStore,
)
from orchestrator_v4.core.ports.interview_stage_completion_judge import (
    InterviewStageCompletionJudge,
)
from orchestrator_v4.core.ports.stage_tracking_settings_store import (
    StageTrackingSettingsStore,
)
from orchestrator_v4.core.use_cases.stage_tracking_judge_runner import (
    apply_stage_completion_judge,
)

ReportRefreshTrigger = Literal["final_report", "export"]

_LOG = logging.getLogger(__name__)


class RefreshStageTrackingBeforeReport:
    def __init__(
        self,
        turn_store: InterviewSessionTurnStore,
        stage_completion_judge: InterviewStageCompletionJudge,
        stage_tracking_settings_store: StageTrackingSettingsStore,
    ) -> None:
        self._turn_store = turn_store
        self._stage_completion_judge = stage_completion_judge
        self._stage_tracking_settings_store = stage_tracking_settings_store

    def execute(self, session_id: int, *, trigger: ReportRefreshTrigger) -> None:
        ctx = self._turn_store.load_turn_context(session_id)
        settings = self._stage_tracking_settings_store.read()
        flags = ctx.stage_flags()
        progress_json = ctx.stage_progress_json
        judge_ran = False

        for stage_id in (1, 2, 3, 4):
            progress = read_stage_progress(progress_json, stage_id)
            decision = should_run_stage_tracking_judge(
                settings,
                stage_id,
                ctx.messages,
                "",
                progress,
                trigger=trigger,
            )
            if not decision.run_judge:
                continue

            flags = apply_stage_completion_judge(
                stage_id=stage_id,
                messages=ctx.messages,
                stage_flags_before=flags,
                stage_completion_judge=self._stage_completion_judge,
                logger=_LOG,
            )
            progress_json = record_stage_judge_attempt_json(
                progress_json, stage_id, ctx.messages
            )
            judge_ran = True

        if not judge_ran:
            return

        self._turn_store.update_session_state(
            session_id,
            current_agent_id=earliest_unfinished_stage(flags),
            stage_flags=flags,
            stage_progress_json=progress_json,
        )
