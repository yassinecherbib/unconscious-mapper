"""
Psychic Season Shift Detector

Determines whether a longitudinal analysis should be triggered.
Called by services/longitudinal.py before building the analyzer prompt.

This replaces the naive "every N entries" trigger. The psyche moves in seasons —
periods of relative stability, punctuated by inflection points.
No AI calls. Pure signal computation on structured data.
"""

from datetime import datetime, timezone
from typing import Optional


# Minimum conditions before any season analysis is valid
MIN_ENTRIES = 7
MIN_DAYS_BETWEEN_ANALYSES = 14

# Thresholds
EGO_INFLECTION_DELTA = 2        # Score change across 3 consecutive entries
ARCHETYPE_ROTATION_WINDOW = 3   # Consecutive entries without a previously dominant archetype
LYSIS_STUCK_THRESHOLD = 0.60    # Proportion unresolved = "stuck season"
LYSIS_INTEGRATION_THRESHOLD = 0.20  # Proportion unresolved = "integration season"
LYSIS_PHASE_WINDOW = 5          # Entries to compute lysis proportion over


def should_trigger_longitudinal(
    entries: list[dict],
    last_analysis_at: Optional[str] = None,  # ISO timestamp or None
) -> dict:
    """
    Determine whether a longitudinal season analysis should be triggered.

    Args:
        entries: All user entries sorted by created_at ASC, each with:
                 - created_at: ISO timestamp str
                 - ego_strength_signal: int 1–6
                 - lysis_assessment: 'resolved' | 'unresolved' | 'ambiguous' | None
                 - dominant_archetypes: list[str]
        last_analysis_at: ISO timestamp of the last longitudinal analysis, or None.

    Returns:
        {
            "should_trigger": bool,
            "reasons": list[str],
            "season_signal": str    # "breakthrough" | "regression" | "stuck" |
                                    # "integrating" | "archetype_shift" | "first_analysis"
        }
    """
    reasons = []
    season_signal = None

    # Floor check
    if len(entries) < MIN_ENTRIES:
        return {"should_trigger": False, "reasons": ["insufficient_entries"], "season_signal": None}

    # Calendar floor — prevent over-triggering during intense journaling bursts
    if last_analysis_at:
        last_dt = datetime.fromisoformat(last_analysis_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_elapsed = (now - last_dt).days
        if days_elapsed < MIN_DAYS_BETWEEN_ANALYSES:
            return {
                "should_trigger": False,
                "reasons": [f"too_soon_{days_elapsed}_days_since_last"],
                "season_signal": None,
            }

    ego_scores = [
        e.get("ego_strength_signal")
        for e in entries
        if e.get("ego_strength_signal") is not None
    ]

    # Condition 1: Ego trajectory inflection (breakthrough or regression)
    if len(ego_scores) >= 3:
        for i in range(len(ego_scores) - 2):
            window = ego_scores[i:i + 3]
            delta = window[-1] - window[0]
            if abs(delta) >= EGO_INFLECTION_DELTA:
                direction = "breakthrough" if delta > 0 else "regression"
                reasons.append(f"ego_inflection_{direction}_delta_{delta}")
                if season_signal is None:
                    season_signal = direction
                break

    # Condition 2: Archetype rotation
    if len(entries) > ARCHETYPE_ROTATION_WINDOW * 2:
        early_archetypes: dict[str, int] = {}
        half = len(entries) // 2
        for e in entries[:half]:
            for a in e.get("dominant_archetypes", []):
                early_archetypes[a] = early_archetypes.get(a, 0) + 1

        if early_archetypes:
            dominant_early = max(early_archetypes, key=early_archetypes.get)
            recent = entries[-ARCHETYPE_ROTATION_WINDOW:]
            recent_archetypes = set()
            for e in recent:
                recent_archetypes.update(e.get("dominant_archetypes", []))

            if dominant_early not in recent_archetypes:
                reasons.append(f"archetype_rotation_{dominant_early}_faded")
                if season_signal is None:
                    season_signal = "archetype_shift"

    # Condition 3: Lysis phase shift
    dream_entries = [e for e in entries if e.get("entry_type") == "dream"]
    if len(dream_entries) >= LYSIS_PHASE_WINDOW:
        recent_dreams = dream_entries[-LYSIS_PHASE_WINDOW:]
        unresolved_count = sum(
            1 for e in recent_dreams if e.get("lysis_assessment") == "unresolved"
        )
        unresolved_ratio = unresolved_count / len(recent_dreams)

        if unresolved_ratio >= LYSIS_STUCK_THRESHOLD:
            reasons.append(f"lysis_stuck_{unresolved_ratio:.0%}_unresolved")
            if season_signal is None:
                season_signal = "stuck"
        elif unresolved_ratio <= LYSIS_INTEGRATION_THRESHOLD:
            reasons.append(f"lysis_integrating_{unresolved_ratio:.0%}_unresolved")
            if season_signal is None:
                season_signal = "integrating"

    # Condition 4: First analysis ever
    if last_analysis_at is None and len(entries) >= MIN_ENTRIES:
        reasons.append("first_analysis")
        if season_signal is None:
            season_signal = "first_analysis"

    should_trigger = len(reasons) > 0

    return {
        "should_trigger": should_trigger,
        "reasons": reasons,
        "season_signal": season_signal,
    }
