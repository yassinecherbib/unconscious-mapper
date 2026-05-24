"""
FastAPI application factory.
CORS middleware is registered BEFORE routers — order is critical.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import entries, graph, chat

app = FastAPI(
    title="Unconscious Mind Mapper API",
    version="0.1.0",
    description="Jungian symbol analysis and topology-based subconscious chat",
)

# CORS — must come before router registration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


app.include_router(entries.router, prefix="/entries", tags=["entries"])
app.include_router(graph.router, prefix="/graph", tags=["graph"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
