"""
Phase 4 — Complex Detection Service

Every 7 entries (entry_count % 7 == 0), reads the full symbol_edges table
for this user, sends it to Gemma for Jungian cluster detection, and rebuilds
the complexes table (DELETE existing rows, INSERT fresh ones).

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
    1. Fetch all symbol_edges for the user (ordered by weight DESC)
    2. Format as plain text list for the prompt
    3. Call Gemma — returns 3-5 named complexes as JSON
    4. Delete existing complexes for this user
    5. Insert fresh complex rows
    Returns the list of detected complexes.
    """
    edges_result = (
        db.table("symbol_edges")
        .select("symbol_a, symbol_b, weight")
        .eq("user_id", user_id)
        .order("weight", desc=True)
        .execute()
    )

    if not edges_result.data:
        return []

    edges = edges_result.data
    prompt = build_complex_detector_prompt(edges)

    response = _client.models.generate_content(
        model="gemma-4-31b-it",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=list[Complex],
            max_output_tokens=2000,
            temperature=0.3,
        ),
    )

    if response.parsed is None:
        print(f"[complexes] Model returned no structured output for user {user_id}")
        return []

    complexes: list[Complex] = response.parsed

    # DELETE + INSERT (clean recompute — no stale accumulation)
    db.table("complexes").delete().eq("user_id", user_id).execute()

    rows = [
        {
            "user_id": user_id,
            "name": c.name,
            "summary": c.summary,
            "symbols": c.symbols,
        }
        for c in complexes
    ]
    if rows:
        db.table("complexes").insert(rows).execute()

    return complexes
