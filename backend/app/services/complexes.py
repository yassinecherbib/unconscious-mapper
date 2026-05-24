"""
Phase 4 — Complex Detection Service

Triggered by season_detector (via longitudinal pipeline) OR every 7 entries as fallback.
Reads symbol_edges WITH affective data (avg_intensity, avg_valence, dominant_emotion)
and sends to Gemma for Jungian cluster detection with psychic-charge scoring.

Stale complex rows are never accumulated — each run is a clean recompute.
"""
from google import genai
from google.genai import types

from app.config import settings
from app.models import Complex
from app.prompts.complex_detector import build_complex_detector_prompt

_client = genai.Client(api_key=settings.gemini_api_key)


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
                response_schema=list[Complex],
                max_output_tokens=2000,
                temperature=0.3,
            ),
        )
    except Exception as exc:
        print(f"[complexes] LLM call failed for user {user_id}: {exc}")
        return []

    if response.parsed is None:
        print(f"[complexes] Model returned no structured output for user {user_id}")
        return []

    complexes: list[Complex] = response.parsed

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
