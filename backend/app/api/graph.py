"""
GET /graph — returns symbol_edges as D3-compatible {nodes[], edges[]} JSON.
Phase 3: wired into graph service.
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
    Returns the user's symbol co-occurrence network as:
      { nodes: [{ id, value }], edges: [{ source, target, value }] }

    - node.value  = total weight (sum of all edges touching that node)
    - edge.value  = co-occurrence count between two symbols
    """
    return await build_graph(user.id, db)
