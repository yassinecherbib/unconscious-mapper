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
) -> str:
    """
    Build the extraction prompt for a single journal entry.

    Args:
        raw_text: The raw dream/psychedelic/meditation text from the user.
        entry_type: One of 'dream', 'psychedelic', 'meditation'.
        previous_entries_summary: A brief textual summary of prior entries
            (used so the model can draw genuine connections). Pass empty string
            if this is the user's first entry.

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

    return f"""You are a depth-psychology analyst trained in the Jungian tradition.
Your task is to extract the symbolic, archetypal, emotional, and structural content
of the following {entry_type} entry with precision and interpretive integrity.

{type_context}

---
EXTRACTION FRAMEWORK
---

SYMBOLS
Identify specific images, objects, figures, places, animals, elements, colours, or actions
that carry symbolic weight. For each:
- Assign a category: animal | element | figure | place | object | colour | geometric | celestial | bodily | action
- Write a 1–2 sentence note on its significance in THIS specific context — not a generic dictionary definition.
  Ground the note in what actually happens to the symbol in the entry (is it threatening? transforming?
  pursued? destroyed?). That dynamic is the meaning.

ARCHETYPES
Map to Jungian archetypes where genuinely present. Do not force mappings onto thin material.
Candidates: Shadow, Anima, Animus, Self, Persona, Trickster, Great Mother, Terrible Mother,
Wise Old Man, Hero, Child, Threshold Guardian, Death, Rebirth.
For each detected archetype:
- Assign confidence (0.0–1.0)
- Cite the specific textual evidence
- Note whether it appears to be projected (seen in an external dream figure, especially
  a threatening or idealized one) or integrating (the dream-ego engaging it directly).
  Projection = unintegrated. Direct engagement = individuation in motion.

COMPENSATION AXIS
In 1–2 sentences: what does this unconscious content appear to be compensating for?
What one-sidedness in the conscious ego is the psyche pushing back against?
This is the most interpretively important field. If the entry is too thin to determine, say so.

EGO STRENGTH SIGNAL
Rate the dream-ego's posture on a 1–6 scale:
1 = Absent (pure observation, no ego presence)
2 = Passive/Overwhelmed (threatened, paralyzed, fleeing)
3 = Failing (attempting action but failing or unprepared)
4 = Holding Ground (maintaining presence under pressure)
5 = Engaging (confronting, questioning, choosing)
6 = Integrating (successfully resolving conflict, achieving a goal, receiving a symbol)
Include a 1-sentence rationale.

LYSIS ASSESSMENT (dreams only — skip for other types)
Resolved | Unresolved | Ambiguous
One sentence on what the ending reveals about the dreamer's current psychological position.

EMOTIONS
Name each distinct emotional tone. For each:
- valence: -1.0 (strongly negative) to 1.0 (strongly positive)
- intensity: 0.0 (barely present) to 1.0 (overwhelming)

THEMES
2–5 single words or short phrases naming the core psychological themes.
Examples: "dissolution", "confrontation with shadow", "transformation", "exile",
"return to origin", "devouring mother", "failed heroism", "numinous encounter"

JUNGIAN SUMMARY
2–3 sentences written as a Jungian analyst — focused on the unconscious significance,
not a retelling of events. This is the text the user reads. Make it precise, not reassuring.

CONNECTIONS TO PREVIOUS
List ONLY entry UUIDs from the previous context that share genuine symbolic or archetypal
connections with this entry. Genuine means: the same symbol recurs, the same archetype
activates, or the same compensation axis appears. If no genuine connection exists, return
an empty array. Do NOT manufacture connections to seem thorough.

---
RULES
- Extract what is actually present. Absence of a strong archetype is valid output.
- If the text is too short or vague for meaningful extraction, return minimal but valid output
  and note "insufficient material" in the summary.
- Return strictly valid JSON matching the schema. No markdown. No explanation. No preamble.
---

{prev_section}

Entry type: {entry_type}
Entry text:
---
{raw_text}
---
"""
