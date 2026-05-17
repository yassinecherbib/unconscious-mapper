"""
POST /entries          — create entry + full Jungian pipeline
POST /entries/amplify  — identify ambiguous symbols BEFORE submission (pre-analysis step)
GET  /entries          — list all entries
GET  /entries/unlock/progress — unlock gate progress
GET  /entries/{id}     — single entry with full analysis

Full POST /entries pipeline (updated):
  1.  Rate-limit check
  2.  Insert raw entry (analysis = null)
  3.  Fetch last 5 entries as previous context summary
  4.  Build amplification context (personal associations from DB)
  5.  Run Gemma extraction with amplification context → AnalysisResult
  6.  Update entry with analysis JSONB
  7.  Upsert symbol edges WITH affective data
  8.  Increment profile entry_count; set first_entry_at if first
  9.  Unlock check
 10.  Integration risk check (psychedelic / high-intensity meditation only)
 11.  Complex detection every 7 entries OR if season shift detected
 12.  Longitudinal season-shift trigger check
 13.  Return full entry with analysis + integration_guidance if present
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import Client

from app.dependencies import check_rate_limit, get_current_user, get_db_client
from app.services.analysis import run_extraction
from app.services.edges import upsert_edges_with_affect
from app.services.unlock import check_and_unlock, check_longitudinal_trigger

router = APIRouter()


class EntryCreate(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=5000)
    entry_type: str = Field(..., pattern="^(dream|psychedelic|meditation)$")


class AmplifyRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=5000)
    entry_type: str = Field(..., pattern="^(dream|psychedelic|meditation)$")


def _build_previous_summary(entries: list[dict]) -> str:
    lines = []
    for e in entries:
        analysis = e.get("analysis")
        if isinstance(analysis, dict) and "jungian_summary" in analysis:
            lines.append(f"Entry {e['id']}: {analysis['jungian_summary']}")
    return "\n".join(lines) if lines else ""


# ── /amplify — pre-submission amplification step ─────────────────────────────

@router.post("/amplify")
async def amplify_entry(
    body: AmplifyRequest,
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """
    Identifies 0-3 psychically ambiguous symbols and returns questions
    for the user to answer before final submission. Frontend shows these
    as a 'Dig Deeper' dialog — user answers are POSTed to /entries with
    the main submission.
    """
    from app.services.amplification import identify_symbols_to_amplify

    items = await identify_symbols_to_amplify(
        raw_text=body.raw_text,
        entry_type=body.entry_type,
        user_id=user.id,
        db=db,
    )
    return {"symbols_to_amplify": [i.model_dump() for i in items]}


# ── POST /entries — full pipeline ─────────────────────────────────────────────

class EntryCreateWithAssociations(EntryCreate):
    personal_associations: list[dict] | None = None
    # Each dict: {"symbol": str, "meaning": str}


@router.post("", status_code=201)
async def create_entry(
    body: EntryCreateWithAssociations,
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """Full pipeline: amplification context → extraction → edges → unlock → risk → arc."""
    check_rate_limit(user.id)

    # ── Step 1: Save any personal associations provided by the user ──
    if body.personal_associations:
        from app.services.amplification import save_personal_associations
        await save_personal_associations(user.id, body.personal_associations, db)

    # ── Step 2: Insert raw entry ──
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

    # ── Step 3: Fetch last 5 entries for previous context ──
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

    # ── Step 4: Build amplification context (personal associations from DB) ──
    from app.services.amplification import build_amplification_context
    personal_assoc_context = await build_amplification_context(user.id, db)

    # ── Step 5: AI Extraction ──
    analysis_dict: dict | None = None
    symbol_names: list[str] = []
    emotions: list[dict] = []
    ego_score: int | None = None
    jungian_summary: str = ""

    try:
        result = await run_extraction(
            raw_text=body.raw_text,
            entry_type=body.entry_type,
            previous_entries_summary=previous_summary,
            personal_associations=personal_assoc_context,
        )
        analysis_dict = result.model_dump()
        symbol_names = [s.name for s in result.symbols]
        emotions = [e.model_dump() for e in result.emotions]
        ego_score = result.ego_strength_signal.score if result.ego_strength_signal else None
        jungian_summary = result.jungian_summary
    except Exception as exc:
        print(f"[entries] extraction failed for {entry_id}: {exc}")
        analysis_dict = {"error": "parse_failed"}

    # ── Step 6: Persist analysis ──
    db.table("entries").update({"analysis": analysis_dict}).eq("id", entry_id).execute()
    entry["analysis"] = analysis_dict

    extraction_ok = not analysis_dict.get("error")

    # ── Step 7: Upsert symbol edges WITH affective data ──
    if symbol_names and extraction_ok:
        await upsert_edges_with_affect(
            user_id=user.id,
            entry_id=entry_id,
            symbol_names=symbol_names,
            emotions=emotions,
            db=db,
        )

    # ── Step 8: Update profile counters ──
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
        if not profile["first_entry_at"]:
            update_payload["first_entry_at"] = datetime.now(timezone.utc).isoformat()
        db.table("profiles").update(update_payload).eq("id", user.id).execute()

    # ── Step 9: Unlock check ──
    try:
        await check_and_unlock(user.id, db)
    except Exception as exc:
        print(f"[entries] unlock check failed: {exc}")

    # ── Step 10: Integration risk assessment ──
    integration_guidance: str | None = None
    if extraction_ok:
        from app.services.integration_risk import assess_integration_risk, should_assess_risk
        if should_assess_risk(body.entry_type, ego_score):
            try:
                risk_result = await assess_integration_risk(
                    raw_text=body.raw_text,
                    entry_type=body.entry_type,
                    jungian_summary=jungian_summary,
                    ego_strength_signal=ego_score or 0,
                    user_id=user.id,
                    entry_id=entry_id,
                    db=db,
                )
                if risk_result:
                    integration_guidance = risk_result.integration_guidance
            except Exception as exc:
                print(f"[entries] integration risk failed: {exc}")

    # ── Step 11: Complex detection (every 7 entries OR on season shift) ──
    season_triggered = False
    if extraction_ok:
        try:
            season_triggered = await check_longitudinal_trigger(user.id, db)
        except Exception as exc:
            print(f"[entries] longitudinal trigger failed: {exc}")

        if new_count % 7 == 0 or season_triggered:
            try:
                from app.services.complexes import detect_and_store_complexes
                await detect_and_store_complexes(user.id, db, force=season_triggered)
            except Exception as exc:
                print(f"[entries] complex detection failed: {exc}")

    # ── Step 12: Build response ──
    response = dict(entry)
    if integration_guidance:
        response["integration_guidance"] = integration_guidance

    return response


# ── GET /entries ──────────────────────────────────────────────────────────────

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
    """Returns unlock gate progress. Must appear before /{entry_id}."""
    from app.services.unlock import get_unlock_progress
    return await get_unlock_progress(user.id, db)


@router.get("/{entry_id}")
async def get_entry(
    entry_id: str,
    user=Depends(get_current_user),
    db: Client = Depends(get_db_client),
):
    """Return a single entry with full analysis. 404 if not found."""
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
