"""
Gemini adapter: routing + response generation for interview turns.

Uses the Google GenAI SDK (``google-genai``) as the single Gemini client path.
Routing follows the same structured-JSON prompt as v3; response generation injects
tone directives and cross-agent context into the system instruction, matching v3
DomainAgent behavior.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Sequence

from google import genai
from google.genai import types

from orchestrator_v4.core.entities.interview_turn import ConversationAppend, RoutingDecision
from orchestrator_v4.infrastructure.ai.gemini_generate_config import (
    build_agent_generate_config,
    build_router_generate_config,
)
from orchestrator_v4.infrastructure.ai.gemini_policy_constants import (
    DEFAULT_FLASH_LITE_MODEL_ID,
)

ROUTING_DIRECTIVE_TEMPLATE = (
    "You are an interview routing engine.\n"
    "CURRENT STAGE ID: {current_stage_id}\n"
    "\n"
    "Your goal is to move the user through the stages in order (1 -> 2 -> 3 -> 4).\n"
    "\n"
    "AGENTS AND THEIR DOMAINS:\n"
    "{agent_hints}\n"
    "\n"
    "DECISION LOGIC:\n"
    "- STAY: User is providing data for the CURRENT STAGE.\n"
    "- DRIFT: User is talking about a DIFFERENT stage, but current stage isn't finished.\n"
    "- ADVANCE: User has provided sufficient data for the current stage OR suggests moving on.\n"
    "\n"
    'Respond with ONLY a JSON object: '
    '{{"agent_id": <number>, "workflow_status": "STAY"|"DRIFT"|"ADVANCE", "reason": "..."}}'
)

_LOG = logging.getLogger(__name__)


class GeminiInterviewLlmGateway:
    """Implements ``InterviewLlmGateway`` using the Google GenAI SDK."""

    def __init__(
        self,
        api_key: str,
        *,
        router_model: str = DEFAULT_FLASH_LITE_MODEL_ID,
        agent_model: str = DEFAULT_FLASH_LITE_MODEL_ID,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self._router_model = router_model
        self._agent_model = agent_model

    # ── Port: route_intent ────────────────────────────────────────

    def route_intent(
        self,
        user_input: str,
        current_agent_id: int,
        agent_hints: dict[int, str],
    ) -> RoutingDecision:
        hints_text = "\n".join(
            f"Agent {aid}: {hint}" for aid, hint in sorted(agent_hints.items())
        )
        prompt = (
            ROUTING_DIRECTIVE_TEMPLATE.format(
                current_stage_id=current_agent_id,
                agent_hints=hints_text,
            )
            + f'\n\nConsultant\'s input: "{user_input}"'
        )

        config = build_router_generate_config()

        try:
            response = self._client.models.generate_content(
                model=self._router_model,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                config=config,
            )
        except Exception:
            _LOG.warning(
                "route_intent Gemini call failed; defaulting to STAY on current agent",
                exc_info=True,
            )
            return RoutingDecision(
                target_agent_id=current_agent_id,
                workflow_status="STAY",
                reason="Routing failed (API error); defaulting to current agent",
            )

        return self._parse_routing_response(response.text or "", current_agent_id)

    # ── Port: get_response ────────────────────────────────────────

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
        full_system = system_prompt

        if psychological_phase:
            full_system += (
                "\n\n=== PSYCHOLOGICAL TONE DIRECTIVE ===\n"
                f"{psychological_phase}\n"
                "==================================="
            )

        if cross_context:
            block = (
                "\n\n=== RECENT GLOBAL CONVERSATION CONTEXT ===\n"
                "For situational awareness, here is what the consultant "
                "recently discussed with OTHER agents. Use this to avoid "
                "repeating questions.\n\n"
            )
            for msg in cross_context:
                speaker = (
                    "Consultant/Founder"
                    if msg.role == "user"
                    else f"Agent ({msg.source_agent_name or f'Agent {msg.agent_id}'})"
                )
                block += f"[{speaker}]: {msg.content}\n"
            block += "==========================================\n"
            full_system += block

        # history already includes the current user message (appended by use case)
        contents: list[types.Content] = []
        for msg in history:
            role = "user" if msg.role == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=msg.content)])
            )

        config = build_agent_generate_config(
            system_instruction=full_system,
            temperature_str=temperature,
            thinking_level_str=thinking_level,
            include_thoughts=include_thoughts,
        )

        response = self._client.models.generate_content(
            model=model.strip() or self._agent_model,
            contents=contents,
            config=config,
        )

        text = response.text
        if not text:
            raise RuntimeError("Gemini returned an empty response")
        return text

    # ── JSON parsing ──────────────────────────────────────────────

    @staticmethod
    def _parse_routing_response(
        raw_text: str, fallback_agent_id: int,
    ) -> RoutingDecision:
        try:
            json_match = re.search(r"\{[\s\S]*\}", raw_text)
            if json_match:
                raw_text = json_match.group(0)
            data = json.loads(raw_text)
        except (json.JSONDecodeError, TypeError):
            return RoutingDecision(
                target_agent_id=fallback_agent_id,
                workflow_status="STAY",
                reason="Default routing (unparseable router response)",
            )

        if not isinstance(data, dict):
            return RoutingDecision(
                target_agent_id=fallback_agent_id,
                workflow_status="STAY",
                reason="Default routing (router JSON was not an object)",
            )

        try:
            agent_id = int(data.get("agent_id", data.get("id", fallback_agent_id)))
        except (ValueError, TypeError):
            return RoutingDecision(
                target_agent_id=fallback_agent_id,
                workflow_status="STAY",
                reason="Default routing (unparseable router response)",
            )

        if agent_id < 1 or agent_id > 4:
            agent_id = fallback_agent_id

        return RoutingDecision(
            target_agent_id=agent_id,
            workflow_status=str(data.get("workflow_status", "STAY")),
            reason=str(data.get("reason", "Routed by AI")),
        )
