"""
Integration Risk Assessment Service — NEW FILE

Runs ONLY on psychedelic and high-intensity meditation entries.
Detects spiritual inflation, ego dissolution, shadow bypassing, premature closure.
Only integration_guidance is exposed to the user. Risk flags stored internally.
"""
from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import settings
from app.prompts.integration_risk import build_integration_risk_prompt
from app.services.analysis import GEMMA_MODEL

_client = genai.Client(api_key=settings.gemini_api_key)

# Entry types and ego score threshold that trigger risk assessment
RISK_ENTRY_TYPES = {"psychedelic"}
HIGH_INTENSITY_MEDITATION_EGO_THRESHOLD = 5  # score >= 5 in meditation = high intensity


class RiskFlag(BaseModel):
    present: bool
    severity: str | None = None
    evidence: str | None = None


class ShadowBypassingFlag(RiskFlag):
    form: str | None = None


class IntegrationRiskResult(BaseModel):
    spiritual_inflation: RiskFlag
    ego_dissolution_without_regrounding: RiskFlag
    shadow_bypassing: ShadowBypassingFlag
    premature_closure: RiskFlag
    integration_guidance: str
    overall_risk_level: str


def should_assess_risk(entry_type: str, ego_score: int | None) -> bool:
    """Decide whether to run integration risk assessment for this entry."""
    if entry_type in RISK_ENTRY_TYPES:
        return True
    if entry_type == "meditation" and ego_score is not None and ego_score >= HIGH_INTENSITY_MEDITATION_EGO_THRESHOLD:
        return True
    return False


async def assess_integration_risk(
    raw_text: str,
    entry_type: str,
    jungian_summary: str,
    ego_strength_signal: int,
    user_id: str,
    entry_id: str,
    db,
) -> IntegrationRiskResult | None:
    """
    1. Fetch 3 most recent entry summaries for context
    2. Run integration risk prompt
    3. Store full result in entries.integration_risk JSONB
    4. Only integration_guidance is returned to the caller for exposure
    """
    # Fetch 3 recent entry summaries for context
    recent_result = (
        db.table("entries")
        .select("analysis")
        .eq("user_id", user_id)
        .neq("id", entry_id)
        .order("created_at", desc=True)
        .limit(3)
        .execute()
    )

    recent_summaries = []
    for e in (recent_result.data or []):
        analysis = e.get("analysis") or {}
        summary = analysis.get("jungian_summary")
        if summary:
            recent_summaries.append(summary)

    prompt = build_integration_risk_prompt(
        raw_text=raw_text,
        entry_type=entry_type,
        jungian_summary=jungian_summary,
        ego_strength_signal=ego_strength_signal,
        recent_entries_summaries=recent_summaries,
    )

    try:
        response = _client.models.generate_content(
            model=GEMMA_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=IntegrationRiskResult,
                max_output_tokens=800,
                temperature=0.1,
            ),
        )

        if response.parsed is None:
            return None

        result: IntegrationRiskResult = response.parsed

        # Persist full result to entries table
        db.table("entries").update(
            {"integration_risk": result.model_dump()}
        ).eq("id", entry_id).execute()

        return result

    except Exception as exc:
        print(f"[integration_risk] Assessment failed for entry {entry_id}: {exc}")
        return None
