"""
Gemini adapter: grades whether a single interview stage is complete.

Implements ``InterviewStageCompletionJudge`` using the Google GenAI SDK,
with the same structured-JSON + MINIMAL-thinking profile as the router.
Loads the per-stage completion prompt body from
``runtime/prompts/stage_completion/N_<stage_name>_completion.md`` via the
shared ``CachedPromptFileReader``; adapter never raises for model-side
errors — any failure becomes a ``judge_error:`` verdict that the use case
routes to the heuristic fallback.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping, Sequence

from google import genai

from orchestrator_v4.core.entities.interview_turn import TurnConversationLine
from orchestrator_v4.core.entities.stage_completion_verdict import (
    StageCompletionVerdict,
)
from orchestrator_v4.core.ports.interview_stage_completion_judge import (
    InterviewStageCompletionJudge,
)
from orchestrator_v4.infrastructure.ai.gemini_generate_config import (
    build_stage_completion_judge_generate_config,
)
from orchestrator_v4.infrastructure.ai.gemini_policy_constants import (
    DEFAULT_FLASH_LITE_MODEL_ID,
)
from orchestrator_v4.infrastructure.persistence.cached_prompt_file_reader import (
    CachedPromptFileReader,
)

_LOG = logging.getLogger(__name__)

# Filenames mirror the stage prompt filenames, with a ``_completion`` suffix.
_COMPLETION_PROMPT_FILE_BY_STAGE: dict[int, str] = {
    1: "1_brand_spine_completion.md",
    2: "2_founder_extraction_completion.md",
    3: "3_customer_reality_completion.md",
    4: "4_architecture_translation_completion.md",
}


def _judge_error_verdict(stage_id: int, reason_suffix: str) -> StageCompletionVerdict:
    return StageCompletionVerdict(
        stage_id=stage_id,
        stage_complete=False,
        confidence=0.0,
        reason=f"judge_error: {reason_suffix}",
    )


class GeminiStageCompletionJudge(InterviewStageCompletionJudge):
    """Implements ``InterviewStageCompletionJudge`` using the Google GenAI SDK."""

    def __init__(
        self,
        api_key: str,
        prompt_cache: CachedPromptFileReader,
        *,
        stage_completion_prompts_relative_dir: str = "stage_completion",
        judge_model: str = DEFAULT_FLASH_LITE_MODEL_ID,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self._prompt_cache = prompt_cache
        self._prompts_dir = stage_completion_prompts_relative_dir
        self._judge_model = judge_model

    def judge_stage_completion(
        self,
        stage_id: int,
        messages: Sequence[TurnConversationLine],
        stage_flags_before: Mapping[int, bool],
    ) -> StageCompletionVerdict:
        # Domain-boundary defense: only 1..4 are real stages.
        prompt_filename = _COMPLETION_PROMPT_FILE_BY_STAGE.get(stage_id)
        if prompt_filename is None:
            return _judge_error_verdict(stage_id, f"stage_id {stage_id} not in 1..4")

        relative_path = f"{self._prompts_dir}/{prompt_filename}"
        try:
            system_instruction = self._prompt_cache.read_or_empty(relative_path)
        except Exception:
            _LOG.warning(
                "stage_completion_judge prompt load failed; relative_path=%r",
                relative_path,
                exc_info=True,
            )
            return _judge_error_verdict(stage_id, "prompt_load_failed")

        active_stage_lines = [m for m in messages if m.agent_id == stage_id]
        transcript_block = _render_transcript_block(active_stage_lines)
        flags_block = _render_flags_block(stage_flags_before)

        user_prompt = (
            f"STAGE_ID: {stage_id}\n"
            f"PRIOR_STAGE_FLAGS:\n{flags_block}\n\n"
            f"ACTIVE_STAGE_TRANSCRIPT:\n{transcript_block}\n\n"
            "Decide whether this stage is complete per the rubric in the system "
            "instruction. Output only the JSON object specified by OUTPUT CONTRACT."
        )

        config = build_stage_completion_judge_generate_config(
            system_instruction=system_instruction
        )

        _LOG.info(
            "stage_completion_judge call model=%s stage_id=%d transcript_lines=%d",
            self._judge_model,
            stage_id,
            len(active_stage_lines),
        )

        try:
            response = self._client.models.generate_content(
                model=self._judge_model,
                contents=[{"role": "user", "parts": [{"text": user_prompt}]}],
                config=config,
            )
        except Exception:
            _LOG.warning(
                "stage_completion_judge Gemini call failed",
                exc_info=True,
            )
            return _judge_error_verdict(stage_id, "api_error")

        raw_text = response.text or ""
        _LOG.info(
            "stage_completion_judge raw response.text[:200]=%r (total_len=%d)",
            raw_text[:200],
            len(raw_text),
        )
        verdict = _parse_verdict_response(raw_text, stage_id)
        _LOG.info(
            "stage_completion_judge parsed stage_id=%d complete=%s confidence=%.2f reason=%r",
            verdict.stage_id,
            verdict.stage_complete,
            verdict.confidence,
            verdict.reason,
        )
        return verdict


def _render_transcript_block(lines: Sequence[TurnConversationLine]) -> str:
    if not lines:
        return "(no messages yet for this stage)"
    rendered: list[str] = []
    for m in lines:
        role = m.role if m.role in ("user", "assistant", "system") else "assistant"
        rendered.append(f"[{role}]: {m.content}")
    return "\n".join(rendered)


def _render_flags_block(flags: Mapping[int, bool]) -> str:
    return "\n".join(
        f"  stage{i}_complete={bool(flags.get(i, False))}" for i in (1, 2, 3, 4)
    )


def _parse_verdict_response(raw_text: str, stage_id: int) -> StageCompletionVerdict:
    try:
        json_match = re.search(r"\{[\s\S]*\}", raw_text)
        text = json_match.group(0) if json_match else raw_text
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return _judge_error_verdict(stage_id, "unparseable_json")

    if not isinstance(data, dict):
        return _judge_error_verdict(stage_id, "response_not_object")

    try:
        stage_complete = bool(data["stage_complete"])
        confidence = float(data["confidence"])
    except (KeyError, TypeError, ValueError):
        return _judge_error_verdict(stage_id, "missing_or_bad_required_fields")

    # Clamp confidence to the contract range.
    if confidence < 0.0:
        confidence = 0.0
    elif confidence > 1.0:
        confidence = 1.0

    reason = str(data.get("reason", "") or "")
    evidence_found = _safe_str_tuple(data.get("evidence_found"))
    missing_topics = _safe_str_tuple(data.get("missing_topics"))

    return StageCompletionVerdict(
        stage_id=stage_id,
        stage_complete=stage_complete,
        confidence=confidence,
        reason=reason,
        evidence_found=evidence_found,
        missing_topics=missing_topics,
    )


def _safe_str_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(x) for x in value if isinstance(x, (str, int, float, bool)))
