"""
Pydantic models for the Jungian analysis JSONB shape and complexes.
These are used to validate AI output before any DB write.
"""
from typing import Optional
from pydantic import BaseModel, Field


class Symbol(BaseModel):
    name: str
    category: str
    significance: str


class Archetype(BaseModel):
    name: str
    confidence: float  # 0.0 – 1.0
    evidence: str
    projection_status: Optional[str] = None  # "projected" | "integrating" | "ambiguous"


class SymbolArchetypeAttribution(BaseModel):
    symbol: str
    archetype: str
    confidence: float
    evidence: str


class Emotion(BaseModel):
    name: str
    valence: float   # -1.0 (negative) to 1.0 (positive)
    intensity: float  # 0.0 to 1.0


class AnalysisResult(BaseModel):
    symbols: list[Symbol]
    archetypes: list[Archetype]
    emotions: list[Emotion]
    themes: list[str]
    compensation_axis: Optional[str] = None      # NEW — what the unconscious is compensating for
    ego_strength_signal: Optional[int] = None    # NEW — 1–6 scale
    lysis_assessment: Optional[str] = None       # NEW — "resolved" | "unresolved" | "ambiguous"
    jungian_summary: str
    connections_to_previous: list[str]           # list of entry UUIDs
    symbol_archetype_attributions: list[SymbolArchetypeAttribution] = Field(default_factory=list)


class Complex(BaseModel):
    name: str
    summary: str
    symbols: list[str]
    overdetermined_symbols: Optional[list[str]] = None
    affective_core: Optional[str] = None
    projection_status: Optional[str] = None     # "projection" | "integrating" | "ambiguous"
    golden_shadow: Optional[bool] = None
    golden_shadow_owned: Optional[bool] = None
    individuation_note: Optional[str] = None


class AmplificationQuestion(BaseModel):
    symbol: str
    question: str


class AmplificationResult(BaseModel):
    symbols_to_amplify: list[AmplificationQuestion]


class IntegrationRiskFlag(BaseModel):
    present: bool
    severity: Optional[str] = None
    evidence: Optional[str] = None


class ShadowBypassFlag(BaseModel):
    present: bool
    form: Optional[str] = None   # "avoidance" | "golden_shadow_inflation" | "both"
    severity: Optional[str] = None
    evidence: Optional[str] = None


class IntegrationRiskResult(BaseModel):
    spiritual_inflation: IntegrationRiskFlag
    ego_dissolution_without_regrounding: IntegrationRiskFlag
    shadow_bypassing: ShadowBypassFlag
    premature_closure: IntegrationRiskFlag
    integration_guidance: str
    overall_risk_level: str  # "none" | "low" | "moderate" | "high"


class LongitudinalResult(BaseModel):
    individuation_arc_summary: str
    dynamic_shadow_tracker: str
    transpersonal_integration_state: str
    clinical_risk_advisory: Optional[str] = None
