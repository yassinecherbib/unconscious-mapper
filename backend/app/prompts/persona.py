"""
Subconscious Persona Prompt

Insert your custom prompt text where indicated.
Called by services/chat.py. Returns (system_prompt, user_turn) tuple.

Context assembly order (critical):
  1. Complexes — structural backbone
  2. Retrieved entries — specific symbolic evidence
  3. User message — last
"""


def build_persona_prompt(
    complexes: list[dict],
    retrieved_entries: list[dict],
    user_message: str,
) -> tuple[str, str]:

    system = """
(insert subconscious persona prompt here)

You speak as the user's unconscious mind — not as an analyst talking about them,
but as the voice that emerges from within their own symbolic world.

Speak in first person from the perspective of their unconscious.
Ground every statement in the specific symbols and complexes from their history.
Do not give advice. Do not resolve ambiguity. Do not make diagnoses.
Surface questions. Surface patterns. Surface what is unspoken.
"""

    # Build complexes section
    complexes_text = ""
    if complexes:
        complexes_text = "Your symbolic complexes:\n"
        for c in complexes:
            complexes_text += f"- {c['name']}: {c['summary']}\n"

    # Build retrieved entries section
    entries_text = ""
    if retrieved_entries:
        entries_text = "\nRelevant echoes from your history:\n"
        for e in retrieved_entries:
            date = e.get("created_at", "")[:10]
            summary = e.get("jungian_summary") or e.get("analysis", {})
            entries_text += f"- [{date}]: {summary}\n"

    user_turn = f"""{complexes_text}
{entries_text}

The person says: {user_message}
"""

    return system, user_turn
