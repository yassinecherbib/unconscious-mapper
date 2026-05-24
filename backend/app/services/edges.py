"""
Phase 2 — Edge Building Service

After a successful analysis, iterates all symbol pairs in the entry
and upserts them into symbol_edges.

CRITICAL INVARIANT: symbol_a < symbol_b (alphabetical) ALWAYS.
This is the only way the unique constraint (user_id, symbol_a, symbol_b)
correctly deduplicates (water, fire) and (fire, water) as the same edge.
"""
from itertools import combinations

from supabase import Client


def _ordered_pair(a: str, b: str) -> tuple[str, str]:
    """Return the pair sorted alphabetically — enforces the unique constraint."""
    return tuple(sorted([a, b]))  # type: ignore[return-value]


async def upsert_edges(
    user_id: str,
    entry_id: str,
    symbol_names: list[str],
    db: Client,
    emotions: list[dict] | None = None,
) -> None:
    """
    For a symbols list [A, B, C], generates pairs (A,B), (A,C), (B,C).
    Each pair is upserted: on conflict, weight += 1 and entry_id is appended.

    If fewer than 2 symbols exist, skips silently (no pairs can be formed).
    Errors during upsert are logged but do not fail the entry submission.
    """
    if db is None:
        raise ValueError("db client parameter is required")
    if emotions is None:
        emotions = []
    if len(symbol_names) < 2:
        return

    pairs = [_ordered_pair(a, b) for a, b in combinations(symbol_names, 2)]

    for sym_a, sym_b in pairs:
        try:
            # Supabase upsert: on conflict (user_id, symbol_a, symbol_b)
            # we need raw SQL for the increment + array_append behaviour.
            # We use rpc for the atomic upsert.
            db.rpc(
                "upsert_symbol_edge",
                {
                    "p_user_id": user_id,
                    "p_symbol_a": sym_a,
                    "p_symbol_b": sym_b,
                    "p_entry_id": entry_id,
                },
            ).execute()
        except Exception as exc:
            # Edge failure must NOT fail the entry — log and continue
            print(f"[edges] upsert failed for ({sym_a}, {sym_b}): {exc}")
