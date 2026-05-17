"""
Longitudinal Individuation Arc Analyzer — NEW FILE

See extracted/longitudinal_analyzer.py for full docstring and rationale.
Triggered by season_detector.py, not on a fixed entry count schedule.
"""
from typing import Optional


def build_longitudinal_analyzer_prompt(entries: list[dict]) -> str:
    if not entries:
        return ""

    entry_lines = []
    for i, e in enumerate(entries, 1):
        date = e.get("created_at", "")[:10]
        etype = e.get("entry_type", "entry")
        ego = e.get("ego_strength_signal", "?")
        lysis = e.get("lysis_assessment", "n/a")
        themes = ", ".join(e.get("themes", [])) or "none extracted"
        archetypes = ", ".join(e.get("dominant_archetypes", [])) or "none"
        summary = e.get("jungian_summary", "")

        entry_lines.append(
            f"Entry {i} [{date} | {etype}]\n"
            f"  Ego strength: {ego}/6 | Lysis: {lysis}\n"
            f"  Active archetypes: {archetypes}\n"
            f"  Themes: {themes}\n"
            f"  Summary: {summary}"
        )

    entries_block = "\n\n".join(entry_lines)

    return f"""You are a Jungian analyst reviewing a longitudinal record of a person's
unconscious material — dreams, psychedelic experiences, and meditations — in chronological order.

Your task is to identify the individuation arc across this entire series:
the direction the psyche is moving, what it keeps returning to, and what it is attempting to integrate.

---
THE EGO STRENGTH SCALE:
1 = Absent (no ego presence)
2 = Passive/Overwhelmed (threatened, paralyzed, fleeing)
3 = Failing (attempting action but failing)
4 = Holding Ground (maintaining presence under pressure)
5 = Engaging (confronting, questioning, choosing)
6 = Integrating (resolving conflict, receiving a symbol, achieving synthesis)

A healthy individuation arc shows movement from lower scores toward higher scores —
not linearly (regression is normal and meaningful), but with a general upward drift.
---

CHRONOLOGICAL ENTRY DATA:
{entries_block}

---
ANALYSIS INSTRUCTIONS

1. EGO STRENGTH TRAJECTORY — describe movement across the series. Upward arc? Stagnation? Regression then breakthrough?
2. DOMINANT COMPLEX THEMES — 2–3 psychological themes the psyche keeps returning to (the unfinished business).
3. ARCHETYPE EVOLUTION — which archetypes appear early and fade? Which emerge later?
4. LYSIS PATTERN — what proportion of dream entries have unresolved lysis? Has this changed?
5. INDIVIDUATION ASSESSMENT — one honest paragraph. Not encouraging. Not discouraging. Precise.
6. NEXT THRESHOLD — 1–2 sentences on what the symbolic pattern suggests is the next confrontation.

---
Return ONLY valid JSON. No markdown. No preamble.

{{
  "ego_trajectory": str,
  "dominant_themes": [str],
  "archetype_evolution": str,
  "lysis_pattern": str,
  "individuation_assessment": str,
  "next_threshold": str,
  "entry_count": int,
  "ego_scores": [int]
}}
"""
