"""
Phase 4 — Complex Detection Service

Triggered by season_detector (via longitudinal pipeline) OR every 7 entries as fallback.
Reads symbol_edges WITH affective data (avg_intensity, avg_valence, dominant_emotion)
and sends to Gemma for Jungian cluster detection with psychic-charge scoring.

Stale complex rows are never accumulated — each run is a clean recompute.
"""
import json
from google import genai
from google.genai import types

from app.config import settings
from app.models import Complex
from app.prompts.complex_detector import build_complex_detector_prompt

_client = genai.Client(api_key=settings.gemini_api_key)


def parse_and_map_complexes(raw_json_str: str) -> list[Complex]:
    try:
        data = json.loads(raw_json_str)
        if isinstance(data, dict):
            complexes_list = data.get("complexes") or data.get("clusters") or data.get("data")
            if isinstance(complexes_list, list):
                data = complexes_list
            else:
                data = [data]
        if not isinstance(data, list):
            data = []

        res = []
        for c in data:
            if isinstance(c, dict):
                name = c.get("name") or ""
                summary = c.get("summary") or ""
                symbols = c.get("symbols") or []
                if not isinstance(symbols, list):
                    symbols = []
                symbols = [str(s) for s in symbols]

                overdetermined_symbols = c.get("overdetermined_symbols") or []
                if not isinstance(overdetermined_symbols, list):
                    overdetermined_symbols = []
                overdetermined_symbols = [str(os) for os in overdetermined_symbols]

                affective_core = c.get("affective_core")
                projection_status = c.get("projection_status") or "ambiguous"
                golden_shadow = c.get("golden_shadow")
                if isinstance(golden_shadow, str):
                    golden_shadow = golden_shadow.lower() == "true"
                golden_shadow_owned = c.get("golden_shadow_owned")
                if isinstance(golden_shadow_owned, str):
                    golden_shadow_owned = golden_shadow_owned.lower() == "true"
                individuation_note = c.get("individuation_note")

                res.append(Complex(
                    name=name,
                    summary=summary,
                    symbols=symbols,
                    overdetermined_symbols=overdetermined_symbols,
                    affective_core=affective_core,
                    projection_status=projection_status,
                    golden_shadow=golden_shadow,
                    golden_shadow_owned=golden_shadow_owned,
                    individuation_note=individuation_note
                ))
        return res
    except Exception as exc:
        print(f"[complexes] failed to parse complexes JSON: {exc}")
        return []


async def detect_and_store_complexes(user_id: str, db) -> list[Complex]:
    """
    1. Fetch all symbol_edges for the user WITH affective data
    2. Compute avg_intensity and avg_valence by joining with entry emotion data
    3. Call Gemma — returns 3-5 named complexes as JSON (psychic-charge weighted)
    4. Delete existing complexes for this user
    5. Insert fresh complex rows with full schema
    Returns the list of detected complexes.
    """
    edges_result = (
        db.table("symbol_edges")
        .select("symbol_a, symbol_b, weight, avg_intensity, avg_valence, dominant_emotion")
        .eq("user_id", user_id)
        .order("weight", desc=True)
        .execute()
    )

    if not edges_result.data:
        return []

    edges = edges_result.data

    # Back-fill affective fields with defaults if columns don't exist yet
    for edge in edges:
        edge.setdefault("avg_intensity", 0.5)
        edge.setdefault("avg_valence", 0.0)
        edge.setdefault("dominant_emotion", "unknown")

    prompt = build_complex_detector_prompt(edges)

    try:
        response = await _client.aio.models.generate_content(
            model="gemma-4-26b-a4b-it",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=2000,
                temperature=0.3,
                http_options=types.HttpOptions(timeout=180000),
            ),
        )
    except Exception as exc:
        print(f"[complexes] LLM call failed for user {user_id}: {exc}")
        return []

    if not response.text:
        print(f"[complexes] Model returned empty output for user {user_id}")
        return []

    complexes = parse_and_map_complexes(response.text)

    # DELETE + INSERT (clean recompute)
    db.table("complexes").delete().eq("user_id", user_id).execute()

    rows = [
        {
            "user_id": user_id,
            "name": c.name,
            "summary": c.summary,
            "symbols": c.symbols,
            "overdetermined_symbols": c.overdetermined_symbols or [],
            "affective_core": c.affective_core,
            "projection_status": c.projection_status,
            "golden_shadow": c.golden_shadow,
            "golden_shadow_owned": c.golden_shadow_owned,
            "individuation_note": c.individuation_note,
        }
        for c in complexes
    ]
    if rows:
        db.table("complexes").insert(rows).execute()

    return complexes
