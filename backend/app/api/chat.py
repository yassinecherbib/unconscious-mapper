"""
GET /chat/stream — topology-aware SSE subconscious chat.
Phase 4 will wire in: gate check → seed extraction → topology retrieval → streamed Gemma response.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from supabase import Client

from app.dependencies import get_current_user, get_db_client

router = APIRouter()


class ChatMessage(BaseModel):
    message: str


@router.post("/stream")
async def chat_stream(
    body: ChatMessage,
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """
    Phase 4 implementation:
      1. Gate check — verify chat_unlocked = true in profiles
      2. Extract seed symbols from user message (lightweight Gemma call)
      3. Topology retrieval — find top-5 connected symbols via symbol_edges
      4. Fetch relevant entries by entry_ids from matched edges
      5. Fetch user's complexes (pre-computed clusters)
      6. Assemble persona prompt: complexes → retrieved entries → user message
      7. Stream Gemma response via SSE

    Note: Use fetch + ReadableStream on the frontend — NOT EventSource.
    EventSource cannot send Authorization headers.
    """
    # Gate check stub — Phase 4 replaces this with real unlock verification
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

    # Stub — Phase 4 replaces with real streaming response
    async def stub_stream():
        yield "data: Chat feature coming in Phase 4.\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stub_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
