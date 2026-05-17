"""
Phase 4 — Chat Service (updated)

Changes vs original:
  - Complexes fetch now includes all new fields (projection_status, golden_shadow, etc.)
  - Supports optional seed_entry_id to inject a specific entry into context
  - Model updated to gemma-4-27b-it
"""
from google import genai

from app.config import settings
from app.prompts.persona import build_persona_prompt
from app.services.analysis import GEMMA_MODEL
from app.services.retrieval import get_topology_context

_client = genai.Client(api_key=settings.gemini_api_key)


async def stream_chat_response(
    user_id: str,
    user_message: str,
    db,
    seed_entry_id: str | None = None,
):
    """
    AsyncGenerator yielding SSE-formatted data lines.
    Frontend reads with fetch + ReadableStream — NOT EventSource.

    Args:
        seed_entry_id: If provided, inject this entry's context first (used when
                       user opens chat from a specific journal entry).
    """
    # 1. Topology retrieval — seed → edges → entries + complexes
    context = await get_topology_context(
        user_id, user_message, db, seed_entry_id=seed_entry_id
    )

    # 2. Fetch complexes with ALL new fields for persona assembly
    complexes_result = (
        db.table("complexes")
        .select(
            "name, summary, symbols, overdetermined_symbols, affective_core, "
            "projection_status, golden_shadow, golden_shadow_owned, individuation_note"
        )
        .eq("user_id", user_id)
        .execute()
    )
    complexes = complexes_result.data or []

    # 3. Build persona prompt
    system_prompt, user_turn = build_persona_prompt(
        complexes=complexes,
        retrieved_entries=context["retrieved_entries"],
        user_message=user_message,
    )

    # 4. Stream Gemma response
    try:
        with _client.models.generate_content_stream(
            model=GEMMA_MODEL,
            contents=user_turn,
            config={
                "system_instruction": system_prompt,
                "max_output_tokens": 1000,
                "temperature": 0.7,
            },
        ) as stream:
            for chunk in stream:
                if chunk.text:
                    yield f"data: {chunk.text}\n\n"
    except Exception as exc:
        yield f"data: [ERROR] {str(exc)}\n\n"

    yield "data: [DONE]\n\n"
