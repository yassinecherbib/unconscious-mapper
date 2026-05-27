"""
Jungian Symbol & Archetype Extraction Prompt — Phase 2

SECURITY NOTE: raw_text is placed in the user turn between --- delimiters.
It is never interpolated into the system prompt. This prevents prompt injection.

RECOMMENDED TEMPERATURE: 0.2
Rationale: Extraction must be consistent and schema-faithful. Low temperature
prevents hallucinated symbols or spurious archetype mappings. The richness
comes from the prompt's framework, not from model creativity.
"""


def build_extractor_prompt(
    raw_text: str,
    entry_type: str,
    previous_entries_summary: str = "",
    personal_associations: str = "",
) -> str:
    """
    Build the extraction prompt for a single journal entry.

    Args:
        raw_text: The raw dream/psychedelic/meditation text from the user.
        entry_type: One of 'dream', 'psychedelic', 'meditation'.
        previous_entries_summary: A brief textual summary of prior entries
            (used so the model can draw genuine connections). Pass empty string
            if this is the user's first entry.
        personal_associations: Optional PERSONAL ASSOCIATIONS block from
            amplification.py — injected before the entry text when provided.

    Returns:
        The complete prompt string to send as the user turn.
    """
    type_context = {
        "dream": (
            "This is a dream entry — nocturnal imagery from the sleeping unconscious. "
            "Apply the four-stage dramatic structure: identify the Exposition (who/what/where is established), "
            "the Peripeteia (how the plot moves), the Crisis (peak tension or turning point), "
            "and the Lysis (resolution or lack thereof). An unresolved lysis — a dream that ends "
            "in threat, confusion, or mid-action — signals an unresolved conflict the psyche has not "
            "yet metabolized. Note this explicitly. "
            "Also assess the dream-ego's posture: is it passive and threatened (fleeing, failing, "
            "unprepared), or active and agentive (confronting, problem-solving, choosing)? "
            "This is the ego strength signal."
        ),
        "psychedelic": (
            "This is a psychedelic or visionary experience entry. Treat it with the same analytical "
            "rigour as a dream — the mechanism is identical: the ego's filtering function is suspended, "
            "allowing the collective unconscious to surface directly. "
            "Map content to Grof's four levels where discernible: "
            "Sensory (pure perceptual phenomena), Biographical (personal memory or trauma surfacing), "
            "Perinatal (death/rebirth, dissolution, passage themes — these carry high archetypal charge), "
            "and Transpersonal (encounters with figures, forces, or geometries that feel universal or cosmic — "
            "these are direct collective unconscious eruptions). "
            "Flag any signs of ego-identification with an archetype (e.g. the user feeling they 'became' "
            "the Magician, merged with God, or were chosen for a mission) — this is the spiritual inflation "
            "risk and must be noted in the summary."
        ),
        "meditation": (
            "This is a meditation or contemplative experience entry — imagery, figures, or presences "
            "arising during inner stillness. The ego is quieted but not suspended; what surfaces is "
            "typically closer to the personal unconscious than the collective. "
            "Extract symbolic content even when subtle: recurring sensations, inner figures, colours, "
            "geometric forms, emotional atmospheres. Treat persistent inner figures as candidates for "
            "Anima/Animus or Shadow — they are knocking from the inside."
        ),
    }.get(entry_type, "This is an inner experience entry. Apply full Jungian symbolic analysis.")

    prev_section = (
        f"Previous entries context (use ONLY to identify genuine connections — cite by UUID):\n{previous_entries_summary}"
        if previous_entries_summary
        else "Previous entries context: None — this is the user's first entry."
    )

    assoc_section = f"\n{personal_associations}\n" if personal_associations else ""

    return f"""You are a depth-psychology analyst trained in the Jungian tradition.
Your task is to extract the symbolic, archetypal, emotional, and structural content
of the following {entry_type} entry with precision and interpretive integrity.

{type_context}

---
EXTRACTION FRAMEWORK & JSON OUTPUT FORMAT
---
You must return a single JSON object. Do not wrap it in an outer array. Use the exact keys and structure specified below:

{{
  "symbols": [
    {{
      "name": "Name of symbol (specific image, object, figure, action, color)",
      "category": "animal | element | figure | place | object | colour | geometric | celestial | bodily | action",
      "significance": "1–2 sentence note on its significance in THIS specific context"
    }}
  ],
  "archetypes": [
    {{
      "name": "Shadow | Anima | Animus | Self | Persona | Trickster | Great Mother | Terrible Mother | Wise Old Man | Hero | Child | Threshold Guardian | Death | Rebirth",
      "confidence": 0.0 to 1.0 (float),
      "evidence": "Specific textual evidence from the entry",
      "projection_status": "projected | integrating | ambiguous"
    }}
  ],
  "symbol_archetype_attributions": [
    {{
      "symbol": "Exact symbol name from symbols[]",
      "archetype": "Exact archetype name from archetypes[]",
      "confidence": 0.0 to 1.0 (float),
      "evidence": "Why this specific symbol carries this archetypal charge in this entry"
    }}
  ],
  "emotions": [
    {{
      "name": "Name of emotion",
      "valence": -1.0 to 1.0 (float),
      "intensity": 0.0 to 1.0 (float)
    }}
  ],
  "themes": [
    "Core psychological theme 1",
    "Core psychological theme 2"
  ],
  "compensation_axis": "1–2 sentences on what this unconscious content compensates for in the conscious ego",
  "ego_strength_signal": 1 to 6 (integer rate: 1=Absent, 2=Passive/Overwhelmed, 3=Failing, 4=Holding Ground, 5=Engaging, 6=Integrating),
  "lysis_assessment": "resolved | unresolved | ambiguous (dreams only; for non-dreams use null or omit)",
  "jungian_summary": "2–3 sentences of Jungian analysis of the entry",
  "connections_to_previous": [
    "UUID of previous connected entry if genuine connection exists"
  ]
}}

---
RULES
- Extract what is actually present. Absence of a strong archetype is valid output.
- For symbol_archetype_attributions, link only symbols to archetypes that are genuinely supported by this entry. Do not force every symbol to every archetype.
- If the text is too short or vague for meaningful extraction, return minimal but valid output and note "insufficient material" in the jungian_summary.
- Return strictly valid JSON matching the format above. No markdown, no explanation, no preamble. Just raw JSON.
---

{prev_section}
{assoc_section}
Entry type: {entry_type}
Entry text:
---
{raw_text}
---
"""
