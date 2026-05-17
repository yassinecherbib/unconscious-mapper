"""
Phase 3 — Graph Service

Reads symbol_edges for the current user and returns a D3-compatible
{ nodes[], edges[] } JSON object for the force-directed graph.

Node value = sum of all edge weights touching that node.
Edge value = co-occurrence weight between two symbols.
"""
from supabase import Client


async def build_graph(user_id: str, db: Client) -> dict:
    """
    Returns:
      {
        nodes: [{ id: str, value: int }],
        edges: [{ source: str, target: str, value: int }]
      }
    """
    result = (
        db.table("symbol_edges")
        .select("symbol_a, symbol_b, weight")
        .eq("user_id", user_id)
        .execute()
    )

    rows = result.data or []

    # Accumulate node values (total weight per symbol)
    node_values: dict[str, int] = {}
    edges = []

    for row in rows:
        sym_a = row["symbol_a"]
        sym_b = row["symbol_b"]
        w = row["weight"]

        node_values[sym_a] = node_values.get(sym_a, 0) + w
        node_values[sym_b] = node_values.get(sym_b, 0) + w
        edges.append({"source": sym_a, "target": sym_b, "value": w})

    nodes = [{"id": sym, "value": val} for sym, val in node_values.items()]

    return {"nodes": nodes, "edges": edges}
