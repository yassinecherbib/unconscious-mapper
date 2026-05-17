"""
POST /entries  — create a new journal entry + run Jungian AI extraction (Phase 2)
GET  /entries  — list all entries for the authenticated user
GET  /entries/{id} — retrieve a single entry with full analysis

Phase 2 pipeline (POST /entries):
  1. Rate-limit check
  2. Insert raw entry (analysis = null initially)
  3. Fetch last 5 entries as previous context summary
  4. Call Gemma extraction service → validated AnalysisResult
  5. Update entry with analysis JSONB
  6. Upsert symbol co-occurrence edges into symbol_edges
  7. Increment profile entry_count; set first_entry_at if first entry
  8. Run unlock check (entry_count >= 7 AND days >= 7)
  9. If entry_count % 7 == 0 → run complex detection (async-ish, errors silenced)
 10. Return full entry with analysis
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import Client

from app.dependencies import check_rate_limit, get_current_user, get_db_client
from app.services.analysis import run_extraction
from app.services.edges import upsert_edges
from app.services.unlock import check_and_unlock

router = APIRouter()


class EntryCreate(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=5000)
    entry_type: str = Field(..., pattern="^(dream|psychedelic|meditation)$")


def _build_previous_summary(entries: list[dict]) -> str:
    """
    Build a short previous-context string from the last N entries.
    Only includes entries that have a completed analysis — skips errored/null ones.
    Format: 'Entry <uuid>: <jungian_summary>'
    """
    lines = []
    for e in entries:
        analysis = e.get("analysis")
        if isinstance(analysis, dict) and "jungian_summary" in analysis:
            lines.append(f"Entry {e['id']}: {analysis['jungian_summary']}")
    return "\n".join(lines) if lines else ""


@router.post("", status_code=201)
async def create_entry(
    body: EntryCreate,
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """
    Full Phase 2 pipeline: validate → store raw → extract with Gemma →
    store analysis → upsert edges → update counters → unlock check.
    Returns the complete entry object with analysis field populated.
    """
    check_rate_limit(user.id)

    # ── Step 1: Insert raw entry (analysis null until extraction completes) ──
    insert_result = (
        db.table("entries")
        .insert(
            {
                "user_id": user.id,
                "raw_text": body.raw_text,
                "entry_type": body.entry_type,
                "analysis": None,
            }
        )
        .execute()
    )

    if not insert_result.data:
        raise HTTPException(status_code=500, detail="Failed to create entry")

    entry = insert_result.data[0]
    entry_id: str = entry["id"]

    # ── Step 2: Fetch last 5 entries for previous context ──
    prev_result = (
        db.table("entries")
        .select("id, analysis")
        .eq("user_id", user.id)
        .neq("id", entry_id)           # exclude the one we just inserted
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    previous_summary = _build_previous_summary(prev_result.data or [])

    # ── Step 3: AI Extraction (Gemma 4) ──
    analysis_dict: dict | None = None
    symbol_names: list[str] = []

    try:
        result = await run_extraction(
            raw_text=body.raw_text,
            entry_type=body.entry_type,
            previous_entries_summary=previous_summary,
        )
        analysis_dict = result.model_dump()
        symbol_names = [s.name for s in result.symbols]
    except Exception as exc:
        # Extraction failure must NOT fail the entry — store error marker
        print(f"[entries] extraction failed for {entry_id}: {exc}")
        analysis_dict = {"error": "parse_failed"}

    # ── Step 4: Update entry with analysis JSONB ──
    db.table("entries").update({"analysis": analysis_dict}).eq("id", entry_id).execute()
    entry["analysis"] = analysis_dict

    # ── Step 5: Upsert symbol edges (only if extraction succeeded) ──
    if symbol_names and not analysis_dict.get("error"):
        await upsert_edges(
            user_id=user.id,
            entry_id=entry_id,
            symbol_names=symbol_names,
            db=db,
        )

    # ── Step 6: Update profile counters ──
    profile_result = (
        db.table("profiles")
        .select("entry_count, first_entry_at")
        .eq("id", user.id)
        .maybe_single()
        .execute()
    )

    new_count = 1
    if profile_result.data:
        profile = profile_result.data
        new_count = profile["entry_count"] + 1
        update_payload: dict = {"entry_count": new_count}
        if profile["first_entry_at"] is None:
            update_payload["first_entry_at"] = datetime.now(timezone.utc).isoformat()
        db.table("profiles").update(update_payload).eq("id", user.id).execute()

    # ── Step 7: Unlock check (sets chat_unlocked = true when both gates pass) ──
    try:
        await check_and_unlock(user.id, db)
    except Exception as exc:
        print(f"[entries] unlock check failed: {exc}")

    # ── Step 8: Complex detection every 7 entries ──
    if new_count % 7 == 0 and not analysis_dict.get("error"):
        try:
            from app.services.complexes import detect_and_store_complexes
            await detect_and_store_complexes(user.id, db)
        except Exception as exc:
            print(f"[entries] complex detection failed at count {new_count}: {exc}")

    return entry


@router.get("")
async def list_entries(
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """Return all entries for the current user, newest first."""
    result = (
        db.table("entries")
        .select("id, entry_type, raw_text, analysis, created_at")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


@router.get("/unlock/progress")
async def unlock_progress(
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """
    Returns current unlock gate progress for the LockedOverlay UI.
    Response: { entry_count: int, days_elapsed: int, unlocked: bool }
    This route MUST appear before /{entry_id} so FastAPI doesn't treat
    the literal string 'unlock' as a dynamic entry id.
    """
    from app.services.unlock import get_unlock_progress
    return await get_unlock_progress(user.id, db)


@router.get("/{entry_id}")
async def get_entry(
    entry_id: str,
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """Return a single entry with full analysis. 404 if not found or belongs to another user."""
    result = (
        db.table("entries")
        .select("*")
        .eq("id", entry_id)
        .eq("user_id", user.id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Entry not found")
    return result.data
