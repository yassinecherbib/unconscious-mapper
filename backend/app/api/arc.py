"""
GET /arc       — returns the user's latest longitudinal arc analysis
GET /arc/status — returns season signal and last analysis timestamp

These endpoints power the /arc frontend page (ArcChart + EgoStrengthIndicator).
"""
from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.dependencies import get_current_user, get_db_client

router = APIRouter()


@router.get("")
async def get_arc(
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """
    Returns the most recent longitudinal individuation arc analysis.
    Stored as JSONB in profiles.latest_arc_analysis.

    Shape:
      {
        ego_trajectory: str,
        dominant_themes: [str],
        archetype_evolution: str,
        lysis_pattern: str,
        individuation_assessment: str,
        next_threshold: str,
        entry_count: int,
        ego_scores: [int]
      }

    Returns 404 if no analysis has been run yet (not enough entries
    or season shift not yet triggered).
    """
    result = (
        db.table("profiles")
        .select("latest_arc_analysis, last_longitudinal_at, arc_season_signal")
        .eq("id", user.id)
        .maybe_single()
        .execute()
    )

    if not result.data or not result.data.get("latest_arc_analysis"):
        raise HTTPException(
            status_code=404,
            detail="No arc analysis yet. Keep journaling — the arc builds over time.",
        )

    return {
        "analysis": result.data["latest_arc_analysis"],
        "last_updated": result.data.get("last_longitudinal_at"),
        "season_signal": result.data.get("arc_season_signal"),
    }


@router.get("/status")
async def get_arc_status(
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """
    Lightweight status check for the arc page header badge.
    Returns whether an arc exists and what the current season signal is.
    """
    result = (
        db.table("profiles")
        .select("last_longitudinal_at, arc_season_signal, entry_count")
        .eq("id", user.id)
        .maybe_single()
        .execute()
    )

    if not result.data:
        return {"has_arc": False, "season_signal": None, "entry_count": 0}

    return {
        "has_arc": result.data.get("last_longitudinal_at") is not None,
        "season_signal": result.data.get("arc_season_signal"),
        "last_updated": result.data.get("last_longitudinal_at"),
        "entry_count": result.data.get("entry_count", 0),
    }


@router.post("/trigger")
async def trigger_arc_manually(
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """
    Manual arc trigger — available only when entry_count >= 7.
    For testing / dev use. In production this is called automatically by
    the season detector.
    """
    profile_result = (
        db.table("profiles")
        .select("entry_count")
        .eq("id", user.id)
        .maybe_single()
        .execute()
    )

    count = (profile_result.data or {}).get("entry_count", 0)
    if count < 7:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 7 entries to generate arc. Current: {count}",
        )

    from app.services.longitudinal import run_longitudinal_analysis
    result = await run_longitudinal_analysis(user.id, db)

    if result is None:
        raise HTTPException(status_code=500, detail="Arc analysis failed.")

    return {"status": "triggered", "analysis": result.model_dump()}
