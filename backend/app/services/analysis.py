"""
Phase 2 — AI Extraction Service (updated)

Changes vs original:
  - Model changed to gemma-4-27b-it (Gemma 4, ~26B total / 4B active MoE)
  - Accepts optional personal_associations string for amplification context
  - Imports updated AnalysisResult with new fields
"""
from google import genai
from google.genai import types

from app.config import settings
from app.models import AnalysisResult
from app.prompts.extractor import build_extractor_prompt

# Gemma 4 (user-specified exact MoE model)
GEMMA_MODEL = "gemma-4-26b-a4b-it"

_client = genai.Client(api_key=settings.gemini_api_key)


async def run_extraction(
    raw_text: str,
    entry_type: str,
    previous_entries_summary: str = "",
    personal_associations: str = "",
) -> AnalysisResult:
    """
    Extract Jungian symbols, archetypes, emotions, themes, and new fields
    (ego_strength_signal, lysis_assessment, compensation_axis) from one entry.
    Returns a validated AnalysisResult or raises on failure.
    """
    prompt = build_extractor_prompt(
        raw_text=raw_text,
        entry_type=entry_type,
        previous_entries_summary=previous_entries_summary,
        personal_associations=personal_associations,
    )

    response = _client.models.generate_content(
        model=GEMMA_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AnalysisResult,
            max_output_tokens=1500,
            temperature=0.2,
        ),
    )

    if response.parsed is None:
        raise ValueError(f"Model returned no structured output. Raw: {response.text[:500]}")

    return response.parsed
