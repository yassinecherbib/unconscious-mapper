"""
Integration Risk Service

Runs after the main extraction for psychedelic entries and low-ego meditation entries.
Returns an integration risk assessment to be stored in the entry's analysis field
and surfaced in the UI as "integration guidance" (never as a warning or diagnosis).

Trigger condition:
  entry_type == 'psychedelic'
  OR (entry_type == 'meditation' AND ego_strength_signal <= 2)
"""
import json

from google import genai
from google.genai import types

from app.config import settings
from app.prompts.integration_risk import build_integration_risk_prompt

from app.models import IntegrationRiskResult

_client = genai.Client(api_key=settings.gemini_api_key)


def _should_run(entry_type: str, ego_strength_signal: int | None) -> bool:
    if entry_type == "psychedelic":
        return True
    if entry_type == "meditation" and ego_strength_signal is not None and ego_strength_signal <= 2:
        return True
    return False


async def run_integration_risk(
    raw_text: str,
    entry_type: str,
    jungian_summary: str,
    ego_strength_signal: int | None,
    user_id: str,
    db,
) -> dict | None:
    """
    Runs integration risk assessment if triggered.
    Returns the risk dict to be merged into the entry's analysis field,
    or None if the trigger condition is not met.
    """
    if not _should_run(entry_type, ego_strength_signal):
        return None

    # Fetch last 3 entry summaries for context
    recent_result = (
        db.table("entries")
        .select("analysis")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(3)
        .execute()
    )
    recent_summaries = []
    for row in recent_result.data or []:
        analysis = row.get("analysis") or {}
        if isinstance(analysis, dict) and "jungian_summary" in analysis:
            recent_summaries.append(analysis["jungian_summary"])

    prompt = build_integration_risk_prompt(
        raw_text=raw_text,
        entry_type=entry_type,
        jungian_summary=jungian_summary,
        ego_strength_signal=ego_strength_signal or 3,
        recent_entries_summaries=recent_summaries,
    )

    try:
        response = await _client.aio.models.generate_content(
            model="gemma-4-26b-a4b-it",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=IntegrationRiskResult,
                max_output_tokens=800,
                temperature=0.2,
            ),
        )
        if response.parsed is None:
            print(f"[integration_risk] model returned no structured output. Raw: {response.text[:500]}")
            return None
        return response.parsed.model_dump()
    except Exception as exc:
        print(f"[integration_risk] assessment failed: {exc}")
        return None
