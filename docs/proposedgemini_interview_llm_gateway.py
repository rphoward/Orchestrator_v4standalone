"""
Gemini adapter: routing + response generation for interview turns.

Uses the Google GenAI SDK (``google-genai``) as the single Gemini client path.
Routing follows the same structured-JSON prompt as v3.
Response generation implements a strict Draft -> Sense -> Validate pipeline 
to enforce SDT and psychological guardrails without relying on prompt-following.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Sequence

from google import genai
from google.genai import types

from orchestrator_v4.core.entities.interview_turn import ConversationAppend, RoutingDecision

# IMPORTANT: This assumes you have added the Validation classes we built 
# into your pierce_holt_engine.py file!
from orchestrator_v4.core.entities.pierce_holt_engine import DraftEvaluation, ResonanceValidator

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
        
        # In this architecture, we use the assigned agent_model for drafting,
        # and we lock the "Sensor" to the fastest, cheapest model available.
        self._agent_model = agent_model
        self._sensor_model = DEFAULT_FLASH_LITE_MODEL_ID 

    # ── Port: route_intent (Unchanged) ────────────────────────────────────────

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


    # ── The Sensor Prompt Builder ────────────────────────────────────────

    def _build_sensor_prompt(self, draft_text: str) -> str:
        """Forces the fast model to act purely as a Boolean evaluator."""
        return f"""
Analyze the following text and evaluate it against our psychological rubric.
Return ONLY a valid JSON object with boolean (true/false) values. Do not explain your reasoning.

Text to analyze: "{draft_text}"

Required JSON Schema:
{{
    "jargon": bool,
    "monologue": bool,
    "kant_fail": bool,
    "sdt_targeted": bool,
    "autonomous": bool,
    "evocative": bool,
    "reflective": bool,
    "controlling": bool,
    "prescriptive": bool
}}
"""

    # ── Port: get_response (The Upgraded Pipeline) ────────────────────────

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
        
        # 1. Build the foundational system prompt
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

        # --- THE ARCHITECTURAL SHIFT ---
        # We append a hard directive demanding 3 JSON-formatted drafts.
        full_system += (
            "\n\nCRITICAL DIRECTIVE: You must generate 3 distinct options for your next response. "
            "Format your output EXACTLY as a JSON array of strings, like [\"draft 1\", \"draft 2\", \"draft 3\"]."
        )

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

        # 2. Generate the Drafts (Heavyweight Model)
        response = self._client.models.generate_content(
            model=model.strip() or self._agent_model,
            contents=contents,
            config=config,
        )

        text = response.text
        if not text:
            raise RuntimeError("Gemini returned an empty response")

        # Safely extract the JSON array
        try:
            json_match = re.search(r"\[[\s\S]*\]", text)
            if json_match:
                text = json_match.group(0)
            drafts = json.loads(text)
            if not isinstance(drafts, list) or len(drafts) == 0:
                raise ValueError("Payload was not a valid list")
        except Exception as e:
            _LOG.warning(f"Draft extraction failed, falling back to treating output as a single draft. Error: {e}")
            drafts = [text] # Graceful fallback if the LLM refuses to write an array

        # 3. Run the Sensor (Lightweight Model)
        evaluated_drafts = []
        sensor_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0,
        )

        for draft_text in drafts:
            if not isinstance(draft_text, str):
                continue

            sensor_prompt = self._build_sensor_prompt(draft_text)
            
            try:
                sensor_resp = self._client.models.generate_content(
                    model=self._sensor_model, 
                    contents=[{"role": "user", "parts": [{"text": sensor_prompt}]}],
                    config=sensor_config,
                )
                tags = json.loads(sensor_resp.text or "{}")
            except Exception as e:
                _LOG.warning(f"Sensor failed on a draft, defaulting to False tags: {e}")
                tags = {}

            # Map the AI's boolean tags directly to your Core Entity
            evaluation = DraftEvaluation(
                draft_text=draft_text,
                contains_jargon=bool(tags.get("jargon", False)),
                contains_internal_monologue=bool(tags.get("monologue", False)),
                violates_kant_test=bool(tags.get("kant_fail", False)),
                is_sdt_targeted=bool(tags.get("sdt_targeted", False)),
                is_autonomous=bool(tags.get("autonomous", False)),
                is_evocative=bool(tags.get("evocative", False)),
                is_reflective=bool(tags.get("reflective", False)),
                is_controlling=bool(tags.get("controlling", False)),
                is_prescriptive=bool(tags.get("prescriptive", False))
            )
            evaluated_drafts.append(evaluation)

        # 4. The Core makes the final decision
        winning_draft = ResonanceValidator.select_best_draft(evaluated_drafts)

        # 5. Total Firewall Fallback
        if not winning_draft:
            _LOG.warning("ResonanceValidator killed all drafts. Triggering fallback response.")
            return "I want to make sure I'm giving you the space you need here. What feels like the most natural next step for you to explore?"

        return winning_draft

    # ── JSON parsing (Unchanged) ──────────────────────────────────────────────

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