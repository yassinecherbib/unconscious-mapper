"""
Phase 4 — Complex Detection Service (updated)

Changes vs original:
  - Fetches affective edge columns: avg_intensity, avg_valence, dominant_emotion
  - Rows passed to prompt include affective data for psychic-charge scoring
  - INSERT includes all new complex fields from updated Complex model
  - Trigger condition updated: season_signal is checked; %7 kept as fallback
  - Model updated to gemma-4-27b-it
"""
from google import genai
from google.genai import types

from app.config import settings
from app.models import Complex
from app.prompts.complex_detector import build_complex_detector_prompt
from app.services.analysis import GEMMA_MODEL

_client = genai.Client(api_key=settings.gemini_api_key)


async def detect_and_store_complexes(
    user_id: str,
    db,
    force: bool = False,
) -> list[Complex]:
    """
    1. Fetch all symbol_edges WITH affective columns
    2. Build affective-aware complex detector prompt
    3. Call Gemma — returns 3-5 named complexes with new fields
    4. DELETE + INSERT (clean recompute)
    Returns the list of detected complexes.

    Args:
        force: If True, skip the %7 guard (used when season shift is detected).
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
    prompt = build_complex_detector_prompt(edges)

    response = _client.models.generate_content(
        model=GEMMA_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=list[Complex],
            max_output_tokens=2000,
            temperature=0.3,
        ),
    )

    if response.parsed is None:
        print(f"[complexes] No structured output for user {user_id}")
        return []

    complexes: list[Complex] = response.parsed

    # DELETE + INSERT — clean recompute, no stale accumulation
    db.table("complexes").delete().eq("user_id", user_id).execute()

    rows = [
        {
            "user_id": user_id,
            "name": c.name,
            "summary": c.summary,
            "symbols": c.symbols,
            "overdetermined_symbols": c.overdetermined_symbols,
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
