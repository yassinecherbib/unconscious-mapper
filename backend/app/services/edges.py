"""
Phase 2 — Edge Building Service (updated for affective data)

After a successful analysis, iterates all symbol pairs in the entry
and upserts them into symbol_edges WITH affective data.

CRITICAL INVARIANT: symbol_a < symbol_b (alphabetical) ALWAYS.

New vs original:
  - Accepts emotions: list[dict] (from AnalysisResult.emotions)
  - Computes entry-level avg_intensity and avg_valence from emotions
  - Builds emotion_counts JSONB for dominant_emotion tracking
  - Calls updated RPC upsert_symbol_edge_with_affect
"""
from itertools import combinations

from supabase import Client


def _ordered_pair(a: str, b: str) -> tuple[str, str]:
    """Return the pair sorted alphabetically — enforces the unique constraint."""
    return tuple(sorted([a, b]))  # type: ignore[return-value]


def _compute_affective_stats(emotions: list[dict]) -> tuple[float, float, dict]:
    """
    Compute entry-level affective stats from emotions list.
    Returns: (avg_intensity, avg_valence, emotion_counts)
    emotion_counts = {emotion_name: count} for dominant_emotion tracking.
    """
    if not emotions:
        return 0.0, 0.0, {}

    total_intensity = sum(e.get("intensity", 0.0) for e in emotions)
    total_valence = sum(e.get("valence", 0.0) for e in emotions)
    n = len(emotions)

    avg_intensity = total_intensity / n
    avg_valence = total_valence / n

    emotion_counts: dict[str, int] = {}
    for e in emotions:
        name = e.get("name", "unknown")
        emotion_counts[name] = emotion_counts.get(name, 0) + 1

    return avg_intensity, avg_valence, emotion_counts


async def upsert_edges_with_affect(
    user_id: str,
    entry_id: str,
    symbol_names: list[str],
    emotions: list[dict],
    db: Client,
) -> None:
    """
    For a symbols list [A, B, C], generates pairs (A,B), (A,C), (B,C).
    Each pair is upserted with affective data using incremental running averages.

    Calls the upsert_symbol_edge_with_affect Supabase RPC function.
    """
    if len(symbol_names) < 2:
        return

    avg_intensity, avg_valence, emotion_counts = _compute_affective_stats(emotions)
    pairs = [_ordered_pair(a, b) for a, b in combinations(symbol_names, 2)]

    for sym_a, sym_b in pairs:
        try:
            db.rpc(
                "upsert_symbol_edge_with_affect",
                {
                    "p_user_id": user_id,
                    "p_symbol_a": sym_a,
                    "p_symbol_b": sym_b,
                    "p_entry_id": entry_id,
                    "p_avg_intensity": avg_intensity,
                    "p_avg_valence": avg_valence,
                    "p_emotion_counts": emotion_counts,
                },
            ).execute()
        except Exception as exc:
            print(f"[edges] affective upsert failed for ({sym_a}, {sym_b}): {exc}")
