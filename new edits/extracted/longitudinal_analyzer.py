"""
Longitudinal Individuation Arc Analyzer

NEW FILE — not in original codebase.

TRIGGER LOGIC — DO NOT USE ENTRY COUNT AS THE SOLE TRIGGER.
The psyche moves in seasons, not counts. 10 entries over 3 years is not the same
psychic moment as 10 entries over 3 weeks. The longitudinal analyzer should run when
a SEASON SHIFT is detected, not on a fixed schedule.

A season shift is indicated by ANY of the following:
  1. ENTRY-COUNT FLOOR: minimum 7 entries exist (below this, no meaningful arc)
  2. EGO TRAJECTORY INFLECTION: ego_strength_signal changes by ±2 across 3 consecutive
     entries in either direction (breakthrough or regression — both are season markers)
  3. ARCHETYPE ROTATION: a previously dominant archetype disappears for 3+ entries and
     a new one appears — the psyche has moved to a new territory
  4. LYSIS PHASE SHIFT: unresolved lysis proportion crosses a threshold in either direction
     (> 60% unresolved for 5 entries = stuck season | < 20% for 5 entries = integration season)
  5. CALENDAR FLOOR: minimum 14 days have elapsed since last longitudinal analysis,
     regardless of entry count. Prevents over-triggering during intense journaling periods.

These conditions should be computed in services/longitudinal.py before calling this prompt.
The prompt itself is agnostic to why it was triggered — it always analyzes the full history.

RECOMMENDED TEMPERATURE: 0.3
"""


def build_longitudinal_analyzer_prompt(entries: list[dict]) -> str:
    """
    Build the longitudinal arc analysis prompt.

    Args:
        entries: List of entry dicts sorted by created_at ASC, each containing:
                 - created_at: ISO timestamp
                 - entry_type: 'dream' | 'psychedelic' | 'meditation'
                 - ego_strength_signal: int 1–6 (from extractor)
                 - lysis_assessment: 'resolved' | 'unresolved' | 'ambiguous' | None
                 - themes: list[str]
                 - jungian_summary: str
                 - dominant_archetypes: list[str]

    Returns:
        Prompt string for the longitudinal analysis call.
    """
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
THE EGO STRENGTH SCALE (for reference):
1 = Absent (no ego presence in the experience)
2 = Passive/Overwhelmed (threatened, paralyzed, fleeing)
3 = Failing (attempting action but failing)
4 = Holding Ground (maintaining presence under pressure)
5 = Engaging (confronting, questioning, choosing)
6 = Integrating (resolving conflict, receiving a symbol, achieving synthesis)

A healthy individuation arc shows movement from lower scores toward higher scores over time —
not linearly (regression is normal and meaningful), but with a general upward drift.
---

CHRONOLOGICAL ENTRY DATA:
{entries_block}

---
ANALYSIS INSTRUCTIONS

1. EGO STRENGTH TRAJECTORY
   Describe the movement of ego strength scores across the series.
   Is there a discernible upward arc? Stagnation? Regression followed by breakthrough?
   Note any sharp changes and what preceded them.

2. DOMINANT COMPLEX THEMES
   What 2–3 psychological themes recur most persistently across the series?
   These are the complexes the psyche keeps returning to — the unfinished business.

3. ARCHETYPE EVOLUTION
   Which archetypes appear early and fade? Which emerge later?
   Movement from Shadow-dominant early entries toward Self or Anima/Animus engagement later
   is a classic individuation signal. Note what you see.

4. LYSIS PATTERN
   What proportion of dream entries have unresolved lysis?
   A high proportion of unresolved endings indicates the psyche is holding significant
   unmetabolized tension. Has this changed over time?

5. INDIVIDUATION ASSESSMENT
   A honest one-paragraph assessment of where this person appears to be on their individuation arc.
   Not encouraging. Not discouraging. Precise. What is the psyche working on?
   What has it made progress on? What remains projected or avoided?

6. NEXT THRESHOLD
   In 1–2 sentences: what does the symbolic pattern suggest is the next confrontation?
   What is knocking at the threshold that has not yet been opened?

---
RETURN FORMAT
Return ONLY valid JSON. No markdown. No preamble.

{{
  "ego_trajectory": str,           // Description of ego strength movement across the series
  "dominant_themes": [str],        // 2–3 recurring psychological themes
  "archetype_evolution": str,      // Description of how archetypes shift across the series
  "lysis_pattern": str,            // Assessment of unresolved vs resolved lysis proportion and trend
  "individuation_assessment": str, // Honest paragraph on current individuation position
  "next_threshold": str,           // 1–2 sentences on what the psyche is approaching
  "entry_count": int,              // Total entries analyzed
  "ego_scores": [int]              // Raw ego strength scores in chronological order (for graphing)
}}
"""
