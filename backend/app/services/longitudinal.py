"""
Longitudinal Analysis Service

Triggered by season_detector.should_trigger_longitudinal() — NOT a fixed entry count.
Reads full entry history, builds the longitudinal prompt, calls Gemma, stores result.

Stores the result in a 'longitudinal_analyses' table (created via migration below).
"""
import json

from google import genai
from google.genai import types

from app.config import settings
from app.prompts.longitudinal_analyzer import build_longitudinal_analyzer_prompt
from app.services.season_detector import should_trigger_longitudinal
from app.models import LongitudinalResult

_client = genai.Client(api_key=settings.gemini_api_key)


def parse_and_map_longitudinal(raw_json_str: str) -> dict | None:
    try:
        data = json.loads(raw_json_str)
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        if not isinstance(data, dict):
            return None
        return {
            "individuation_arc_summary": str(data.get("individuation_arc_summary") or data.get("individuation_summary") or ""),
            "dynamic_shadow_tracker": str(data.get("dynamic_shadow_tracker") or data.get("shadow_tracker") or ""),
            "transpersonal_integration_state": str(data.get("transpersonal_integration_state") or data.get("integration_state") or ""),
            "clinical_risk_advisory": data.get("clinical_risk_advisory") or data.get("risk_advisory"),
        }
    except Exception as exc:
        print(f"[longitudinal] failed to parse JSON: {exc}")
        return None


async def maybe_run_longitudinal(user_id: str, db) -> dict | None:
    """
    Checks season shift conditions, runs longitudinal analysis if triggered.
    Returns the analysis result dict or None if not triggered.
    Errors are silenced — longitudinal analysis must never fail an entry submission.
    """
    try:
        # Fetch all entries for this user with required fields
        entries_result = (
            db.table("entries")
            .select("id, created_at, entry_type, analysis")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        raw_entries = entries_result.data or []

        # Flatten analysis fields into top-level for season_detector
        entries = []
        for e in raw_entries:
            analysis = e.get("analysis") or {}
            entries.append({
                "created_at": e["created_at"],
                "entry_type": e["entry_type"],
                "ego_strength_signal": analysis.get("ego_strength_signal"),
                "lysis_assessment": analysis.get("lysis_assessment"),
                "themes": analysis.get("themes", []),
                "jungian_summary": analysis.get("jungian_summary", ""),
                "dominant_archetypes": [
                    a["name"] for a in analysis.get("archetypes", [])
                    if a.get("confidence", 0) >= 0.5
                ],
            })

        # Sort ASC for longitudinal (we fetched DESC above)
        entries = list(reversed(entries))

        # Fetch last analysis timestamp
        last_result = (
            db.table("longitudinal_analyses")
            .select("created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        last_analysis_at = None
        if last_result.data:
            last_analysis_at = last_result.data[0]["created_at"]

        # Check season shift conditions
        trigger = should_trigger_longitudinal(entries, last_analysis_at)
        if not trigger["should_trigger"]:
            return None

        # Build and run prompt
        prompt = build_longitudinal_analyzer_prompt(entries)
        if not prompt:
            return None

        response = await _client.aio.models.generate_content(
            model="gemma-4-26b-a4b-it",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=1500,
                temperature=0.3,
                http_options=types.HttpOptions(timeout=180000),
            ),
        )

        if not response.text:
            print("[longitudinal] model returned empty output")
            return None

        result = parse_and_map_longitudinal(response.text)
        if not result:
            return None

        # Store in longitudinal_analyses table
        db.table("longitudinal_analyses").insert({
            "user_id": user_id,
            "result": result,
            "season_signal": trigger["season_signal"],
            "trigger_reasons": trigger["reasons"],
        }).execute()

        return result

    except Exception as exc:
        print(f"[longitudinal] analysis failed for {user_id}: {exc}")
        return None
