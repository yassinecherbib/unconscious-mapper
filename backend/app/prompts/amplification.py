"""
Amplification Pre-Analysis Prompt — NEW FILE

See extracted/amplification.py for full docstring and rationale.
Identifies 2-3 psychically ambiguous symbols and generates questions
for the user BEFORE the main extractor runs.
"""
from typing import Optional


def build_amplification_prompt(
    raw_text: str,
    entry_type: str,
    known_personal_symbols: dict[str, str],
) -> str:
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
- Symbols that are just setting or background with no emotional charge
- Symbols the user has already defined (see known list below)

{known_block}
For each selected symbol, generate one question. The question should:
- Be genuinely curious, not leading
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
      "symbol": str,
      "question": str
    }}
  ]
}}

If the entry is too short, vague, or contains no psychically ambiguous symbols,
return an empty array: {{ "symbols_to_amplify": [] }}
"""


def build_extractor_with_amplification(
    personal_associations: dict[str, str],
) -> str:
    """Returns a context block to inject into the extractor prompt."""
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
