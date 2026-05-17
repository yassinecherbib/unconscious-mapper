"""
Longitudinal Arc Analysis Service — NEW FILE

Triggered by season_detector.py — NOT on every entry.
Fetches all entries' analysis metadata, calls the longitudinal analyzer prompt,
and stores the result in profiles.latest_arc_analysis JSONB.
"""
from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import settings
from app.prompts.longitudinal_analyzer import build_longitudinal_analyzer_prompt
from app.services.analysis import GEMMA_MODEL

_client = genai.Client(api_key=settings.gemini_api_key)


class ArcAnalysisResult(BaseModel):
    ego_trajectory: str
    dominant_themes: list[str]
    archetype_evolution: str
    lysis_pattern: str
    individuation_assessment: str
    next_threshold: str
    entry_count: int
    ego_scores: list[int]


async def run_longitudinal_analysis(user_id: str, db) -> ArcAnalysisResult | None:
    """
    1. Fetch all entries with their analysis JSONB (ego, lysis, archetypes)
    2. Build longitudinal prompt
    3. Call Gemma
    4. Store result in profiles.latest_arc_analysis
    5. Update profiles.last_longitudinal_at and arc_season_signal
    """
    entries_result = (
        db.table("entries")
        .select("id, created_at, entry_type, analysis")
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )

    if not entries_result.data:
        return None

    # Flatten analysis JSONB into per-entry dicts
    flattened = []
    for e in entries_result.data:
        analysis = e.get("analysis") or {}
        ego = analysis.get("ego_strength_signal")
        ego_score = ego.get("score") if isinstance(ego, dict) else None
        lysis = analysis.get("lysis_assessment")
        lysis_result = lysis.get("result") if isinstance(lysis, dict) else None
        archetypes = [
            a["name"]
            for a in (analysis.get("archetypes") or [])
            if a.get("confidence", 0) >= 0.6
        ]
        themes = analysis.get("themes") or []
        summary = analysis.get("jungian_summary") or ""

        flattened.append({
            "created_at": e["created_at"],
            "entry_type": e["entry_type"],
            "ego_strength_signal": ego_score,
            "lysis_assessment": lysis_result,
            "dominant_archetypes": archetypes,
            "themes": themes,
            "jungian_summary": summary,
        })

    prompt = build_longitudinal_analyzer_prompt(flattened)

    try:
        response = _client.models.generate_content(
            model=GEMMA_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ArcAnalysisResult,
                max_output_tokens=1000,
                temperature=0.25,
            ),
        )

        if response.parsed is None:
            print(f"[longitudinal] No structured output for user {user_id}")
            return None

        result: ArcAnalysisResult = response.parsed

        # Persist to profiles
        db.table("profiles").update(
            {
                "latest_arc_analysis": result.model_dump(),
                "last_longitudinal_at": "now()",
            }
        ).eq("id", user_id).execute()

        return result

    except Exception as exc:
        print(f"[longitudinal] Failed for user {user_id}: {exc}")
        return None
