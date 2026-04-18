"""Psychological phase and tone directive text (ported from v3 PierceHoltEngine)."""

from __future__ import annotations


def psychological_phase_value(current_agent_id: int, total_user_chat_messages: int) -> str:
    """
    Phase label matching v3 PierceHoltEngine.evaluate_state (.value strings).
    total_user_chat_messages should include messages already persisted plus this turn's user line.
    """
    if current_agent_id <= 2:
        return "EXPLORATION"
    if current_agent_id == 3 and total_user_chat_messages > 5:
        return "CRISIS_INTERVENTION"
    return "EPIPHANY_INTEGRATION"


def get_tone_directive(current_agent_id: int, total_user_chat_messages: int) -> str:
    """Domain-generated tone text passed blindly to the LLM gateway."""
    phase = psychological_phase_value(current_agent_id, total_user_chat_messages)
    directives = {
        "EXPLORATION": (
            "TONE: Warm, probing, and open-ended. The founder is still "
            "exploring their ideas. Encourage free expression. Ask "
            "broad, curiosity-driven questions. Avoid premature judgment "
            "or narrowing the scope."
        ),
        "CRISIS_INTERVENTION": (
            "TONE: Supportive, grounding, and direct. The founder may be "
            "experiencing cognitive dissonance between their assumptions "
            "and customer reality. Validate their feelings, but gently "
            "surface contradictions. Help them sit with discomfort rather "
            "than rushing to resolve it."
        ),
        "EPIPHANY_INTEGRATION": (
            "TONE: Synthesizing, connective, and forward-looking. The "
            "founder is ready to integrate insights into actionable "
            "architecture. Draw explicit connections between earlier "
            "discoveries. Focus on translating insights into concrete "
            "structural decisions."
        ),
    }
    return directives.get(phase, "")
