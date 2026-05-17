"""
Amplification Service — NEW FILE

Two functions:
  1. identify_symbols_to_amplify() — calls the model to pick 2-3 ambiguous symbols
     and generate questions for the user. Runs BEFORE the main extractor.

  2. save_personal_associations() — stores user answers in personal_symbol_associations table.
"""
from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import settings
from app.prompts.amplification import build_amplification_prompt
from app.services.analysis import GEMMA_MODEL

_client = genai.Client(api_key=settings.gemini_api_key)


class AmplificationItem(BaseModel):
    symbol: str
    question: str


class AmplificationResult(BaseModel):
    symbols_to_amplify: list[AmplificationItem]


async def identify_symbols_to_amplify(
    raw_text: str,
    entry_type: str,
    user_id: str,
    db,
) -> list[AmplificationItem]:
    """
    Step 1 of the amplification loop:
    Fetch user's known personal associations, run the amplification prompt,
    return 0-3 questions for the frontend to present.
    """
    # Fetch existing personal associations
    assoc_result = (
        db.table("personal_symbol_associations")
        .select("symbol, personal_meaning")
        .eq("user_id", user_id)
        .execute()
    )
    known: dict[str, str] = {
        row["symbol"]: row["personal_meaning"]
        for row in (assoc_result.data or [])
    }

    prompt = build_amplification_prompt(
        raw_text=raw_text,
        entry_type=entry_type,
        known_personal_symbols=known,
    )

    try:
        response = _client.models.generate_content(
            model=GEMMA_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AmplificationResult,
                max_output_tokens=300,
                temperature=0.2,
            ),
        )

        if response.parsed is None:
            return []

        return response.parsed.symbols_to_amplify

    except Exception as exc:
        print(f"[amplification] identify failed: {exc}")
        return []


async def save_personal_associations(
    user_id: str,
    associations: list[dict],  # [{"symbol": str, "meaning": str}]
    db,
) -> None:
    """
    Step 2 of the amplification loop:
    Persist user's answers to personal_symbol_associations.
    Uses upsert so existing meanings are updated if the same symbol is revisited.
    """
    if not associations:
        return

    rows = [
        {
            "user_id": user_id,
            "symbol": a["symbol"],
            "personal_meaning": a["meaning"],
        }
        for a in associations
        if a.get("symbol") and a.get("meaning")
    ]

    if rows:
        db.table("personal_symbol_associations").upsert(
            rows,
            on_conflict="user_id, symbol",
        ).execute()


async def build_amplification_context(user_id: str, db) -> str:
    """
    Builds a personal associations context string to inject into the extractor.
    Called after save_personal_associations (or independently for re-analysis).
    """
    from app.prompts.amplification import build_extractor_with_amplification

    assoc_result = (
        db.table("personal_symbol_associations")
        .select("symbol, personal_meaning")
        .eq("user_id", user_id)
        .execute()
    )

    known = {
        row["symbol"]: row["personal_meaning"]
        for row in (assoc_result.data or [])
    }

    return build_extractor_with_amplification(known)
