"""
Amplification Pre-Analysis Prompt

NEW FILE — not in original codebase.
This is the step that separates genuine Jungian analysis from AI dream dictionary lookup.

WHAT THIS DOES AND WHY IT EXISTS

In Jungian practice, the analyst never interprets a symbol without first asking the dreamer
for their personal associations. The symbol "black dog" means something categorically different
to someone whose childhood dog was black and died traumatically than to someone who has never
owned a dog. The archetypal layer (Jung's amplification via mythology, culture, history) is
the SECOND layer — it contextualizes the personal, it does not replace it.

The original extractor.py jumped straight to interpretation. This file inserts the correct
intermediate step: the system identifies 2–3 symbols that are ambiguous without personal
context and surfaces them to the user as questions. The user's answers are then passed back
into the extractor as part of the entry context, improving interpretation quality.

FLOW:
  1. User submits raw entry text
  2. [THIS FILE] — quick call, identifies ambiguous symbols, returns questions
  3. UI surfaces questions to the user (optional — user can skip)
  4. User answers (or skips)
  5. extractor.py runs with raw_text + personal_associations included

RECOMMENDED TEMPERATURE: 0.3
Rationale: Symbol identification must be accurate. The questions must feel genuinely
curious, not generic. 0.3 gives enough voice to make the questions land without
drifting into therapeutic mimicry.

Called by: services/amplification.py (to be created)
Timing: After entry submission, before extractor.py runs.
Max tokens: 300 — this must be fast and lightweight.
"""


def build_amplification_prompt(
    raw_text: str,
    entry_type: str,
    known_personal_symbols: dict[str, str],  # symbol -> user's previously stated meaning
) -> str:
    """
    Build the amplification question prompt.

    Args:
        raw_text: The raw entry text.
        entry_type: 'dream' | 'psychedelic' | 'meditation'
        known_personal_symbols: Dict of symbols the user has already defined personally
                                 from previous amplification sessions.
                                 e.g. {"water": "always feels like my mother's silence"}
                                 These should NOT be asked again.

    Returns:
        Prompt string. Model returns a small JSON object with 2–3 questions.
    """
    known_block = ""
    if known_personal_symbols:
        known_block = (
            "Symbols already personally defined by this user — do NOT ask about these:\n"
            + "\n".join(f"- {sym}: \"{meaning}\"" for sym, meaning in known_personal_symbols.items())
            + "\n"
        )
    else:
        known_block = "No symbols have been personally defined yet.\n"

    return f"""You are a Jungian analyst reviewing a {entry_type} entry before interpretation.

Your task is to identify the 2–3 symbols in this entry that are most psychically ambiguous —
symbols whose meaning in this specific context cannot be reliably determined without knowing
this particular person's associations with them.

WHAT MAKES A SYMBOL AMBIGUOUS (prioritize these):
- Animals: the same animal means radically different things depending on personal history
- People (unnamed or archetypal): "a tall man", "my mother", "an old woman"
- Buildings, rooms, houses: personal resonance is almost always idiosyncratic
- Recurring symbols: if something appears with unusual emphasis or repetition in THIS entry
- Any symbol carrying the highest emotional charge in the entry

WHAT TO SKIP:
- Symbols with clear archetypal meaning that personal association is unlikely to override
  (e.g. universal geometric forms, celestial bodies in a non-personal context)
- Symbols that are just setting or background with no emotional charge
- Symbols the user has already defined (see known list below)

{known_block}

For each selected symbol, generate one question. The question should:
- Be genuinely curious, not leading ("What does water make you think of in your waking life?"
  NOT "Does water represent your emotions?")
- Be open-ended — no yes/no
- Sound like a thoughtful person asking, not a form field
- Be short: one sentence

ENTRY TEXT:
---
{raw_text}
---

Return ONLY valid JSON. No markdown. No preamble.
{{
  "symbols_to_amplify": [
    {{
      "symbol": str,          // The exact symbol term as it appears in the entry
      "question": str         // The question to ask the user
    }}
  ]
}}

If the entry is too short, vague, or contains no psychically ambiguous symbols,
return an empty array: {{ "symbols_to_amplify": [] }}
"""


def build_extractor_with_amplification(
    raw_text: str,
    personal_associations: dict[str, str],  # symbol -> user's answer
) -> str:
    """
    Returns an addendum to append to the extractor prompt when personal associations
    have been collected. Injected into extractor.py's prev_section or as a separate
    context block.

    Args:
        raw_text: Not used here — just for documentation. Passed to extractor.py.
        personal_associations: Dict of symbol -> user's stated personal meaning.
                               e.g. {"black dog": "reminds me of my father's depression"}

    Returns:
        A formatted string to inject into the extractor prompt as personal context.
    """
    if not personal_associations:
        return ""

    lines = "\n".join(
        f"- \"{symbol}\": {meaning}"
        for symbol, meaning in personal_associations.items()
    )

    return (
        f"PERSONAL ASSOCIATIONS (provided by the user — weight these heavily "
        f"over archetypal defaults when interpreting these specific symbols):\n{lines}"
    )
