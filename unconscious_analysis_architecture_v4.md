# Unconscious Mind Mapper
### System Architecture & Build Plan — Prototype v1

---

## The Big Idea

Most people have no structured relationship with their unconscious mind. Dreams evaporate by morning. Psychedelic insights fade within days. The patterns that repeat across months — the same symbols, the same emotional textures, the same unresolved archetypes surfacing in different costumes — go completely unnoticed because there's no system to hold them.

This project builds that system.

**The core premise:** your unconscious communicates through symbols, archetypes, and emotional patterns. It speaks the same private language across every dream, every altered state, every vision. If you can record that language consistently and analyze it with enough contextual intelligence, patterns emerge that no single entry would reveal on its own.

**What the user experiences:**

1. They submit a dream or psychedelic trip in plain text — no structure required, just raw description
2. The system immediately returns a Jungian analysis: symbols extracted, archetypes identified, emotional valence scored, connections drawn to previous entries
3. Over time, a visual map of their symbolic world builds up — a force-directed graph showing which symbols recur, which archetypes dominate, which themes cluster together
4. After enough entries (7+ over 7+ days), a chat interface unlocks — an AI that has absorbed their entire symbolic history and speaks *from* it, not *about* it. Not a therapist. Not a chatbot. Something closer to a mirror that talks back.

**Why this hasn't been done well before:**
- Generic dream apps give static symbol dictionaries ("water means emotion") — no personalization, no memory, no pattern detection
- Journaling apps have no intelligence layer
- AI chat apps have no longitudinal memory or symbolic framework

This sits at the intersection of all three and uses Jungian methodology as the analytical backbone — the most developed systematic framework for unconscious symbolism that exists.

**What this is not:**
- A therapy tool
- A diagnostic tool
- A replacement for actual psychological work

It is an instrument for self-observation. A long-term mirror.

---

## Design Principles

- **Depth over breadth.** One thing done well: unconscious pattern analysis. No mood tracking, no habit logging, no social features.
- **The user's language, not ours.** The AI adapts to the user's personal symbol system over time, not the other way around.
- **Earn the chat feature.** The subconscious persona is locked until there's enough data to make it meaningful. A chatbot with 2 entries of context is useless. One with 20 entries across 3 months is something else entirely.
- **The AI must be structurally aware, not just text-aware.** The chat feature doesn't retrieve the most recent entries — it retrieves the most *connected* entries. The difference is everything.
- **Privacy is structural.** Dreams are among the most private data a person can generate. Row-level security enforced at the DB. No user ever sees another's data, ever.

---

## The Retrieval Architecture Decision

This section explains a critical design choice that separates a shallow chatbot from a real pattern-detecting mirror.

### Why "Last 20 Entries" Is Wrong

The naive approach — feeding the chat AI the user's most recent entries as context — has a fundamental flaw: **chronological bias**. If a user dreams of a Black Dog in Entry 1 and Entry 47, those two entries are structurally related in the user's unconscious but will never appear in the same context window unless they happen to be recent. The AI is blind to the connection.

Worse, a raw symbol frequency list ("water appears 12 times") tells the AI nothing useful. It doesn't tell the AI that *water* is the bridge between the *Mother* archetype and *Death* themes in this specific user's psyche. Frequency without topology is noise.

### Why Full GraphRAG Is Also Wrong (For Now)

True GraphRAG — Microsoft's implementation, Neo4j-based community detection — is expensive, slow to index, requires asynchronous heavy background processing, and is engineered for datasets orders of magnitude larger than 20-50 dreams per person. It would kill prototype momentum without adding proportional value at this scale.

### The Hybrid Approach: Topology-Based Retrieval + Community Summaries

The solution sits between these two extremes. It uses the SQL edge table (already built for the visual graph) as a *retrieval index*, not just a visual data source. When the chat AI needs context, it doesn't ask "what's recent?" — it asks "what's most connected to what the user is talking about right now?"

This is the architecture used from Phase 4 onward.

---

## 1. System Architecture

### Core Pattern: Modular Monolith

One backend, one database, one frontend. Analysis runs synchronously. No queues, no workers, no separate services. Right-sized for 100 users.

### Component Map

```
┌──────────────────────────────────────────────┐
│                 CLIENT LAYER                 │
│             Next.js Frontend                 │
│  ┌─────────────┐  ┌────────────────────────┐ │
│  │ Dream Input │  │  Symbol Graph (D3.js)  │ │
│  │ & Journal   │  │  visual only           │ │
│  └─────────────┘  └────────────────────────┘ │
│  ┌──────────────────────────────────────────┐ │
│  │       Subconscious Chat (locked)         │ │
│  └──────────────────────────────────────────┘ │
└─────────────────────┬────────────────────────┘
                      │ REST + SSE
┌─────────────────────▼────────────────────────┐
│               FastAPI Backend                │
│                                              │
│  /entries        → ingest + analyze (sync)   │
│  /graph          → symbol map JSON           │
│  /chat/stream    → topology-aware SSE        │
│  /auth           → delegated to Supabase     │
└─────────────────────┬────────────────────────┘
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
    Anthropic Claude API    Supabase PostgreSQL
                            ├── entries (raw + analysis JSONB)
                            ├── symbol_edges (co-occurrence graph)
                            ├── complexes (community summaries)
                            └── Auth (users + unlock state)
```

### Data Flows

**New Entry Submission**
```
User submits dream text
        │
        ▼
FastAPI validates input (Pydantic, max 5000 chars)
        │
        ▼
Claude API — extract symbols, archetypes, emotions, connections
[uses: extractor prompt]
        │
        ▼
Store raw text + analysis JSONB in entries table
        │
        ▼
Upsert symbol co-occurrence pairs into symbol_edges table
(for every pair of symbols in this entry, increment edge weight)
        │
        ▼
Increment user entry_count
        │
        ▼  (every 7 entries, or on first unlock threshold pass)
Run complex detection job (sync, ~2-4s extra)
[uses: complex detection prompt]
Store output in complexes table
        │
        ▼  (if entry_count >= 7 AND days_since_first >= 7)
Set chat_unlocked = true
        │
        ▼
Return full analysis to frontend
```

**Symbol Graph Request (Visual Only)**
```
Frontend requests GET /graph
        │
        ▼
SQL: SELECT from symbol_edges for this user
        │
        ▼
Returns {nodes[], edges[]} — same table, different consumer
        │
        ▼
D3.js renders force-directed graph on client
```

**Subconscious Chat — Topology-Based Retrieval**
```
User sends message
        │
        ▼
Gate check: chat_unlocked verified server-side
        │
        ▼
Extract seed symbols from user's message
[uses: seed extraction prompt — lightweight, no streaming]
        │
        ▼
Query symbol_edges: find top 5 symbols most connected
to any seed symbol by edge weight
        │
        ▼
Fetch all entries containing any of those top symbols
(topology-retrieved entries, not chronological)
        │
        ▼
Fetch user's complexes from complexes table
(pre-computed community summaries — the structural backbone)
        │
        ▼
Assemble persona prompt:
  - complexes summaries (structural backbone)
  - topology-retrieved entry excerpts (specific evidence)
  - user's message
[uses: persona prompt]
        │
        ▼
Claude API — streamed response via SSE
        │
        ▼
Frontend renders token by token
```

### Communication Protocols

| Boundary | Protocol |
|---|---|
| Frontend ↔ Backend | REST (JSON) |
| Chat streaming | Server-Sent Events (SSE) |
| Backend ↔ Claude API | HTTPS REST |
| Backend ↔ Supabase | TCP (asyncpg) |

---

## 2. Technology Stack

| Layer | Technology | Justification |
|---|---|---|
| Backend | Python 3.12 + FastAPI | Async-native, minimal boilerplate, best Anthropic SDK support |
| Frontend | Next.js 14 (App Router) | SSR + React ecosystem; SSE handling is native |
| Styling | TailwindCSS + shadcn/ui | Fast dark UI, zero runtime CSS overhead |
| Graph visualization | D3.js | Force-directed layout for the symbol map |
| Database | Supabase PostgreSQL | Free tier; JSONB + relational edges table handles all retrieval needs at this scale |
| Auth | Supabase Auth | Free; JWT, sessions, email verification out of the box |
| AI | Anthropic Claude API (claude-sonnet-4-20250514) | Best structured extraction and instruction-following for Jungian analysis |
| Deployment | Railway or Render (free/hobby tier) | Zero infra management; deploys from GitHub push |

Everything listed has a free tier sufficient for 100 users.

---

## 3. Repository Structure

```
unconscious-mapper/
│
├── README.md
├── .env.example                        # ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_KEY
├── .gitignore
│
├── backend/
│   ├── pyproject.toml                  # fastapi, anthropic, asyncpg, supabase-py, pydantic
│   │
│   └── app/
│       ├── main.py                     # FastAPI app factory, CORS, route registration
│       ├── config.py                   # Pydantic settings from env vars
│       ├── database.py                 # Supabase client + asyncpg session factory
│       │
│       ├── api/
│       │   ├── entries.py              # POST /entries, GET /entries, GET /entries/{id}
│       │   ├── graph.py                # GET /graph — symbol_edges → D3 JSON
│       │   └── chat.py                 # GET /chat/stream — topology-aware SSE
│       │
│       ├── services/
│       │   ├── analysis.py             # Calls Claude extractor, validates output, returns structured data
│       │   ├── edges.py                # Upserts symbol co-occurrence pairs into symbol_edges after each entry
│       │   ├── complexes.py            # Runs complex detection every 7 entries, stores community summaries
│       │   ├── retrieval.py            # Topology-based retrieval: seed symbols → connected edges → entries
│       │   ├── graph.py                # Reads symbol_edges → D3-compatible {nodes[], edges[]}
│       │   ├── chat.py                 # Assembles prompt from complexes + retrieved entries, streams response
│       │   └── unlock.py               # Gate logic: entry_count + days threshold check
│       │
│       ├── prompts/                    # All prompt templates — isolated, versioned
│       │   ├── extractor.py            # (insert Jungian symbol + archetype extraction prompt here)
│       │   ├── complex_detector.py     # (insert symbolic complex / community detection prompt here)
│       │   ├── seed_extractor.py       # (insert lightweight seed symbol extraction from chat message prompt here)
│       │   └── persona.py              # (insert subconscious persona prompt here)
│       │
│       └── tests/
│           ├── test_analysis.py        # Mocked Claude, tests extraction parsing + Pydantic validation
│           ├── test_edges.py           # Co-occurrence upsert logic
│           ├── test_retrieval.py       # Topology retrieval: given seed symbols, correct entries returned
│           ├── test_complexes.py       # Complex detection output shape
│           └── test_unlock.py          # Gate condition logic
│
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   │
│   └── app/
│       ├── layout.tsx                  # Root layout, dark theme provider
│       ├── page.tsx                    # Landing / onboarding
│       │
│       ├── journal/
│       │   ├── page.tsx                # Entry list + new entry form
│       │   └── [id]/page.tsx           # Single entry: raw text + full analysis display
│       │
│       ├── map/
│       │   └── page.tsx                # D3 symbol graph — the visual map
│       │
│       ├── chat/
│       │   └── page.tsx                # Subconscious chat (locked overlay if gate not passed)
│       │
│       └── components/
│           ├── EntryForm.tsx           # Text input + type selector (dream/psychedelic/meditation)
│           ├── EntryCard.tsx           # Displays symbols, archetypes, jungian summary
│           ├── SymbolGraph.tsx         # D3 force-directed graph wrapper
│           ├── ChatWindow.tsx          # SSE streaming chat UI
│           └── LockedOverlay.tsx       # Gate UI showing progress on both unlock conditions
│
└── docs/
    ├── retrieval-design.md             # Explains topology-based retrieval decisions
    ├── prompt-designs.md               # Prompt engineering decisions and iteration notes
    └── db-schema.md                    # Full table definitions and JSONB shape reference
```

---

## 4. Data Model

### PostgreSQL Tables (via Supabase)

**users** — base managed by Supabase Auth, extended with:
- `entry_count` (int, default 0)
- `chat_unlocked` (bool, default false)
- `first_entry_at` (timestamptz, nullable)
- `created_at` (timestamptz)

**entries**
- `id` (uuid, PK)
- `user_id` (uuid, FK → auth.users)
- `raw_text` (text)
- `entry_type` (enum: dream | psychedelic | meditation)
- `analysis` (JSONB) — full Claude extraction result
- `created_at` (timestamptz)

**symbol_edges** — the retrieval index, dual-purpose: powers the D3 visual AND topology-based chat retrieval
- `id` (uuid, PK)
- `user_id` (uuid, FK)
- `symbol_a` (text)
- `symbol_b` (text)
- `weight` (int) — incremented each time both symbols co-occur in an entry
- `entry_ids` (uuid[]) — array of entry UUIDs where this pair co-occurred
- unique constraint on `(user_id, symbol_a, symbol_b)`

**complexes** — pre-computed community summaries, the structural backbone for chat context
- `id` (uuid, PK)
- `user_id` (uuid, FK)
- `name` (text) — e.g., "The Water-Death-Mirror Cluster"
- `summary` (text) — Claude-generated paragraph describing the complex
- `symbols` (text[]) — the symbol members of this community
- `computed_at` (timestamptz)

**JSONB `analysis` shape** — what Claude must return, validated by Pydantic before any DB write:
```json
{
  "symbols": [
    { "name": "water", "category": "element", "significance": "..." }
  ],
  "archetypes": [
    { "name": "Shadow", "confidence": 0.85, "evidence": "..." }
  ],
  "emotions": [
    { "name": "fear", "valence": -0.7, "intensity": 0.8 }
  ],
  "themes": ["dissolution", "transformation"],
  "jungian_summary": "...",
  "connections_to_previous": ["entry_uuid_1", "entry_uuid_2"]
}
```

### State Management

| Data | Where | Notes |
|---|---|---|
| Raw dream text | PostgreSQL entries | Permanent |
| Claude extraction | PostgreSQL JSONB | Permanent, queryable |
| Symbol co-occurrences | PostgreSQL symbol_edges | Persistent retrieval index + visual source |
| Symbolic complexes | PostgreSQL complexes | Recomputed every 7 entries |
| Chat session history | React state (frontend only) | Not persisted — fresh each session |
| User JWT / session | Supabase Auth | Managed externally |
| Unlock status | PostgreSQL users table | Persistent flag |

### How the Two Consumers Share One Table

`symbol_edges` is read by two completely different consumers for completely different purposes:

- **D3 graph (visual):** reads `symbol_a`, `symbol_b`, `weight` — renders the topology as a force-directed visual for the user's eyes
- **Topology retrieval (AI context):** given seed symbols extracted from a chat message, queries `symbol_edges` to find the top-N most connected neighbors, then fetches `entry_ids` to pull the structurally relevant entries

The visual map and the AI's retrieval index are the same data structure. This is why building the edges table correctly in Phase 2 is the most important structural decision in the whole project.

---

## 5. Non-Functional Requirements

### Deployment

Railway or Render free/hobby tier:
```
Two services:
├── backend   (FastAPI — auto-deploy from /backend on git push)
└── frontend  (Next.js — auto-deploy from /frontend on git push)

Database: Supabase free tier (500MB — sufficient for 100 users)
```

No Docker required locally. Run `uvicorn app.main:app --reload` and `next dev`.

### Performance at 100 Users

| Concern | Reality |
|---|---|
| Claude extraction latency | 3-5s per entry — show a loading state |
| Complex detection (every 7 entries) | Additional 2-4s — run after returning initial analysis, or accept the wait |
| Topology retrieval query | Edge table lookup + entry fetch — under 50ms |
| Concurrent chat sessions | SSE is lightweight; FastAPI async handles it |
| D3 graph render | Client-side, no server cost |

### Security

| Concern | Approach |
|---|---|
| Auth | Supabase JWT on all backend routes |
| Data isolation | Supabase RLS on all tables — users can only access their own rows |
| Input validation | Pydantic on all inputs; 5000 char max on entry text |
| API key safety | Anthropic key backend-only, never exposed to frontend |
| Rate limiting | 5 entries per user per hour — checked in FastAPI before Claude call |
| Prompt injection | User text always passed as data content, never interpolated into system instructions |

### CI/CD

```
GitHub push → Railway/Render auto-deploy
```

---

## 6. Prompts Reference

All prompts live in `backend/app/prompts/`. Each file exports a function accepting runtime variables and returning a complete prompt string ready to send to Claude.

| File | Purpose | Template Variables | Placeholder |
|---|---|---|---|
| `extractor.py` | Extract symbols, archetypes, emotions, themes from one entry. Return strict JSON. | `raw_text`, `entry_type`, `previous_entries_summary` | (insert Jungian extraction prompt here) |
| `complex_detector.py` | Given the full edge list for a user, identify 3-5 symbolic complexes (clusters). Name and describe each as a Jungian complex. Return strict JSON. | `edge_list`, `archetype_history` | (insert symbolic complex detection prompt here) |
| `seed_extractor.py` | Given a chat message from the user, extract the 1-3 most symbolically significant terms to use as retrieval seeds. Lightweight, fast, no streaming. Return a plain JSON array. | `user_message`, `known_symbols` | (insert seed symbol extraction prompt here) |
| `persona.py` | Given the user's complexes and topology-retrieved entry excerpts, respond to their message speaking as their subconscious. Stream response. | `complexes[]`, `retrieved_entries[]`, `user_message` | (insert subconscious persona prompt here) |

**Extraction prompt requirements:**
- Return only valid JSON matching the analysis schema — no markdown, no preamble
- Use Jungian framework explicitly (Shadow, Anima/Animus, Self, Persona, Trickster, etc.)
- Reference previous entries by UUID when drawing connections — never invent connections
- If no meaningful connections exist, return an empty `connections_to_previous` array

**Complex detection prompt requirements:**
- Input is the full `symbol_edges` list as `[(symbol_a, symbol_b, weight), ...]`
- Output is 3-5 named complexes, each with: `name`, `summary`, `symbols[]`
- Names should feel archetypal, not clinical — "The Drowning-Mother Cluster", not "Cluster A"
- Each summary should read as a paragraph a Jungian analyst might write about this pattern

**Seed extractor prompt requirements:**
- Must be fast — this runs synchronously before the chat retrieval step
- Returns a plain JSON array of 1-3 symbol strings: `["water", "mirror"]`
- Should match to symbols already known in the user's history where possible

**Persona prompt requirements:**
- Speak in first person as the user's unconscious — not as an analyst talking *about* them
- Ground every statement in specific symbols and complexes from their history
- Do not give advice, make diagnoses, or resolve ambiguity
- The unconscious surfaces questions, not answers

---

## 7. Unlock Gate

| Condition | Value | Rationale |
|---|---|---|
| Minimum entries | 7 | Enough symbolic data for complex detection to find real clusters |
| Minimum days since first entry | 7 | Prevents bulk-entry gaming; temporal spread is structurally meaningful |

Both must pass simultaneously. Checked in `unlock.py` after every successful entry submission. When both pass for the first time, `chat_unlocked = true` is written and the frontend gate lifts permanently.

---

## 8. Build Phases

Four sequential phases. Each ends in a working state. Hand each to your coding agent as a self-contained unit.

---

### Phase 1 — Foundation & Auth
**Goal:** Working app shell with auth, database schema, and plain entry storage. No AI.

**Deliverables:**
- Supabase project with all four tables created: `users` (extended), `entries`, `symbol_edges`, `complexes`
- RLS enabled on all tables from day one
- FastAPI: `POST /entries` stores raw text, `GET /entries` returns list, `GET /entries/{id}` returns single entry
- Next.js: landing page, register/login via Supabase Auth, journal page with entry form and entry list
- `.env.example` fully documented
- Both services deploy to Railway/Render successfully

**Agent instructions:**
- Create the full repo structure as defined in Section 3
- Implement Supabase Auth in Next.js using `@supabase/ssr`
- `POST /entries`: Pydantic validation → insert to entries table → return entry id. No AI yet. `analysis` stores `null`.
- Enable RLS on `entries`, `symbol_edges`, `complexes`: policy is `user_id = auth.uid()` for all operations
- `symbol_edges` unique constraint: `(user_id, symbol_a, symbol_b)` — enforced at DB level
- No Claude, no edges, no complexes in this phase

---

### Phase 2 — AI Extraction + Edge Building
**Goal:** Every entry is analyzed by Claude. Symbols are extracted and immediately written into the edges table. This phase builds the retrieval index that everything in Phase 4 depends on.

**Deliverables:**
- `extractor.py` with placeholder: (insert Jungian extraction prompt here)
- `analysis.py` service: calls Claude, parses JSON, validates against Pydantic schema
- `edges.py` service: after successful analysis, iterates all symbol pairs in the entry, upserts into `symbol_edges` (increment weight, append entry_id to array)
- `POST /entries` pipeline: validate → store raw → Claude extraction → store analysis JSONB → upsert edges → return
- `GET /entries/{id}` returns full entry with analysis
- Frontend `EntryCard.tsx`: displays symbols, archetypes, emotions, jungian_summary
- `/journal/[id]` page: full analysis breakdown view
- Loading state on submit

**Agent instructions:**
- Use `anthropic` Python SDK — not raw HTTP
- Claude must be instructed to return JSON-only, no markdown fences, no preamble
- Parse Claude response in try/except — if malformed JSON, store `{"error": "parse_failed"}` in analysis field, surface gracefully in UI
- Validate parsed JSON against Pydantic before any DB write — malformed AI output must never reach the database
- Edge upsert logic in `edges.py`: for a symbols list `[A, B, C]`, generate pairs `(A,B), (A,C), (B,C)`. Always store the pair in alphabetical order to prevent duplicates `(water, fire)` vs `(fire, water)`
- On upsert conflict `(user_id, symbol_a, symbol_b)`: increment `weight` by 1, append current `entry_id` to `entry_ids` array
- `extractor.py` prompt function signature: `build_extractor_prompt(raw_text, entry_type, previous_entries_summary) -> str`

---

### Phase 3 — Symbol Map (Visual)
**Goal:** The D3 graph renders the symbol_edges table as an interactive visual. The same data structure that will power retrieval in Phase 4 becomes visible to the user here.

**Deliverables:**
- `GET /graph` endpoint: reads `symbol_edges` for the user, returns `{nodes[], edges[]}`
- `graph.py` service: aggregates node frequencies from edges, returns D3-compatible JSON
- Frontend `/map` page with `SymbolGraph.tsx`: force-directed graph, nodes sized by total connection weight, edges weighted by co-occurrence
- Node hover tooltip: symbol name, total frequency, connected archetypes
- Nav link to map appears after first entry

**Agent instructions:**
- Nodes derived from edges table: collect all unique symbol names, sum their total edge weights as the node `value`
- Edges: each `symbol_edges` row becomes a D3 link with `source`, `target`, `value` (weight)
- D3 `forceSimulation`: `forceManyBody` (repulsion), `forceLink` (edges), `forceCenter`
- Node radius: `Math.sqrt(value) * 4` — prevents dominant nodes from overwhelming the canvas
- Edge opacity: normalize weight to 0.15–0.9 range across all edges for this user
- Color nodes by the archetype most frequently associated with that symbol across entries (pull from analysis JSONB)
- This page is explicitly a visual tool for the user — it is not the AI's retrieval mechanism

---

### Phase 4 — Topology-Based Retrieval + Subconscious Chat
**Goal:** The chat feature unlocks. The AI retrieves context through graph topology — not chronology — and speaks as the user's subconscious grounded in their symbolic complexes.

**Deliverables:**
- `complex_detector.py` prompt with placeholder: (insert symbolic complex detection prompt here)
- `complexes.py` service: every 7 entries, reads full `symbol_edges` for user, calls Claude to detect 3-5 complexes, stores results in `complexes` table — runs synchronously at end of entry pipeline
- `seed_extractor.py` prompt with placeholder: (insert seed symbol extraction from chat message prompt here)
- `retrieval.py` service:
  1. Call Claude with seed_extractor prompt to get 1-3 seed symbols from the user's message
  2. Query `symbol_edges` for top 5 symbols most connected to any seed (highest edge weight sum)
  3. Collect all `entry_ids` from those edges
  4. Fetch and return those entries (deduplicated)
- `persona.py` prompt with placeholder: (insert subconscious persona prompt here)
- `chat.py` service: fetch complexes → run retrieval → assemble persona prompt → stream Claude response
- `unlock.py` service: `entry_count >= 7` AND `days_since_first_entry >= 7` → set `chat_unlocked = true`
- `GET /chat/stream` SSE endpoint: gate check → topology retrieval → stream
- Frontend `/chat` page:
  - `chat_unlocked = false`: `LockedOverlay.tsx` showing both conditions with live progress counts
  - `chat_unlocked = true`: `ChatWindow.tsx` with SSE streaming
- Chat history in React state only — not persisted

**Agent instructions:**
- Gate check is always server-side — never trust frontend state
- SSE endpoint: FastAPI `StreamingResponse` with `text/event-stream` content type
- Persona prompt context assembly order: (1) complexes summaries first — structural backbone, (2) topology-retrieved entry excerpts — specific evidence, (3) user's message last
- Keep total context under 8000 tokens: summarize retrieved entries to 2-3 sentences each, not full raw text
- `LockedOverlay.tsx` must show both conditions with specific counts: "5 of 7 entries" and "3 of 7 days" — never a vague lock message
- Complex detection runs every 7 entries (when `entry_count % 7 == 0`). It overwrites previous complexes — don't accumulate stale rows
- `retrieval.py` signature: `get_topology_context(user_id, user_message, db) -> {retrieved_entries[], complexes[]}` — returns everything `chat.py` needs in one call
- Seed extractor is a fast, non-streaming Claude call — target under 1s. Use `max_tokens=100`
