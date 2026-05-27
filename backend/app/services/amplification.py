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
import asyncio
import re

from google import genai
from google.genai import types

from app.config import settings
from app.prompts.amplification import build_amplification_prompt, build_extractor_with_amplification
from app.models import AmplificationResult

_client = genai.Client(api_key=settings.gemini_api_key)

AMPLIFICATION_MODEL = "gemini-3.1-flash-lite"
AMPLIFICATION_TIMEOUT_SECONDS = 20
AMPLIFICATION_REQUEST_TIMEOUT_MS = 19000

_FALLBACK_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\b(?:angry|quiet|old|young|tall|dark|strange|unknown)\s+(?:man|woman|boy|girl|person|people)\b", re.I),
        "What comes to mind when you think about {symbol}?",
    ),
    (
        re.compile(r"\b(?:man|woman|boy|girl|mother|father|child|person|people)\b", re.I),
        "What is your immediate association with {symbol}?",
    ),
    (
        re.compile(r"\b(?:dark|empty|locked|hidden|strange|old)\s+(?:room|house|building|door|window)\b", re.I),
        "What does {symbol} feel like or remind you of?",
    ),
    (
        re.compile(r"\b(?:room|house|building|door|window|corridor|hallway)\b", re.I),
        "What associations do you have with {symbol}?",
    ),
    (
        re.compile(r"\b(?:dog|cat|snake|bird|horse|wolf|lion|spider|fish)\b", re.I),
        "What personal memories or feelings come up around {symbol}?",
    ),
)


def _load_json_from_model_text(raw_json_str: str):
    text = raw_json_str.strip()

    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").strip()
        if text.endswith("```"):
            text = text[:-3].strip()

    decoder = json.JSONDecoder()
    for idx, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            data, _ = decoder.raw_decode(text[idx:])
            return data
        except json.JSONDecodeError:
            continue

    return json.loads(text)


def parse_and_map_amplification_result(raw_json_str: str) -> list[dict]:
    try:
        data = _load_json_from_model_text(raw_json_str)
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


def _fallback_amplification_questions(
    raw_text: str,
    known_personal_symbols: dict[str, str],
    limit: int = 3,
) -> list[dict]:
    known = {symbol.lower().strip() for symbol in known_personal_symbols}
    questions: list[dict] = []
    seen: set[str] = set()

    for pattern, question_template in _FALLBACK_PATTERNS:
        for match in pattern.finditer(raw_text):
            symbol = match.group(0).strip()
            key = symbol.lower()
            if key in seen or key in known or any(key in existing or existing in key for existing in seen):
                continue
            seen.add(key)
            questions.append({
                "symbol": symbol,
                "question": question_template.format(symbol=symbol),
            })
            if len(questions) >= limit:
                return questions

    return questions


def _fallback_with_log(
    reason: str,
    raw_text: str,
    known_personal_symbols: dict[str, str],
) -> list[dict]:
    questions = _fallback_amplification_questions(raw_text, known_personal_symbols)
    print(f"[amplification] using fallback questions after {reason}; count={len(questions)}")
    return questions


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
        response = await asyncio.wait_for(
            _client.aio.models.generate_content(
                model=AMPLIFICATION_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    max_output_tokens=300,
                    temperature=0.2,
                    http_options=types.HttpOptions(timeout=AMPLIFICATION_REQUEST_TIMEOUT_MS),
                ),
            ),
            timeout=AMPLIFICATION_TIMEOUT_SECONDS,
        )
        if not response.text:
            print("[amplification] model returned empty output")
            return _fallback_with_log("empty model output", raw_text, known_personal_symbols)
        questions = parse_and_map_amplification_result(response.text)
        if not questions:
            return _fallback_with_log("empty parsed model output", raw_text, known_personal_symbols)
        return questions
    except asyncio.TimeoutError:
        print(f"[amplification] question generation timed out after {AMPLIFICATION_TIMEOUT_SECONDS}s")
        return _fallback_with_log("timeout", raw_text, known_personal_symbols)
    except Exception as exc:
        print(f"[amplification] question generation failed: {exc}")
        return _fallback_with_log("model error", raw_text, known_personal_symbols)


def format_personal_associations(answers: dict[str, str]) -> str:
    """
    Formats user's answers into the PERSONAL ASSOCIATIONS block
    for injection into the extractor prompt.
    """
    return build_extractor_with_amplification("", answers)
