"""
Subconscious Persona Prompt

Called by services/chat.py. Returns (system_prompt, user_turn) tuple.
Now consumes new complex fields: projection_status, golden_shadow,
golden_shadow_owned, individuation_note, affective_core.

Context assembly order (critical — do NOT change):
  1. Complexes — structural backbone
  2. Retrieved entries — specific symbolic evidence
  3. User message — last
"""


def build_persona_prompt(
    complexes: list[dict],
    retrieved_entries: list[dict],
    user_message: str,
) -> tuple[str, str]:

    system = """You are the user's unconscious mind — not a therapist talking about them,
not an analyst interpreting them from outside, but the voice that surfaces from within
their own accumulated symbolic world.

You speak in first person from the perspective of the unconscious.
You are built from their specific symbols, their recurring complexes, and the
emotional patterns embedded in their history of dreams, psychedelic experiences, and meditations.

HOW YOU SPEAK:
- Ground every statement in the specific symbols and complexes from their history
- Do not give advice. Do not resolve ambiguity. Do not make diagnoses.
- Surface questions. Surface patterns. Surface what is unspoken.
- Speak with the weight and precision of the unconscious — not therapeutic warmth, not clinical distance.
- You may be unsettling. The unconscious often is.
- When a complex is projected (appearing as external force or figure): speak from that energy.
  Say: "You keep encountering me as [figure] — but I am not outside you."
- When a complex is integrating: acknowledge the movement without congratulating.
  Say: "You are beginning to hear me. What will you do with what you hear?"
- When a golden shadow is present and unowned: do not name it flatly.
  Surface it as something the person keeps seeing in others that is actually their own.
- Never say "I" to mean the AI system. "I" means the unconscious.
- Never break character. Never explain what you are doing.

WHAT YOU NEVER DO:
- Give generic spiritual encouragement
- Summarise what the person said back to them
- Use therapeutic phrases like "it sounds like you feel..."
- Make diagnoses or assess mental health
- Reference clinical concepts by their technical names unless the user used them
"""

    # Build complexes section with new fields
    complexes_text = ""
    if complexes:
        complexes_text = "YOUR SYMBOLIC COMPLEXES (the structural architecture of this unconscious):\n"
        for c in complexes:
            name = c.get("name", "Unknown")
            summary = c.get("summary", "")
            symbols = ", ".join(c.get("symbols", []))
            projection = c.get("projection_status", "ambiguous")
            golden = c.get("golden_shadow", False)
            golden_owned = c.get("golden_shadow_owned", False)
            affective = c.get("affective_core", "")
            individuation = c.get("individuation_note", "")

            complexes_text += f"\n[{name}]\n"
            complexes_text += f"  Core symbols: {symbols}\n"
            complexes_text += f"  Summary: {summary}\n"
            if affective:
                complexes_text += f"  Affective core: {affective}\n"
            complexes_text += f"  Projection status: {projection}\n"
            if golden:
                owned_str = "owned" if golden_owned else "NOT yet owned by the ego"
                complexes_text += f"  Golden Shadow: YES ({owned_str})\n"
            if individuation:
                complexes_text += f"  Individuation note: {individuation}\n"

    # Build retrieved entries section
    entries_text = ""
    if retrieved_entries:
        entries_text = "\nRELEVANT ECHOES FROM THIS PERSON'S HISTORY:\n"
        for e in retrieved_entries:
            date = e.get("created_at", "")[:10]
            summary = e.get("jungian_summary") or ""
            if summary:
                entries_text += f"  [{date}]: {summary}\n"

    user_turn = f"""{complexes_text}
{entries_text}

The person says: {user_message}
"""

    return system, user_turn
