"""
Phase 4 — Topology-Based Retrieval Service

The retrieval pipeline that makes the chat feature structurally aware:

  Step 1: Extract 1-3 seed symbols from the user's message (lightweight Gemma call)
  Step 2: Query symbol_edges for the top-5 symbols most connected to any seed
  Step 3: Collect all entry_ids from matching edges (deduplicated)
  Step 4: Fetch those entries (jungian_summary + created_at — not full raw_text)
  Step 5: Fetch all complexes for the user

Fallback: if topology retrieval returns < 3 entries, supplement with the
most recent entries up to a total of 5. Never return zero context.
"""
from google import genai
from google.genai import types

from app.config import settings
from app.prompts.seed_extractor import build_seed_extractor_prompt

_client = genai.Client(api_key=settings.gemini_api_key)

MIN_ENTRIES = 3
MAX_ENTRIES = 5


async def get_topology_context(user_id: str, user_message: str, db) -> dict:
    """
    Returns { retrieved_entries: [...], complexes: [...] }
    ready to be injected into the persona prompt.
    """
    # Step 1: Extract seed symbols from user message
    seed_symbols = await _extract_seeds(user_message, user_id, db)

    # Step 2 & 3: Find connected entries via topology
    entry_ids = await _find_connected_entry_ids(user_id, seed_symbols, db)

    # Step 4: Fetch those entries
    retrieved_entries = await _fetch_entries(user_id, entry_ids, db)

    # Fallback: supplement with recent entries if topology returned too few
    if len(retrieved_entries) < MIN_ENTRIES:
        retrieved_entries = await _supplement_with_recent(
            user_id, retrieved_entries, MAX_ENTRIES, db
        )

    # Step 5: Fetch complexes (full schema for persona prompt annotations)
    complexes_result = (
        db.table("complexes")
        .select("name, summary, symbols, projection_status, golden_shadow, golden_shadow_owned, individuation_note")
        .eq("user_id", user_id)
        .order("computed_at", desc=True)
        .execute()
    )

    return {
        "retrieved_entries": retrieved_entries,
        "complexes": complexes_result.data or [],
    }


async def _extract_seeds(user_message: str, user_id: str, db) -> list[str]:
    """Fast Gemma call — returns 1-3 seed symbol strings."""
    # Fetch known symbols for this user to help the model match
    edges = (
        db.table("symbol_edges")
        .select("symbol_a, symbol_b")
        .eq("user_id", user_id)
        .limit(100)
        .execute()
    )
    known_symbols = set()
    for row in edges.data or []:
        known_symbols.add(row["symbol_a"])
        known_symbols.add(row["symbol_b"])

    prompt = build_seed_extractor_prompt(user_message, list(known_symbols))

    try:
        response = await _client.aio.models.generate_content(
            model="gemma-4-26b-a4b-it",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=list[str],
                max_output_tokens=100,
                temperature=0.1,
            ),
        )
        return response.parsed or []
    except Exception as exc:
        print(f"[retrieval] seed extraction failed: {exc} — falling back to word split")
        # Fallback: match words against known symbols
        words = user_message.lower().split()
        return [w for w in words if w in known_symbols][:3]


async def _find_connected_entry_ids(
    user_id: str, seeds: list[str], db
) -> list[str]:
    """For each seed, find top-5 neighbours by weight; collect entry_ids."""
    if not seeds:
        return []

    all_entry_ids: set[str] = set()

    for seed in seeds:
        # Find edges where this symbol appears (either position)
        result = (
            db.table("symbol_edges")
            .select("entry_ids")
            .eq("user_id", user_id)
            .or_(f"symbol_a.eq.{seed},symbol_b.eq.{seed}")
            .order("weight", desc=True)
            .limit(5)
            .execute()
        )
        for row in result.data or []:
            all_entry_ids.update(row.get("entry_ids") or [])

    return list(all_entry_ids)


async def _fetch_entries(user_id: str, entry_ids: list[str], db) -> list[dict]:
    if not entry_ids:
        return []
    result = (
        db.table("entries")
        .select("id, created_at, entry_type, analysis")
        .eq("user_id", user_id)
        .in_("id", entry_ids)
        .execute()
    )
    # Flatten analysis subfields to top level for persona prompt
    entries = []
    for row in result.data or []:
        analysis = row.get("analysis") or {}
        entries.append({
            "id": row["id"],
            "created_at": row["created_at"],
            "entry_type": row.get("entry_type", "entry"),
            "jungian_summary": analysis.get("jungian_summary", ""),
            "ego_strength_signal": analysis.get("ego_strength_signal"),
        })
    return entries


async def _supplement_with_recent(
    user_id: str,
    existing: list[dict],
    target: int,
    db,
) -> list[dict]:
    existing_ids = {e["id"] for e in existing}
    needed = target - len(existing)
    result = (
        db.table("entries")
        .select("id, created_at, entry_type, analysis")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(needed + len(existing_ids))
        .execute()
    )
    for row in result.data or []:
        if row["id"] not in existing_ids and len(existing) < target:
            analysis = row.get("analysis") or {}
            existing.append({
                "id": row["id"],
                "created_at": row["created_at"],
                "entry_type": row.get("entry_type", "entry"),
                "jungian_summary": analysis.get("jungian_summary", ""),
                "ego_strength_signal": analysis.get("ego_strength_signal"),
            })
    return existing
