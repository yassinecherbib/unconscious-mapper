"""
Seed Symbol Extractor Prompt

Insert your custom prompt text where indicated.
Lightweight call — target under 1s, max_tokens=100.
Called by services/retrieval.py before topology traversal.
"""


def build_seed_extractor_prompt(
    user_message: str,
    known_symbols: list[str],
) -> str:
    known = ", ".join(known_symbols[:50]) if known_symbols else "none yet"

    return f"""
(insert seed symbol extraction prompt here)

Extract the 1 to 3 most symbolically significant terms from this message.
Prefer terms that match symbols already in this user's history where possible.

Known symbols: {known}

Message: "{user_message}"

Return ONLY a JSON array of strings. Example: ["water", "shadow"]
No explanation. No markdown.
"""
