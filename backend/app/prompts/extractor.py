"""
Jungian Symbol & Archetype Extraction Prompt — Phase 2

SECURITY NOTE: raw_text is placed in the user turn between --- delimiters.
It is never interpolated into the system prompt. This prevents prompt injection.

The function returns a single string (the user turn only) because google-genai's
response_schema=AnalysisResult handles JSON enforcement natively — no system
prompt is needed; the schema constraint IS the instruction.
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
        The complete prompt string to send as the user turn to Gemma.
    """
    type_context = {
        "dream": (
            "This is a dream entry — nocturnal imagery arising from the sleeping unconscious. "
            "Pay attention to numinous figures, impossible environments, emotional tone on waking, "
            "and recurring motifs the dreamer may not consciously register."
        ),
        "psychedelic": (
            "This is a psychedelic or visionary experience entry — content arising under an expanded "
            "state of consciousness. Treat symbolic content with the same rigour as a dream: "
            "archetypal figures, dissolution of ego boundaries, encounters with the numinous, "
            "geometric or cosmic imagery, and emotional textures should all be extracted."
        ),
        "meditation": (
            "This is a meditation or contemplative experience entry — imagery, feelings, or presences "
            "arising during inner stillness. Extract symbolic content even if it feels subtle: "
            "recurring sensations, inner figures, colours, geometric forms, or emotional atmospheres."
        ),
    }.get(entry_type, "This is an inner experience entry.")

    prev_section = (
        f"Previous entries context (use ONLY to identify genuine connections — cite by UUID):\n{previous_entries_summary}"
        if previous_entries_summary
        else "Previous entries context: None — this is the user's first entry."
    )

    return f"""You are a depth-psychology analyst trained in the Jungian tradition.
Analyse the following {entry_type} entry and extract its symbolic, archetypal, and emotional content.

{type_context}

Jungian framework to apply:
- SYMBOLS: Identify specific images, objects, figures, places, animals, elements, or actions that carry symbolic weight. Assign each a category (e.g. animal, element, figure, place, object, colour, geometric, celestial, bodily) and a 1-2 sentence note on its significance in this specific context.
- ARCHETYPES: Map to Jungian archetypes where genuinely present — Shadow, Anima, Animus, Self, Persona, Trickster, Great Mother, Wise Old Man, Hero, Child, etc. Assign a confidence score (0.0–1.0) and cite specific evidence from the text.
- EMOTIONS: Name each distinct emotional tone, assign valence (-1.0 = strongly negative, 0 = neutral, 1.0 = strongly positive) and intensity (0.0 = barely present, 1.0 = overwhelming).
- THEMES: 2–5 single words or short phrases naming the core psychological themes (e.g. "dissolution", "confrontation with shadow", "transformation", "return to origin").
- JUNGIAN SUMMARY: 2–3 sentences written as a Jungian analyst would write about this entry — focused on its unconscious significance, not a retelling of the content.
- CONNECTIONS TO PREVIOUS: List ONLY entry UUIDs from the previous context that are genuinely connected by shared symbols or archetypal patterns. If no genuine connection exists, return an empty array. Do NOT invent connections.

Rules:
- Extract what is actually present — do not force archetypes onto thin material.
- If the text is too short or vague to extract meaningful symbols, return minimal but valid output.
- Return strictly valid JSON matching the schema. No markdown. No explanation. No preamble.

{prev_section}

Entry type: {entry_type}
Entry text:
---
{raw_text}
---
"""
