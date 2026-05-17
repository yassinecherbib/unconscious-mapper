"""
GET /graph          — symbol co-occurrence graph with affective data
GET /graph/complexes — pre-computed Jungian complexes for this user
"""
from fastapi import APIRouter, Depends
from supabase import Client

from app.dependencies import get_current_user, get_db_client
from app.services.graph import build_graph

router = APIRouter()


@router.get("")
async def get_graph(
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """
    Returns symbol co-occurrence network with affective data:
      {
        nodes: [{ id, value, avg_intensity }],
        edges: [{ source, target, value, avg_intensity, avg_valence, dominant_emotion }]
      }
    """
    return await build_graph(user.id, db)


@router.get("/complexes")
async def get_complexes(
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """
    Returns all pre-computed symbolic complexes for this user including
    new affective fields: projection_status, golden_shadow, individuation_note, etc.
    """
    result = (
        db.table("complexes")
        .select(
            "id, name, summary, symbols, overdetermined_symbols, "
            "affective_core, projection_status, golden_shadow, "
            "golden_shadow_owned, individuation_note, created_at"
        )
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []
