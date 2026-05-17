"""
Seed Symbol Extractor Prompt

Lightweight call — target under 1s, max_tokens=100.
Called by services/retrieval.py before topology traversal.

RECOMMENDED TEMPERATURE: 0.0
Rationale: This is a pure matching/extraction task with a constrained output.
Zero temperature. It must either match a known symbol exactly or identify
the most symbolically loaded term in the message. Creativity is irrelevant here —
consistency and speed are everything. Any temperature above 0.1 risks synonym
drift that breaks graph lookups.
"""


def build_seed_extractor_prompt(
    user_message: str,
    known_symbols: list[str],
) -> str:
    known = ", ".join(known_symbols[:50]) if known_symbols else "none yet"

    return f"""Extract the 1 to 3 most symbolically significant terms from the message below.

Priority rules (apply in order):
1. Prefer exact matches to the known symbols list — graph lookup depends on exact string matching.
2. If no known symbol matches, extract the most symbolically charged noun or figure in the message.
   "Symbolically charged" means: a figure, animal, element, place, object, or action that carries
   archetypal weight in Jungian terms. Prefer concrete nouns over abstract ones.
   Example: "the black dog that kept following me" → ["black dog"], not ["following"] or ["anxiety"].
3. Ignore filler words, conjunctions, emotional descriptors without a symbolic anchor.
4. Maximum 3 terms. Minimum 1.

Known symbols from this user's history: {known}

Message: "{user_message}"

Return ONLY a JSON array of strings. Example: ["water", "shadow", "old man"]
No explanation. No markdown. No preamble.
"""
