"""
Phase 2 — AI Extraction Service

Calls Gemma (gemma-4-31b-it) via google-genai SDK, validates the response
against the AnalysisResult Pydantic model, and returns a validated result.

Key design decisions:
  - Uses response_schema=AnalysisResult so the SDK enforces JSON structure natively.
    No regex fence-stripping needed.
  - If the model call or validation fails, raises an exception caught by the
    entries router which stores {"error": "parse_failed"} in the analysis field.
  - User text is always in the USER turn, never interpolated into the system prompt.
"""
from google import genai
from google.genai import types

from app.config import settings
from app.models import AnalysisResult
from app.prompts.extractor import build_extractor_prompt

# Initialised once — thread-safe for FastAPI's async context
_client = genai.Client(api_key=settings.gemini_api_key)


async def run_extraction(
    raw_text: str,
    entry_type: str,
    previous_entries_summary: str = "",
) -> AnalysisResult:
    """
    Phase 2: Extract Jungian symbols, archetypes, emotions, and themes from one entry.
    Returns a validated AnalysisResult or raises on failure.
    """
    prompt = build_extractor_prompt(raw_text, entry_type, previous_entries_summary)

    response = _client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AnalysisResult,
            max_output_tokens=1500,
            temperature=0.2,  # Low temp for structured extraction reliability
        ),
    )

    # SDK populates response.parsed with the Pydantic object when response_schema is set
    if response.parsed is None:
        raise ValueError(f"Model returned no structured output. Raw: {response.text[:500]}")

    return response.parsed
