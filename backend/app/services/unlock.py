"""
Phase 4 — Unlock Gate Service

Checks whether a user has met both unlock conditions:
  - entry_count >= 7
  - days since first_entry_at >= 7

When both pass for the first time, sets chat_unlocked = true on the profile.
This check runs server-side after every entry submission — never trusted from frontend.
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
