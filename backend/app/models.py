"""
Pydantic models for the Jungian analysis JSONB shape and complexes.
These are used to validate AI output before any DB write.
"""
from typing import Literal, Optional

from pydantic import BaseModel


class Symbol(BaseModel):
    name: str
    category: str
    significance: str


class Archetype(BaseModel):
    name: str
    confidence: float  # 0.0 – 1.0
    evidence: str
    projection_status: Literal["projection", "integrating", "ambiguous"] = "ambiguous"  # NEW


class Emotion(BaseModel):
    name: str
    valence: float   # -1.0 (negative) to 1.0 (positive)
    intensity: float  # 0.0 to 1.0


class CompensationAxis(BaseModel):                          # NEW
    summary: str
    insufficient_material: bool = False


class EgoStrengthSignal(BaseModel):                         # NEW
    score: int        # 1–6
    rationale: str


class LysisAssessment(BaseModel):                           # NEW
    result: Literal["resolved", "unresolved", "ambiguous", "not_applicable"]
    interpretation: str


class AnalysisResult(BaseModel):
    symbols: list[Symbol]
    archetypes: list[Archetype]
    emotions: list[Emotion]
    themes: list[str]
    jungian_summary: str
    connections_to_previous: list[str]  # list of entry UUIDs
    compensation_axis: Optional[CompensationAxis] = None    # NEW
    ego_strength_signal: Optional[EgoStrengthSignal] = None  # NEW
    lysis_assessment: Optional[LysisAssessment] = None       # NEW


class Complex(BaseModel):
    name: str
    summary: str
    symbols: list[str]
    overdetermined_symbols: list[str] = []            # NEW
    affective_core: Optional[str] = None             # NEW
    projection_status: str = "ambiguous"             # NEW
    golden_shadow: bool = False                      # NEW
    golden_shadow_owned: bool = False                # NEW
    individuation_note: Optional[str] = None         # NEW


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_ego_score(analysis: AnalysisResult) -> Optional[int]:
    return analysis.ego_strength_signal.score if analysis.ego_strength_signal else None


def get_dominant_archetypes(analysis: AnalysisResult) -> list[str]:
    return [a.name for a in analysis.archetypes if a.confidence >= 0.6]


def get_lysis(analysis: AnalysisResult) -> Optional[str]:
    return analysis.lysis_assessment.result if analysis.lysis_assessment else None
