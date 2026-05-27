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


def parse_and_map_integration_risk(raw_json_str: str) -> dict | None:
    try:
        data = json.loads(raw_json_str)
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        if not isinstance(data, dict):
            return None

        # Helper to parse flags
        def parse_flag(flag_data, shadow=False) -> dict:
            if not isinstance(flag_data, dict):
                return {"present": False, "severity": None, "evidence": None}
            present = flag_data.get("present", False)
            if isinstance(present, str):
                present = present.lower() == "true"
            severity = flag_data.get("severity")
            evidence = flag_data.get("evidence")
            res = {"present": present, "severity": severity, "evidence": evidence}
            if shadow:
                res["form"] = flag_data.get("form")
            return res

        res = {
            "spiritual_inflation": parse_flag(data.get("spiritual_inflation")),
            "ego_dissolution_without_regrounding": parse_flag(data.get("ego_dissolution_without_regrounding")),
            "shadow_bypassing": parse_flag(data.get("shadow_bypassing"), shadow=True),
            "premature_closure": parse_flag(data.get("premature_closure")),
            "integration_guidance": str(data.get("integration_guidance") or ""),
            "overall_risk_level": str(data.get("overall_risk_level") or "none").lower(),
        }
        if res["overall_risk_level"] not in ["none", "low", "moderate", "high"]:
            res["overall_risk_level"] = "none"
        return res
    except Exception as exc:
        print(f"[integration] failed to parse JSON: {exc}")
        return None


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
                max_output_tokens=800,
                temperature=0.2,
                http_options=types.HttpOptions(timeout=90000),
            ),
        )
        if not response.text:
            print("[integration_risk] model returned empty output")
            return None
        return parse_and_map_integration_risk(response.text)
    except Exception as exc:
        print(f"[integration_risk] assessment failed: {exc}")
        return None
