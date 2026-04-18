"""Lightweight interview session row for list/metadata (no messages)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InterviewSessionSummary:
    """One row from `sessions` — parity with list/export headers, not the full aggregate."""

    id: int
    name: str
    client_name: str
    summary: str
    current_agent_id: int
    stage1_complete: bool
    stage2_complete: bool
    stage3_complete: bool
    stage4_complete: bool
    created_at: str
    updated_at: str

    def __post_init__(self) -> None:
        if self.id < 1:
            raise ValueError(f"id must be positive, got {self.id}")
