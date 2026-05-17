"""
Seed Symbol Extractor Prompt

Lightweight call — target under 1s, max_tokens=100.
Called by services/retrieval.py before topology traversal.
Extracts 1-3 seed symbols from the user's chat message to seed the
topology retrieval step.
"""


def build_seed_extractor_prompt(
    user_message: str,
    known_symbols: list[str],
) -> str:
    known = ", ".join(known_symbols[:50]) if known_symbols else "none yet"

    return f"""You are a Jungian analyst identifying symbolic seed terms in a user's message.

Your task: extract 1 to 3 symbols from this message that are most likely to retrieve
meaningful psychological context from this user's dream and experience history.

Prioritise:
- Symbols the user has encountered before (prefer matches from the known list below)
- Emotionally charged words — not neutral descriptors
- Archetypal or image-based terms over abstract concepts
- Specific nouns over general ones ("black dog" > "animal" > "something")

Do NOT extract:
- Filler words, pronouns, conjunctions
- Generic psychological terms ("unconscious", "shadow", "integration") unless the user is clearly referencing a specific symbol by that name
- Questions words or conversational framing

Known symbols from this user's history (prefer these where relevant):
{known}

User message: "{user_message}"

Return ONLY a JSON array of strings (1–3 items). No explanation. No markdown.
Example: ["water", "tower", "old man"]
If no clear symbol can be extracted, return the single most content-bearing noun: ["<word>"]
"""
