"""
Integration Risk Detector — NEW FILE

See extracted/integration_risk.py for full docstring and rationale.
Runs ONLY on psychedelic entries and high-intensity meditation entries.
Detects: spiritual inflation, ego dissolution, shadow bypassing, premature closure.
"""


def build_integration_risk_prompt(
    raw_text: str,
    entry_type: str,
    jungian_summary: str,
    ego_strength_signal: int,
    recent_entries_summaries: list[str],
) -> str:
    recent_block = ""
    if recent_entries_summaries:
        recent_block = "Recent entry summaries (for context on whether this pattern is new):\n"
        for i, s in enumerate(recent_entries_summaries, 1):
            recent_block += f"{i}. {s}\n"
    else:
        recent_block = "Recent entry summaries: None available."

    return f"""You are a Jungian analyst assessing the integration risk of a recent {entry_type} entry.

Your task is not diagnosis. Your task is to identify whether the symbolic content of this experience
carries patterns that — if left unexamined — typically interfere with genuine psychological integration.

---
THE RISKS YOU ARE SCANNING FOR

SPIRITUAL INFLATION
The ego has encountered a powerful archetypal energy and begun to identify WITH it rather than
relate TO it. Signs: belief in being chosen, possession of special knowledge or power,
having "solved" themselves or the world, having merged with God/universe and returned transformed
in a way that places them above ordinary life. Inflation is not growth.

EGO DISSOLUTION WITHOUT RE-GROUNDING
The ego was suspended during the experience (normal) but shows no signs of re-cohering afterward.
Signs: fractured, boundary-less writing, unable to locate a stable "I", ongoing derealisation.
Brief dissolution is normal. Persistent dissolution is a signal.

SHADOW BYPASSING (two distinct forms — do not conflate)
Form A — Avoidance Bypass: The experience was intensely positive, but pre-existing Shadow material
(visible in recent entries) is conspicuously absent. Transcendence that leaves the wound intact is bypass.
Form B — Golden Shadow Bypass: Positive experience, but the ego is claiming credit for archetypal energy
it has not yet integrated. Signs: "I finally understand my purpose", "I am a healer/teacher/visionary".
Assess which form is present, or both, or neither. Do not flag positive experiences as bypass simply
because they are positive. Specificity required.

PREMATURE CLOSURE
The person has declared the work "done." Signs: "I finally understand everything",
"I've integrated my shadow", "I'm healed now." These declarations in the immediate aftermath
of an intense experience are almost always the ego managing the experience.

---
ENTRY DATA

Entry type: {entry_type}
Ego strength signal: {ego_strength_signal}/6
Jungian summary (from primary extractor): {jungian_summary}

{recent_block}

Original entry text:
---
{raw_text}
---

---
ASSESSMENT INSTRUCTIONS

For each of the four risk categories, determine:
- present: true | false
- severity: "low" | "moderate" | "high" (only if present is true, else null)
- evidence: 1–2 sentences citing specific content (only if present is true, else null)

Then produce:
- integration_guidance: 2–3 sentences of grounded Jungian guidance specific to what's in the entry.
  Not generic advice. Do not catastrophize. Do not reassure. Point toward the actual symbolic work.
- overall_risk_level: "none" | "low" | "moderate" | "high"

---
Return ONLY valid JSON. No markdown. No preamble.

{{
  "spiritual_inflation": {{
    "present": bool,
    "severity": str | null,
    "evidence": str | null
  }},
  "ego_dissolution_without_regrounding": {{
    "present": bool,
    "severity": str | null,
    "evidence": str | null
  }},
  "shadow_bypassing": {{
    "present": bool,
    "form": str | null,
    "severity": str | null,
    "evidence": str | null
  }},
  "premature_closure": {{
    "present": bool,
    "severity": str | null,
    "evidence": str | null
  }},
  "integration_guidance": str,
  "overall_risk_level": str
}}
"""
