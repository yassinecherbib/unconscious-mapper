"""
Phase 4 — Chat Service

Assembles the persona prompt from topology-retrieved context and
streams the Gemma response token-by-token via SSE.

Context assembly order (critical — do NOT change):
  1. Complexes summaries — structural backbone
  2. Topology-retrieved entry excerpts — specific evidence
  3. User's message — last

Total context budget: keep under 8000 tokens.
"""
from google import genai

from app.config import settings
from app.prompts.persona import build_persona_prompt
from app.services.retrieval import get_topology_context

_client = genai.Client(api_key=settings.gemini_api_key)


async def stream_chat_response(user_id: str, user_message: str, db):
    """
    AsyncGenerator yielding SSE-formatted data lines.
    Frontend reads with fetch + ReadableStream — NOT EventSource.
    """
    # 1. Topology retrieval — seed → edges → entries + complexes
    context = await get_topology_context(user_id, user_message, db)

    # 2. Build persona prompt
    system_prompt, user_turn = build_persona_prompt(
        complexes=context["complexes"],
        retrieved_entries=context["retrieved_entries"],
        user_message=user_message,
    )

    # 3. Stream Gemma response
    try:
        with _client.models.generate_content_stream(
            model="gemma-4-31b-it",
            contents=user_turn,
            config={
                "system_instruction": system_prompt,
                "max_output_tokens": 1000,
                "temperature": 0.7,
            },
        ) as stream:
            for chunk in stream:
                if chunk.text:
                    yield f"data: {chunk.text}\n\n"
    except Exception as exc:
        yield f"data: [ERROR] {str(exc)}\n\n"

    yield "data: [DONE]\n\n"
