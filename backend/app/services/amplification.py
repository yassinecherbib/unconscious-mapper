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


def parse_and_map_amplification_result(raw_json_str: str) -> list[dict]:
    try:
        data = json.loads(raw_json_str)
        if isinstance(data, list):
            questions = data
        elif isinstance(data, dict):
            questions = data.get("symbols_to_amplify") or data.get("symbols") or data.get("questions") or []
        else:
            questions = []

        if not isinstance(questions, list):
            questions = []

        mapped = []
        for q in questions:
            if isinstance(q, dict):
                symbol = q.get("symbol") or q.get("name") or ""
                question = q.get("question") or q.get("text") or q.get("prompt") or ""
                if symbol and question:
                    mapped.append({"symbol": symbol, "question": question})
        return mapped
    except Exception as exc:
        print(f"[amplification] failed to parse JSON: {exc}")
        return []


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
                max_output_tokens=300,
                temperature=0.3,
            ),
        )
        if not response.text:
            print("[amplification] model returned empty output")
            return []
        return parse_and_map_amplification_result(response.text)
    except Exception as exc:
        print(f"[amplification] question generation failed: {exc}")
        return []


def format_personal_associations(answers: dict[str, str]) -> str:
    """
    Formats user's answers into the PERSONAL ASSOCIATIONS block
    for injection into the extractor prompt.
    """
    return build_extractor_with_amplification("", answers)
