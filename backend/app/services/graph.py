"""
Graph service for the symbol map.

The payload keeps the original D3-compatible nodes/edges shape while adding
typed symbol, archetype, co-occurrence, and attribution metadata.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from math import pow
from typing import Any

from supabase import Client


HALF_LIFE_DAYS = 30.0
LEGACY_INFERENCE_MULTIPLIER = 0.45


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _decay_for_date(created_at: str | None, now: datetime) -> float:
    parsed = _parse_datetime(created_at)
    if not parsed:
        return 1.0
    age_days = max((now - parsed.astimezone(timezone.utc)).total_seconds() / 86400, 0.0)
    return pow(0.5, age_days / HALF_LIFE_DAYS)


def _clean_name(value: Any) -> str:
    return str(value or "").strip()


def _analysis_symbols(analysis: dict) -> list[str]:
    symbols = analysis.get("symbols") or []
    if not isinstance(symbols, list):
        return []
    names: list[str] = []
    for item in symbols:
        if isinstance(item, dict):
            name = _clean_name(item.get("name") or item.get("symbol") or item.get("term"))
        else:
            name = _clean_name(item)
        if name:
            names.append(name)
    return names


def _analysis_archetypes(analysis: dict) -> list[dict]:
    archetypes = analysis.get("archetypes") or []
    if not isinstance(archetypes, list):
        return []
    cleaned: list[dict] = []
    for item in archetypes:
        if not isinstance(item, dict):
            continue
        name = _clean_name(item.get("name") or item.get("archetype"))
        if not name:
            continue
        try:
            confidence = float(item.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        cleaned.append({"name": name, "confidence": max(0.0, min(1.0, confidence))})
    return cleaned


def _explicit_attributions(analysis: dict) -> list[dict]:
    raw = (
        analysis.get("symbol_archetype_attributions")
        or analysis.get("symbol_archetypes")
        or analysis.get("archetype_attributions")
        or []
    )
    if not isinstance(raw, list):
        return []
    cleaned: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        symbol = _clean_name(item.get("symbol") or item.get("name") or item.get("source"))
        archetype = _clean_name(item.get("archetype") or item.get("target") or item.get("archetype_name"))
        if not symbol or not archetype:
            continue
        try:
            confidence = float(item.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        cleaned.append({
            "symbol": symbol,
            "archetype": archetype,
            "confidence": max(0.0, min(1.0, confidence)),
        })
    return cleaned


def _entry_attributions(entry: dict) -> list[dict]:
    analysis = entry.get("analysis")
    if not isinstance(analysis, dict) or analysis.get("error"):
        return []

    explicit = _explicit_attributions(analysis)
    if explicit:
        return explicit

    symbols = _analysis_symbols(analysis)
    archetypes = _analysis_archetypes(analysis)
    inferred: list[dict] = []
    for symbol in symbols:
        for archetype in archetypes:
            inferred.append({
                "symbol": symbol,
                "archetype": archetype["name"],
                "confidence": archetype["confidence"] * LEGACY_INFERENCE_MULTIPLIER,
            })
    return inferred


def _neighbor_components(symbol: str, adjacency: dict[str, set[str]]) -> int:
    neighbors = set(adjacency.get(symbol, set()))
    if len(neighbors) < 3:
        return len(neighbors)

    seen: set[str] = set()
    components = 0
    for start in neighbors:
        if start in seen:
            continue
        components += 1
        queue: deque[str] = deque([start])
        seen.add(start)
        while queue:
            current = queue.popleft()
            for nxt in adjacency.get(current, set()):
                if nxt == symbol or nxt not in neighbors or nxt in seen:
                    continue
                seen.add(nxt)
                queue.append(nxt)
    return components


def _mark_bridges(nodes: list[dict], edges: list[dict], dominant_by_symbol: dict[str, str | None]) -> None:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        adjacency[source].add(target)
        adjacency[target].add(source)

    for node in nodes:
        if node.get("type") != "symbol":
            continue
        symbol = node["id"]
        components = _neighbor_components(symbol, adjacency)
        neighbor_archetypes = {
            dominant_by_symbol.get(neighbor)
            for neighbor in adjacency.get(symbol, set())
            if dominant_by_symbol.get(neighbor)
        }
        bridge_score = max(components, len(neighbor_archetypes))
        node["bridge_score"] = bridge_score
        node["is_bridge"] = bridge_score >= 3


def build_graph_payload(edge_rows: list[dict], entry_rows: list[dict], now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    entries_by_id = {str(row.get("id")): row for row in entry_rows if row.get("id")}

    node_values: dict[str, int] = defaultdict(int)
    cooccurrence_edges: list[dict] = []

    for row in edge_rows:
        sym_a = _clean_name(row.get("symbol_a"))
        sym_b = _clean_name(row.get("symbol_b"))
        if not sym_a or not sym_b:
            continue
        weight = int(row.get("weight") or 0)
        entry_ids = row.get("entry_ids") or []
        if not isinstance(entry_ids, list):
            entry_ids = []

        decay_values = [
            _decay_for_date(entries_by_id.get(str(entry_id), {}).get("created_at"), now)
            for entry_id in entry_ids
        ]
        decayed_value = sum(decay_values) if decay_values else float(weight)
        recency_weight = decayed_value / max(weight, 1)

        node_values[sym_a] += weight
        node_values[sym_b] += weight
        cooccurrence_edges.append({
            "source": sym_a,
            "target": sym_b,
            "value": weight,
            "type": "cooccurrence",
            "decayed_value": round(decayed_value, 4),
            "recency_weight": round(recency_weight, 4),
        })

    attribution_stats: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: {"score": 0.0, "count": 0.0})
    for entry in entry_rows:
        for attribution in _entry_attributions(entry):
            symbol = attribution["symbol"]
            archetype = attribution["archetype"]
            if symbol not in node_values:
                continue
            attribution_stats[(symbol, archetype)]["score"] += attribution["confidence"]
            attribution_stats[(symbol, archetype)]["count"] += 1

    symbol_scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    archetype_values: dict[str, float] = defaultdict(float)
    attribution_edges: list[dict] = []
    for (symbol, archetype), stats in attribution_stats.items():
        score = stats["score"]
        count = max(stats["count"], 1.0)
        confidence = score / count
        symbol_scores[symbol][archetype] += score
        archetype_values[archetype] += score
        attribution_edges.append({
            "source": symbol,
            "target": f"archetype:{archetype}",
            "value": round(score, 4),
            "type": "attribution",
            "confidence": round(confidence, 4),
        })

    dominant_by_symbol: dict[str, str | None] = {}
    nodes: list[dict] = []
    for symbol, value in node_values.items():
        scores = symbol_scores.get(symbol, {})
        dominant = max(scores, key=scores.get) if scores else None
        dominant_by_symbol[symbol] = dominant
        confidence = 0.0
        if dominant:
            stats = attribution_stats[(symbol, dominant)]
            confidence = stats["score"] / max(stats["count"], 1.0)
        nodes.append({
            "id": symbol,
            "label": symbol,
            "type": "symbol",
            "value": value,
            "dominant_archetype": dominant,
            "dominant_confidence": round(confidence, 4),
            "is_bridge": False,
            "bridge_score": 0,
        })

    for archetype, value in archetype_values.items():
        nodes.append({
            "id": f"archetype:{archetype}",
            "label": archetype,
            "type": "archetype",
            "value": round(value, 4),
        })

    _mark_bridges(nodes, cooccurrence_edges, dominant_by_symbol)

    return {
        "nodes": nodes,
        "edges": cooccurrence_edges + attribution_edges,
        "meta": {
            "half_life_days": int(HALF_LIFE_DAYS),
            "legacy_inference_multiplier": LEGACY_INFERENCE_MULTIPLIER,
        },
    }


async def build_graph(user_id: str, db: Client) -> dict:
    edge_result = (
        db.table("symbol_edges")
        .select("symbol_a, symbol_b, weight, entry_ids")
        .eq("user_id", user_id)
        .execute()
    )
    edge_rows = edge_result.data or []

    entry_result = (
        db.table("entries")
        .select("id, analysis, created_at")
        .eq("user_id", user_id)
        .execute()
    )
    entry_rows = entry_result.data or []

    return build_graph_payload(edge_rows, entry_rows)
