"""
POST /entries       — create a new journal entry + amplification questions
POST /entries/amplify — submit personal association answers, run full extraction
GET  /entries       — list all entries for the authenticated user
GET  /entries/{id}  — retrieve a single entry with full analysis

Full pipeline (POST /entries):
  1. Rate-limit check
  2. Insert raw entry (analysis = null)
  3. Run amplification → return questions to frontend immediately
     (frontend shows questions; user can skip)

POST /entries/amplify completes the pipeline:
  4. Fetch last 5 entries for previous context summary
  5. Format personal associations block (if user answered)
  6. Call Gemma extraction service → validated AnalysisResult
  7. Update entry with analysis JSONB
  8. Upsert symbol co-occurrence edges
  9. Run integration risk check (psychedelic / low-ego meditation)
 10. Increment profile entry_count; set first_entry_at if first entry
 11. Run unlock check
 12. Every 7 entries → run complex detection
 13. Check season shift → maybe run longitudinal analysis
 14. Return full entry with analysis
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import Client

from app.dependencies import check_rate_limit, get_current_user, get_db_client
from app.services.analysis import run_extraction
from app.services.edges import upsert_edges
from app.services.unlock import check_and_unlock
from app.services.amplification import get_amplification_questions, format_personal_associations
from app.services.integration import run_integration_risk
from app.services.complexes import detect_and_store_complexes
from app.services.longitudinal import maybe_run_longitudinal


router = APIRouter()


class EntryCreate(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=5000)
    entry_type: str = Field(..., pattern="^(dream|psychedelic|meditation)$")


class AmplifyBody(BaseModel):
    entry_id: str
    personal_associations: dict[str, str] = Field(default_factory=dict)
    # answers: {symbol: user's answer} — empty dict = user skipped


def _build_previous_summary(entries: list[dict]) -> str:
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
    Step 1 of 2: Store entry, run amplification pre-analysis.
    Returns entry_id + amplification questions (may be empty if no ambiguous symbols).
    Frontend shows the questions; user answers or skips, then calls POST /entries/amplify.
    """
    check_rate_limit(user.id)

    # Insert raw entry
    insert_result = (
        db.table("entries")
        .insert({
            "user_id": user.id,
            "raw_text": body.raw_text,
            "entry_type": body.entry_type,
            "analysis": None,
        })
        .execute()
    )
    if not insert_result.data:
        raise HTTPException(status_code=500, detail="Failed to create entry")

    entry = insert_result.data[0]
    entry_id: str = entry["id"]

    # Run amplification — get questions to surface to the user
    questions = []
    try:
        # Fetch known personal symbols from prior amplification sessions
        known_result = (
            db.table("personal_symbols")
            .select("symbol, meaning")
            .eq("user_id", user.id)
            .execute()
        )
        known = {row["symbol"]: row["meaning"] for row in known_result.data or []}
        questions = await get_amplification_questions(body.raw_text, body.entry_type, known)
    except Exception as exc:
        print(f"[entries] amplification questions failed for {entry_id}: {exc}")

    return {
        "entry_id": entry_id,
        "amplification_questions": questions,
    }


@router.post("/amplify", status_code=200)
async def amplify_entry(
    body: AmplifyBody,
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """
    Step 2 of 2: Run full extraction with optional personal associations.
    This completes the full pipeline and returns the entry with analysis.
    """
    # Fetch the raw entry
    entry_result = (
        db.table("entries")
        .select("id, raw_text, entry_type, analysis")
        .eq("id", body.entry_id)
        .eq("user_id", user.id)
        .maybe_single()
        .execute()
    )
    if not entry_result.data:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry = entry_result.data
    entry_id = entry["id"]
    raw_text = entry["raw_text"]
    entry_type = entry["entry_type"]

    # Fetch previous context
    prev_result = (
        db.table("entries")
        .select("id, analysis")
        .eq("user_id", user.id)
        .neq("id", entry_id)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    previous_summary = _build_previous_summary(prev_result.data or [])

    # Format personal associations block
    personal_associations_block = ""
    if body.personal_associations:
        personal_associations_block = format_personal_associations(body.personal_associations)

        # Persist new personal symbol definitions
        try:
            rows = [
                {"user_id": user.id, "symbol": sym, "meaning": meaning}
                for sym, meaning in body.personal_associations.items()
            ]
            if rows:
                upsert_res = db.table("personal_symbols").upsert(rows, on_conflict="user_id,symbol").execute()
                if not upsert_res.data:
                    print(f"[entries] personal_symbols upsert returned no data for user {user.id}")
        except Exception as exc:
            print(f"[entries] personal_symbols upsert failed: {exc}")

    # ── Main extraction ──
    analysis_dict: dict | None = None
    symbol_names: list[str] = []

    try:
        result = await run_extraction(
            raw_text=raw_text,
            entry_type=entry_type,
            previous_entries_summary=previous_summary,
            personal_associations=personal_associations_block,
        )
        analysis_dict = result.model_dump()
        symbol_names = [s.name for s in result.symbols]
    except Exception as exc:
        print(f"[entries] extraction failed for {entry_id}: {exc}")
        analysis_dict = {"error": "parse_failed"}

    # ── Integration risk check ──
    if analysis_dict and not analysis_dict.get("error"):
        try:
            risk = await run_integration_risk(
                raw_text=raw_text,
                entry_type=entry_type,
                jungian_summary=analysis_dict.get("jungian_summary", ""),
                ego_strength_signal=analysis_dict.get("ego_strength_signal"),
                user_id=user.id,
                db=db,
            )
            if risk:
                analysis_dict["integration_risk"] = risk
        except Exception as exc:
            print(f"[entries] integration risk failed for {entry_id}: {exc}")

    # ── Store analysis ──
    update_res = db.table("entries").update({"analysis": analysis_dict}).eq("id", entry_id).execute()
    if not update_res.data:
        raise HTTPException(status_code=500, detail="Failed to store analysis in database")
    entry["analysis"] = analysis_dict

    # ── Upsert symbol edges ──
    if symbol_names and not analysis_dict.get("error"):
        await upsert_edges(
            user_id=user.id, 
            entry_id=entry_id, 
            symbol_names=symbol_names, 
            emotions=analysis_dict.get("emotions", []),
            db=db
        )

    # ── Update profile counters atomically ──
    rpc_res = db.rpc("increment_profile_entry_count", {"p_user_id": user.id}).execute()
    if not rpc_res.data:
        raise HTTPException(status_code=500, detail="Failed to update user profile entry count")
    
    profile_data = rpc_res.data
    if isinstance(profile_data, list) and len(profile_data) > 0:
        profile_data = profile_data[0]
        
    if isinstance(profile_data, dict):
        new_count = profile_data.get("entry_count", 1)
    else:
        new_count = 1

    # ── Unlock check ──
    try:
        await check_and_unlock(user.id, db)
    except Exception as exc:
        print(f"[entries] unlock check failed: {exc}")

    # ── Complex detection every 7 entries ──
    if new_count % 7 == 0 and not analysis_dict.get("error"):
        try:
            await detect_and_store_complexes(user.id, db)
        except Exception as exc:
            print(f"[entries] complex detection failed at count {new_count}: {exc}")

    # ── Season-triggered longitudinal analysis ──
    if not analysis_dict.get("error"):
        try:
            await maybe_run_longitudinal(user.id, db)
        except Exception as exc:
            print(f"[entries] longitudinal check failed: {exc}")

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
    """Returns current unlock gate progress for the LockedOverlay UI."""
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
