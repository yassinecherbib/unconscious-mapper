"""
Phase 3 — Graph Service (updated for affective data)

Now returns affective edge fields: avg_intensity, avg_valence, dominant_emotion.
These are used by the frontend D3 graph to colour/size edges by emotional charge.
"""
from supabase import Client


async def build_graph(user_id: str, db: Client) -> dict:
    """
    Returns:
      {
        nodes: [{ id: str, value: int, avg_intensity: float }],
        edges: [{ source, target, value, avg_intensity, avg_valence, dominant_emotion }]
      }
    """
    result = (
        db.table("symbol_edges")
        .select("symbol_a, symbol_b, weight, avg_intensity, avg_valence, dominant_emotion")
        .eq("user_id", user_id)
        .execute()
    )

    rows = result.data or []

    # Accumulate node values and intensity-weighted totals
    node_values: dict[str, int] = {}
    node_intensity: dict[str, float] = {}
    node_counts: dict[str, int] = {}
    edges = []

    for row in rows:
        sym_a = row["symbol_a"]
        sym_b = row["symbol_b"]
        w = row["weight"]
        intensity = row.get("avg_intensity") or 0.0
        valence = row.get("avg_valence") or 0.0
        emotion = row.get("dominant_emotion") or ""

        node_values[sym_a] = node_values.get(sym_a, 0) + w
        node_values[sym_b] = node_values.get(sym_b, 0) + w

        # Track avg_intensity per node (for glow/size on frontend)
        for sym in (sym_a, sym_b):
            node_intensity[sym] = node_intensity.get(sym, 0.0) + intensity
            node_counts[sym] = node_counts.get(sym, 0) + 1

        edges.append({
            "source": sym_a,
            "target": sym_b,
            "value": w,
            "avg_intensity": round(intensity, 3),
            "avg_valence": round(valence, 3),
            "dominant_emotion": emotion,
        })

    nodes = [
        {
            "id": sym,
            "value": val,
            "avg_intensity": round(
                node_intensity.get(sym, 0.0) / node_counts.get(sym, 1), 3
            ),
        }
        for sym, val in node_values.items()
    ]

    return {"nodes": nodes, "edges": edges}
