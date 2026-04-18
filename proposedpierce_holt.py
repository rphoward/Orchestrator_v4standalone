from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

# ===========================================================================
# 1. ENUMS (The Absolute Truths of the Domain)
# ===========================================================================
class PsychologicalPhase(Enum):
    EXPLORATION = "EXPLORATION"
    CRISIS_INTERVENTION = "CRISIS_INTERVENTION"
    EPIPHANY_INTEGRATION = "EPIPHANY_INTEGRATION"


# ===========================================================================
# 2. STATE & METRICS (Immutable Context)
# ===========================================================================
@dataclass(frozen=True)
class BehavioralMetrics:
    """The psychological sensor data populated by the Inbound Adapter."""
    # Stall Indicators (Triggers for Crisis)
    lexical_stasis: bool = False
    consequence_looping: bool = False
    premature_negation: bool = False
    
    # Breakthrough Indicators (Triggers for Epiphany)
    curiosity_is_high: bool = False
    ego_defense_active: bool = False


@dataclass(frozen=True)
class InteractionContext:
    """An immutable snapshot of the current conversational state."""
    metrics: BehavioralMetrics

    @property
    def calculated_phase(self) -> PsychologicalPhase:
        """Deterministic state evaluation based strictly on behavioral momentum."""
        # 1. Breakthrough (Crisis -> Epiphany)
        if self.metrics.curiosity_is_high and not self.metrics.ego_defense_active:
            return PsychologicalPhase.EPIPHANY_INTEGRATION
            
        # 2. Stall (Exploration -> Crisis)
        if any([
            self.metrics.lexical_stasis,
            self.metrics.consequence_looping,
            self.metrics.premature_negation
        ]):
            return PsychologicalPhase.CRISIS_INTERVENTION
            
        # 3. Default State
        return PsychologicalPhase.EXPLORATION


@dataclass(frozen=True)
class SystemDirectives:
    """The final, strict contract handed to the Outbound Adapter."""
    phase: PsychologicalPhase
    tone_directive: str
    sdt_guardrail: str
    tactical_directive: str
    anti_pattern_guardrail: str


# ===========================================================================
# 3. GENERATION ENGINE (The Prompt Constructor)
# ===========================================================================
class PierceHoltEngine:
    
    @staticmethod
    def get_tone(phase: PsychologicalPhase) -> str:
        tones = {
            PsychologicalPhase.EXPLORATION: (
                "TONE: Warm, probing, and open-ended. Encourage free expression. "
                "Ask broad, curiosity-driven questions. Avoid premature judgment."
            ),
            PsychologicalPhase.CRISIS_INTERVENTION: (
                "TONE: Supportive, grounding, and direct. Validate feelings, but gently "
                "surface contradictions. Help them sit with discomfort."
            ),
            PsychologicalPhase.EPIPHANY_INTEGRATION: (
                "TONE: Synthesizing, connective, and forward-looking. Focus on "
                "translating insights into concrete structural decisions."
            ),
        }
        return tones.get(phase, "")

    @staticmethod
    def get_sdt_guardrail(phase: PsychologicalPhase) -> str:
        if phase in [PsychologicalPhase.EXPLORATION, PsychologicalPhase.CRISIS_INTERVENTION]:
            return (
                "CRITICAL DIRECTIVE (AUTONOMY): You must never prescribe actions or use "
                "controlling language ('should', 'must'). Frame inquiries to promote "
                "'Tracking' (exploring natural consequences) rather than 'Pliance' "
                "(obedience). Ensure next steps are autonomous experiments."
            )
        if phase == PsychologicalPhase.EPIPHANY_INTEGRATION:
            return (
                "CRITICAL DIRECTIVE (COMPETENCE): Acknowledge the complexity of their "
                "decisions. Frame the synthesis as a product of their own insights, "
                "explicitly reinforcing their capability."
            )
        return ""

    @staticmethod
    def get_tactical_directive(phase: PsychologicalPhase) -> str:
        if phase == PsychologicalPhase.CRISIS_INTERVENTION:
            return (
                "TACTICAL DIRECTIVE (PATTERN INTERRUPT): The user is in a cognitive stall. "
                "You must instantly interrupt the pattern. Acknowledge the loop they are in, "
                "and ask a targeted question that highlights a missing piece of information "
                "to create a 'moderate information gap'."
            )
        if phase == PsychologicalPhase.EPIPHANY_INTEGRATION:
            return (
                "TACTICAL DIRECTIVE (ANCHORING): The user is showing seeking energy. Do not "
                "cheerlead. Validate the shift explicitly, and prompt them to define the "
                "immediate, concrete next step that tests this new insight in reality."
            )
        return "TACTICAL DIRECTIVE (EXPLORING): Maintain open exploration. Follow the user's lead."

    @staticmethod
    def get_anti_pattern_guardrail() -> str:
        """The universal negative constraints (Target 3) applied to all phases."""
        return (
            "CRITICAL DIRECTIVE (BANNED BEHAVIORS): You must never propose a concrete plan, "
            "give direct advice, or use prescriptive/controlling language. You are strictly "
            "forbidden from 'rescuing' the user with empty praise, superficial cheerleading, "
            "or clinical detachment. Maintain the boundaries of a coach, not a therapist. "
            "Never reveal your internal logic, psychological framework names (e.g., SDT, WOOP), "
            "or coaching jargon to the user."
        )

    @classmethod
    def evaluate_state(cls, context: InteractionContext) -> SystemDirectives:
        phase = context.calculated_phase
        return SystemDirectives(
            phase=phase,
            tone_directive=cls.get_tone(phase),
            sdt_guardrail=cls.get_sdt_guardrail(phase),
            tactical_directive=cls.get_tactical_directive(phase),
            anti_pattern_guardrail=cls.get_anti_pattern_guardrail()
        )


# ===========================================================================
# 4. VALIDATION ENGINE (The Resonance Check)
# ===========================================================================
@dataclass(frozen=True)
class DraftEvaluation:
    """A single generated response and the boolean traits tagged by the semantic sensor."""
    draft_text: str
    
    # --- The Firewall (Hard Fails) ---
    contains_jargon: bool          
    contains_internal_monologue: bool 
    violates_kant_test: bool       
    
    # --- Semantic Tags (Used for Scoring) ---
    is_sdt_targeted: bool
    is_autonomous: bool
    is_evocative: bool
    is_reflective: bool
    is_controlling: bool
    is_prescriptive: bool
    
    # --- Conditional Context Tags ---
    aligns_with_context: bool = False
    ignores_context: bool = False
    pivots_from_stall: bool = False

    @property
    def is_valid(self) -> bool:
        """The strict logic gate. If any of these are true, the draft is dead."""
        return not (
            self.contains_jargon or 
            self.contains_internal_monologue or 
            self.violates_kant_test
        )

    @property
    def total_score(self) -> float:
        """The deterministic scoring tournament. Math lives here, not in the LLM."""
        if not self.is_valid:
            return -999.0 

        score = 0.0
        
        # Static Rubric
        if self.is_sdt_targeted: score += 1.8
        if self.is_autonomous: score += 1.0
        if self.is_evocative: score += 0.9
        if self.is_reflective: score += 0.3
        
        # Penalties
        if self.is_controlling: score -= 2.0
        if self.is_prescriptive: score -= 2.0
        
        # Conditional Rubric
        if self.aligns_with_context: score += 3.0
        if self.ignores_context: score -= 3.0
        if self.pivots_from_stall: score += 2.0
            
        return score


class ResonanceValidator:
    """The core engine that decides what the user is allowed to see."""

    @staticmethod
    def select_best_draft(drafts: List[DraftEvaluation]) -> Optional[str]:
        valid_drafts = [d for d in drafts if d.is_valid]
        
        if not valid_drafts:
            return None 

        max_score = max(valid_drafts, key=lambda d: d.total_score).total_score
        top_drafts = [d for d in valid_drafts if d.total_score == max_score]

        # Tie-Breaker: Default to highest Autonomy
        if len(top_drafts) > 1:
            top_drafts.sort(key=lambda d: d.is_autonomous, reverse=True)

        return top_drafts[0].draft_text