"""
POST /chat/stream — topology-aware SSE subconscious chat (fully implemented).

Supports optional seed_entry_id query param — when a user opens chat from
a specific journal entry, that entry's context is injected first.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from supabase import Client

from app.dependencies import get_current_user, get_db_client
from app.services.chat import stream_chat_response

router = APIRouter()


class ChatMessage(BaseModel):
    message: str


@router.post("/stream")
async def chat_stream(
    body: ChatMessage,
    seed_entry_id: str | None = Query(default=None),
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """
    Topology-aware subconscious chat stream.

    Query params:
      seed_entry_id — optional entry UUID to anchor the context retrieval
                      (used when user opens chat from a journal entry).

    Pipeline:
      1. Gate check — verify chat_unlocked on profile
      2. Topology retrieval with optional seed entry
      3. Complex assembly with all new fields
      4. Persona prompt construction
      5. Stream Gemma response via SSE

    IMPORTANT: Use fetch + ReadableStream on the frontend — NOT EventSource.
    EventSource cannot send Authorization headers.
    """
    # Gate check
    profile_result = (
        db.table("profiles")
        .select("chat_unlocked")
        .eq("id", user.id)
        .maybe_single()
        .execute()
    )
    if not profile_result.data or not profile_result.data.get("chat_unlocked"):
        raise HTTPException(
            status_code=403,
            detail="Chat not yet unlocked. Submit at least 7 entries across 7 days.",
        )

    return StreamingResponse(
        stream_chat_response(
            user_id=user.id,
            user_message=body.message,
            db=db,
            seed_entry_id=seed_entry_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
