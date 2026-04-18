"""In-memory InterviewSessionTurnStore for B1 until SQLite writes land in B2."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone

from orchestrator_v4.core.entities.interview_turn import (
    ConversationAppend,
    InterviewTurnAgentRosterEntry,
    RoutingLogAppend,
    TurnContext,
    TurnConversationLine,
    TurnRoutingLogLine,
)
from orchestrator_v4.core.ports.interview_session_turn_store import InterviewSessionTurnStore


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class _MutableSession:
    session_id: int
    name: str
    current_agent_id: int
    stage1_complete: bool
    stage2_complete: bool
    stage3_complete: bool
    stage4_complete: bool
    messages: list[TurnConversationLine] = field(default_factory=list)
    routing_logs: list[TurnRoutingLogLine] = field(default_factory=list)
    agents: tuple[InterviewTurnAgentRosterEntry, ...] = ()

    def to_context(self) -> TurnContext:
        return TurnContext(
            session_id=self.session_id,
            name=self.name,
            current_agent_id=self.current_agent_id,
            stage1_complete=self.stage1_complete,
            stage2_complete=self.stage2_complete,
            stage3_complete=self.stage3_complete,
            stage4_complete=self.stage4_complete,
            messages=tuple(self.messages),
            routing_logs=tuple(self.routing_logs),
            agents=self.agents,
        )


class InMemoryInterviewSessionTurnStore(InterviewSessionTurnStore):
    def __init__(self) -> None:
        self._sessions: dict[int, _MutableSession] = {}

    def seed_context(self, ctx: TurnContext) -> None:
        """Test/dev helper: replace session state from a frozen TurnContext."""
        self._sessions[ctx.session_id] = _MutableSession(
            session_id=ctx.session_id,
            name=ctx.name,
            current_agent_id=ctx.current_agent_id,
            stage1_complete=ctx.stage1_complete,
            stage2_complete=ctx.stage2_complete,
            stage3_complete=ctx.stage3_complete,
            stage4_complete=ctx.stage4_complete,
            messages=list(ctx.messages),
            routing_logs=list(ctx.routing_logs),
            agents=ctx.agents,
        )

    def _require(self, session_id: int) -> _MutableSession:
        s = self._sessions.get(session_id)
        if s is None:
            raise ValueError(f"Session {session_id} not found")
        return s

    def load_turn_context(self, session_id: int) -> TurnContext:
        return self._require(session_id).to_context()

    def append_messages(self, session_id: int, messages: Sequence[ConversationAppend]) -> None:
        s = self._require(session_id)
        for m in messages:
            ts = m.timestamp or _utc_timestamp()
            s.messages.append(
                TurnConversationLine(
                    agent_id=m.agent_id,
                    role=m.role,
                    content=m.content,
                    message_type=m.message_type,
                    timestamp=ts,
                )
            )

    def append_routing_log(self, session_id: int, log: RoutingLogAppend) -> None:
        s = self._require(session_id)
        ts = log.timestamp or _utc_timestamp()
        s.routing_logs.append(
            TurnRoutingLogLine(
                input_text=log.input_text,
                agent_id=log.agent_id,
                agent_name=log.agent_name,
                reason=log.reason,
                timestamp=ts,
            )
        )

    def update_session_state(
        self,
        session_id: int,
        *,
        current_agent_id: int | None = None,
        stage_flags: dict[int, bool] | None = None,
        name: str | None = None,
    ) -> None:
        s = self._require(session_id)
        if current_agent_id is not None:
            s.current_agent_id = current_agent_id
        if stage_flags is not None:
            s.stage1_complete = bool(stage_flags.get(1, s.stage1_complete))
            s.stage2_complete = bool(stage_flags.get(2, s.stage2_complete))
            s.stage3_complete = bool(stage_flags.get(3, s.stage3_complete))
            s.stage4_complete = bool(stage_flags.get(4, s.stage4_complete))
        if name is not None:
            s.name = name
