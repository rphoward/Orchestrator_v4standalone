"""Port: load and mutate session state for one interview turn."""

from __future__ import annotations

from typing import Protocol, Sequence

from orchestrator_v4.core.entities.interview_turn import (
    ConversationAppend,
    RoutingLogAppend,
    TurnContext,
)


class InterviewSessionTurnStore(Protocol):
    def load_turn_context(self, session_id: int) -> TurnContext:
        """Headline + messages + routing logs + agent roster."""
        ...

    def append_messages(self, session_id: int, messages: Sequence[ConversationAppend]) -> None:
        ...

    def append_routing_log(self, session_id: int, log: RoutingLogAppend) -> None:
        ...

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
        ...
