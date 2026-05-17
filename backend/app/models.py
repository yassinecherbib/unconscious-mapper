"""
Pydantic models for the Jungian analysis JSONB shape and complexes.
These are used to validate AI output before any DB write.
"""
from pydantic import BaseModel


class Symbol(BaseModel):
    name: str
    category: str
    significance: str


class Archetype(BaseModel):
    name: str
    confidence: float  # 0.0 – 1.0
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
    jungian_summary: str
    connections_to_previous: list[str]  # list of entry UUIDs


class Complex(BaseModel):
    name: str
    summary: str
    symbols: list[str]
