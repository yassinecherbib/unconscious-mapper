"""
Phase 2 — AI Extraction Service

Calls Gemma (gemma-4-26b-a4b-it) via google-genai SDK, validates the response
against the AnalysisResult Pydantic model, and returns a validated result.

Key design decisions:
  - Runs without response_schema on GenerateContentConfig to avoid constrained
    decoding timeouts in gemma-4-26b-a4b-it.
  - Employs response_mime_type="application/json" and explicit JSON format prompt.
  - Manually parses and maps returned JSON keys to guarantee structural validity
    and robustly handle minor key name discrepancies.
"""
import json
from google import genai
from google.genai import types

from app.config import settings
from app.models import AnalysisResult, Symbol, Archetype, Emotion
from app.prompts.extractor import build_extractor_prompt

# Initialised once — thread-safe for FastAPI's async context
_client = genai.Client(api_key=settings.gemini_api_key)


def parse_and_map_analysis_result(raw_json_str: str) -> AnalysisResult:
    """
    Robustly parse the JSON string, mapping various key name variations
    sometimes outputted by the model to the expected Pydantic schema keys.
    """
    data = json.loads(raw_json_str)

    # If model wrapped the result in a list/array, extract the first object
    if isinstance(data, list):
        if len(data) > 0:
            data = data[0]
        else:
            raise ValueError("Parsed JSON list is empty")

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data)}")

    # 1. Map symbols
    symbols_raw = data.get("symbols", [])
    if not isinstance(symbols_raw, list):
        symbols_raw = []
    mapped_symbols = []
    for s in symbols_raw:
        if isinstance(s, dict):
            name = s.get("name") or s.get("symbol") or s.get("term") or ""
            category = s.get("category") or "object"
            significance = s.get("significance") or s.get("note") or s.get("meaning") or ""
            mapped_symbols.append(Symbol(name=name, category=category, significance=significance))

    # 2. Map archetypes
    archetypes_raw = data.get("archetypes", [])
    if not isinstance(archetypes_raw, list):
        archetypes_raw = []
    mapped_archetypes = []
    for a in archetypes_raw:
        if isinstance(a, dict):
            name = a.get("name") or a.get("archetype") or ""
            confidence = a.get("confidence")
            try:
                confidence = float(confidence) if confidence is not None else 0.5
            except (ValueError, TypeError):
                confidence = 0.5
            evidence = a.get("evidence") or a.get("citation") or ""
            projection_status = a.get("projection_status") or a.get("type") or a.get("projection") or "ambiguous"
            mapped_archetypes.append(Archetype(
                name=name,
                confidence=confidence,
                evidence=evidence,
                projection_status=projection_status
            ))

    # 3. Map emotions
    emotions_raw = data.get("emotions", [])
    if not isinstance(emotions_raw, list):
        emotions_raw = []
    mapped_emotions = []
    for e in emotions_raw:
        if isinstance(e, dict):
            name = e.get("name") or e.get("emotion") or ""
            valence = e.get("valence")
            try:
                valence = float(valence) if valence is not None else 0.0
            except (ValueError, TypeError):
                valence = 0.0
            intensity = e.get("intensity")
            try:
                intensity = float(intensity) if intensity is not None else 0.5
            except (ValueError, TypeError):
                intensity = 0.5
            mapped_emotions.append(Emotion(name=name, valence=valence, intensity=intensity))

    # 4. Map themes
    themes = data.get("themes", [])
    if not isinstance(themes, list):
        themes = []
    themes = [str(t) for t in themes]

    # 5. Map compensation axis
    compensation_axis = data.get("compensation_axis") or data.get("compensation")
    if compensation_axis is not None:
        compensation_axis = str(compensation_axis)

    # 6. Map ego strength signal
    ego_strength_raw = data.get("ego_strength_signal") or data.get("ego_strength")
    ego_strength_signal = None
    if isinstance(ego_strength_raw, dict):
        ego_strength_raw = ego_strength_raw.get("rating") or ego_strength_raw.get("score")
    if ego_strength_raw is not None:
        try:
            ego_strength_signal = int(ego_strength_raw)
        except (ValueError, TypeError):
            ego_strength_signal = None

    # 7. Map lysis assessment
    lysis_raw = data.get("lysis_assessment")
    lysis_assessment = None
    if isinstance(lysis_raw, dict):
        lysis_raw = lysis_raw.get("status") or lysis_raw.get("value")
    if lysis_raw is not None:
        lysis_assessment = str(lysis_raw).lower()
        if lysis_assessment not in ["resolved", "unresolved", "ambiguous"]:
            lysis_assessment = "ambiguous"

    # 8. Map summary
    jungian_summary = data.get("jungian_summary") or data.get("summary") or ""

    # 9. Map connections to previous
    connections_to_previous = data.get("connections_to_previous") or data.get("connections") or []
    if not isinstance(connections_to_previous, list):
        connections_to_previous = []
    connections_to_previous = [str(c) for c in connections_to_previous]

    return AnalysisResult(
        symbols=mapped_symbols,
        archetypes=mapped_archetypes,
        emotions=mapped_emotions,
        themes=themes,
        compensation_axis=compensation_axis,
        ego_strength_signal=ego_strength_signal,
        lysis_assessment=lysis_assessment,
        jungian_summary=jungian_summary,
        connections_to_previous=connections_to_previous
    )


async def run_extraction(
    raw_text: str,
    entry_type: str,
    previous_entries_summary: str = "",
    personal_associations: str = "",
) -> AnalysisResult:
    """
    Phase 2: Extract Jungian symbols, archetypes, emotions, and themes from one entry.
    personal_associations: optional PERSONAL ASSOCIATIONS block from amplification step.
    Returns a validated AnalysisResult or raises on failure.
    """
    prompt = build_extractor_prompt(
        raw_text,
        entry_type,
        previous_entries_summary,
        personal_associations=personal_associations,
    )

    response = await _client.aio.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            max_output_tokens=1500,
            temperature=0.3,
        ),
    )

    if not response.text:
        raise ValueError("Model returned an empty response.")

    return parse_and_map_analysis_result(response.text)
