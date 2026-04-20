"""Build ``GenerateContentConfig`` for router and agent Gemini calls (SDK types only)."""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types

from orchestrator_v4.infrastructure.ai.gemini_policy_constants import (
    ROUTER_GENERATE_TEMPERATURE,
)

_LOG = logging.getLogger(__name__)

_ROUTER_RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "agent_id": types.Schema(type=types.Type.INTEGER),
        "workflow_status": types.Schema(
            type=types.Type.STRING,
            enum=["STAY", "DRIFT", "ADVANCE"],
        ),
        "reason": types.Schema(type=types.Type.STRING),
    },
    required=["agent_id", "workflow_status", "reason"],
)

_STAGE_COMPLETION_JUDGE_RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "stage_complete": types.Schema(type=types.Type.BOOLEAN),
        "confidence": types.Schema(type=types.Type.NUMBER),
        "reason": types.Schema(type=types.Type.STRING),
        "evidence_found": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
        ),
        "missing_topics": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
        ),
    },
    required=["stage_complete", "confidence", "reason"],
)


def resolve_thinking_level_enum(raw: str) -> types.ThinkingLevel | None:
    level = raw.strip().upper()
    if not level:
        return None
    if level == "OFF":
        level = "MINIMAL"
    if level not in {"MINIMAL", "LOW", "MEDIUM", "HIGH"}:
        return None
    return getattr(types.ThinkingLevel, level, None)


def parse_temperature_for_config(raw: str) -> float | None:
    candidate = raw.strip()
    if not candidate:
        return None
    try:
        parsed = float(candidate)
    except ValueError:
        return None
    if parsed == 0.0:
        return 0.0

    clamped = max(0.1, min(2.0, parsed))
    if clamped != parsed:
        _LOG.warning(
            "Agent temperature %s is out of supported non-zero range [0.1, 2.0]; "
            "using soft-clamped value %.1f",
            candidate,
            clamped,
        )
    return clamped


def build_router_generate_config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=_ROUTER_RESPONSE_SCHEMA,
        temperature=ROUTER_GENERATE_TEMPERATURE,
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.MINIMAL,
        ),
    )


def build_stage_completion_judge_generate_config(
    system_instruction: str,
) -> types.GenerateContentConfig:
    """Structured-JSON config for the stage-completion judge.

    Matches the router profile (``temperature=0.1``, thinking MINIMAL) so
    stage-grading latency and cost stay in the same order of magnitude as
    routing. The system_instruction carries the per-stage completion prompt
    body loaded by the adapter from ``runtime/prompts/stage_completion/``.
    """
    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=_STAGE_COMPLETION_JUDGE_RESPONSE_SCHEMA,
        temperature=ROUTER_GENERATE_TEMPERATURE,
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.MINIMAL,
        ),
    )


def build_agent_generate_config(
    system_instruction: str,
    temperature_str: str,
    thinking_level_str: str,
    include_thoughts: bool,
) -> types.GenerateContentConfig:
    config_kwargs: dict[str, Any] = {
        "system_instruction": system_instruction,
    }

    parsed_temp = parse_temperature_for_config(temperature_str)
    if parsed_temp is not None:
        config_kwargs["temperature"] = parsed_temp

    enum_level = resolve_thinking_level_enum(thinking_level_str)
    if enum_level is not None or include_thoughts:
        thinking_kwargs: dict[str, Any] = {}
        if enum_level is not None:
            thinking_kwargs["thinking_level"] = enum_level
        elif include_thoughts:
            fallback_level = getattr(types.ThinkingLevel, "MINIMAL", None)
            if fallback_level is not None:
                thinking_kwargs["thinking_level"] = fallback_level
        if include_thoughts:
            thinking_kwargs["include_thoughts"] = True

        try:
            config_kwargs["thinking_config"] = types.ThinkingConfig(**thinking_kwargs)
        except TypeError:
            thinking_kwargs.pop("include_thoughts", None)
            if thinking_kwargs:
                config_kwargs["thinking_config"] = types.ThinkingConfig(**thinking_kwargs)

    return types.GenerateContentConfig(**config_kwargs)
