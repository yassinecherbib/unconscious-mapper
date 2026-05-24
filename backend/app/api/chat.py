"""
GET  /chat/stream   — topology-aware SSE subconscious chat (Active Imagination)
GET  /chat/longitudinal — fetch the latest longitudinal analysis for the user
"""
from fastapi import APIRouter, Depends, HTTPException
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
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """
    Active Imagination chat — streams the unconscious persona response via SSE.

    Steps:
      1. Gate check — verify chat_unlocked = true in profiles
      2. Extract seed symbols from user message (Gemma call, temp=0.0)
      3. Topology retrieval — find connected entries via symbol_edges
      4. Fetch user's complexes (pre-computed, with projection_status + golden_shadow)
      5. Assemble persona prompt: complexes → retrieved entries → user message
      6. Stream Gemma response (temp=0.75)

    Frontend: use fetch + ReadableStream, NOT EventSource.
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
        stream_chat_response(user.id, body.message, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/longitudinal")
async def get_longitudinal(
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """
    Returns the most recent longitudinal individuation arc analysis for the user.
    Includes the season_signal so the UI can contextually frame the output.
    Returns 404 if no analysis has been computed yet.
    """
    result = (
        db.table("longitudinal_analyses")
        .select("result, season_signal, trigger_reasons, created_at")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="No longitudinal analysis yet. Keep journaling — it runs when the psyche signals a season shift.",
        )
    return result.data
