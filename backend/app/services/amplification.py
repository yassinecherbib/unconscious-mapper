"""
Amplification Service

Runs the amplification pre-analysis call when a user submits a new entry.
Returns questions about personally ambiguous symbols for the user to answer
before the main extraction runs.

Flow:
  1. entries router calls get_amplification_questions()
  2. Questions are returned to the frontend immediately (before extraction)
  3. Frontend shows them; user answers or skips
  4. Frontend calls POST /entries/amplify with answers
  5. entries router calls run_extraction() with personal_associations included
"""
import json

from google import genai
from google.genai import types

from app.config import settings
from app.prompts.amplification import build_amplification_prompt, build_extractor_with_amplification
from app.models import AmplificationResult

_client = genai.Client(api_key=settings.gemini_api_key)


async def get_amplification_questions(
    raw_text: str,
    entry_type: str,
    known_personal_symbols: dict[str, str],
) -> list[dict]:
    """
    Returns a list of {symbol, question} dicts to ask the user.
    Returns [] if no ambiguous symbols found or if the call fails.
    """
    prompt = build_amplification_prompt(raw_text, entry_type, known_personal_symbols)

    try:
        response = await _client.aio.models.generate_content(
            model="gemma-4-26b-a4b-it",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AmplificationResult,
                max_output_tokens=300,
                temperature=0.3,
            ),
        )
        if response.parsed is None:
            print(f"[amplification] model returned no structured output. Raw: {response.text[:500]}")
            return []
        return [q.model_dump() for q in response.parsed.symbols_to_amplify]
    except Exception as exc:
        print(f"[amplification] question generation failed: {exc}")
        return []


def format_personal_associations(answers: dict[str, str]) -> str:
    """
    Formats user's answers into the PERSONAL ASSOCIATIONS block
    for injection into the extractor prompt.
    """
    return build_extractor_with_amplification("", answers)
