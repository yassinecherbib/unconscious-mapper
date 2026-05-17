"""
Psychic Season Shift Detector — NEW FILE

Moved directly from extracted/season_detector.py — no changes needed.
Determines whether a longitudinal analysis should be triggered.
Pure Python signal computation — no AI calls.
"""

from datetime import datetime, timezone
from typing import Optional


MIN_ENTRIES = 7
MIN_DAYS_BETWEEN_ANALYSES = 14

EGO_INFLECTION_DELTA = 2
ARCHETYPE_ROTATION_WINDOW = 3
LYSIS_STUCK_THRESHOLD = 0.60
LYSIS_INTEGRATION_THRESHOLD = 0.20
LYSIS_PHASE_WINDOW = 5


def should_trigger_longitudinal(
    entries: list[dict],
    last_analysis_at: Optional[str] = None,
) -> dict:
    """
    Determine whether a longitudinal season analysis should be triggered.

    Args:
        entries: All user entries sorted by created_at ASC, each with:
                 - created_at, ego_strength_signal, lysis_assessment, dominant_archetypes
        last_analysis_at: ISO timestamp of the last longitudinal analysis, or None.

    Returns:
        { "should_trigger": bool, "reasons": list[str], "season_signal": str | None }
    """
    reasons = []
    season_signal = None

    if len(entries) < MIN_ENTRIES:
        return {"should_trigger": False, "reasons": ["insufficient_entries"], "season_signal": None}

    if last_analysis_at:
        last_dt = datetime.fromisoformat(last_analysis_at.replace("Z", "+00:00"))
        days_elapsed = (datetime.now(timezone.utc) - last_dt).days
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

    # Condition 1: Ego trajectory inflection
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
            dominant_early = max(early_archetypes, key=early_archetypes.get)  # type: ignore
            recent = entries[-ARCHETYPE_ROTATION_WINDOW:]
            recent_archetypes: set[str] = set()
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

    return {
        "should_trigger": len(reasons) > 0,
        "reasons": reasons,
        "season_signal": season_signal,
    }
