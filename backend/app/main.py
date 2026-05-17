"""
FastAPI application factory.
CORS middleware is registered BEFORE routers — order is critical.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import entries, graph, chat
from app.api import arc

app = FastAPI(
    title="Unconscious Mind Mapper API",
    version="0.2.0",
    description=(
        "Jungian symbol analysis, affective topology, individuation arc tracking, "
        "and topology-aware subconscious chat."
    ),
)

# CORS — must come before router registration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health_check():
    return {"status": "ok", "version": "0.2.0"}


app.include_router(entries.router, prefix="/entries", tags=["entries"])
app.include_router(graph.router, prefix="/graph", tags=["graph"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(arc.router, prefix="/arc", tags=["arc"])
