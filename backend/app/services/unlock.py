"""
Phase 4 — Unlock Gate Service

Checks whether a user has met both unlock conditions:
  - entry_count >= 7
  - days since first_entry_at >= 7

When both pass for the first time, sets chat_unlocked = true on the profile.
This check runs server-side after every entry submission — never trusted from frontend.

NEW: check_longitudinal_trigger() — decides whether to run season-based
longitudinal arc analysis and triggers it as a background task.
"""
from datetime import datetime, timezone

from supabase import Client


async def check_and_unlock(user_id: str, db: Client) -> bool:
    """
    Returns True if chat was just unlocked or was already unlocked.
    Returns False if conditions are not yet met.
    """
    result = (
        db.table("profiles")
        .select("entry_count, first_entry_at, chat_unlocked")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )

    if not result.data:
        return False

    profile = result.data

    # Already unlocked — nothing to do
    if profile.get("chat_unlocked"):
        return True

    entry_count: int = profile.get("entry_count", 0)
    first_entry_at_str: str | None = profile.get("first_entry_at")

    if entry_count < 7 or not first_entry_at_str:
        return False

    first_entry_at = datetime.fromisoformat(first_entry_at_str)
    days_elapsed = (datetime.now(timezone.utc) - first_entry_at).days

    if days_elapsed < 7:
        return False

    # Both conditions met — unlock permanently
    db.table("profiles").update({"chat_unlocked": True}).eq("id", user_id).execute()
    return True


async def get_unlock_progress(user_id: str, db: Client) -> dict:
    """
    Returns unlock progress for the LockedOverlay UI component.
    Example: { entry_count: 5, days_elapsed: 3, unlocked: false }
    """
    result = (
        db.table("profiles")
        .select("entry_count, first_entry_at, chat_unlocked")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )

    if not result.data:
        return {"entry_count": 0, "days_elapsed": 0, "unlocked": False}

    profile = result.data
    days_elapsed = 0
    if profile.get("first_entry_at"):
        first = datetime.fromisoformat(profile["first_entry_at"])
        days_elapsed = (datetime.now(timezone.utc) - first).days

    return {
        "entry_count": profile.get("entry_count", 0),
        "days_elapsed": days_elapsed,
        "unlocked": profile.get("chat_unlocked", False),
    }


async def check_longitudinal_trigger(user_id: str, db: Client) -> bool:
    """
    Checks whether a psychic season shift has occurred and triggers
    longitudinal arc analysis if so. Errors are silenced.

    Returns True if analysis was triggered, False otherwise.
    """
    from app.services.season_detector import should_trigger_longitudinal
    from app.services.longitudinal import run_longitudinal_analysis

    try:
        # Fetch profile for last_longitudinal_at
        profile_result = (
            db.table("profiles")
            .select("last_longitudinal_at, arc_season_signal")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        last_at = None
        if profile_result.data:
            last_at = profile_result.data.get("last_longitudinal_at")

        # Fetch all entries with analysis metadata
        entries_result = (
            db.table("entries")
            .select("id, created_at, entry_type, analysis")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )

        entries = []
        for e in (entries_result.data or []):
            analysis = e.get("analysis") or {}
            ego = analysis.get("ego_strength_signal")
            lysis = analysis.get("lysis_assessment")
            entries.append({
                "created_at": e["created_at"],
                "entry_type": e["entry_type"],
                "ego_strength_signal": ego.get("score") if isinstance(ego, dict) else None,
                "lysis_assessment": lysis.get("result") if isinstance(lysis, dict) else None,
                "dominant_archetypes": [
                    a["name"]
                    for a in (analysis.get("archetypes") or [])
                    if a.get("confidence", 0) >= 0.6
                ],
            })

        decision = should_trigger_longitudinal(entries, last_at)

        if not decision["should_trigger"]:
            return False

        # Update arc_season_signal badge on profile before analysis
        if decision.get("season_signal"):
            db.table("profiles").update(
                {"arc_season_signal": decision["season_signal"]}
            ).eq("id", user_id).execute()

        # Run the full longitudinal analysis
        await run_longitudinal_analysis(user_id, db)
        return True

    except Exception as exc:
        print(f"[unlock] longitudinal trigger failed for {user_id}: {exc}")
        return False
