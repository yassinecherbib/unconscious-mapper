# AGENT RULES — Unconscious Mind Mapper
### Read this entire file before writing a single line of code.

This file is the implementation contract. Every rule here exists because the alternative causes a debugging spiral. Do not skip sections. Do not assume you know better than what's written.

---

## 0. Meta Rules

- **Read the architecture doc first.** The file `unconscious_analysis_architecture_v4.md` is the source of truth for what to build. These rules are *how* to build it without breaking things.
- **One phase at a time.** Do not implement Phase 3 logic while building Phase 1. Each phase must be complete and manually testable before moving on.
- **Never invent structure.** If a field, table, or service isn't in the architecture doc or these rules, ask before adding it.
- **Failing loudly is better than failing silently.** Every error must surface visibly — to logs, to the API response, or to the UI. Silent failures (swallowed exceptions, unchecked nulls) are the #1 source of hours-long debugging sessions in this project.
- **Test the pipeline end-to-end after every phase** before declaring it done. Submit a real entry, check the DB, check the response.

---

## 1. Project Setup

### Environment Variables

Create `.env` at the repo root and `.env.example` alongside it. Never commit `.env`.

Required keys:
```
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
```

Use `SUPABASE_SERVICE_ROLE_KEY` on the backend only (bypasses RLS for admin operations like incrementing `entry_count`). Use `SUPABASE_ANON_KEY` on the frontend (respects RLS).

Never expose `SUPABASE_SERVICE_ROLE_KEY` or `ANTHROPIC_API_KEY` to the frontend. Ever.

### Python Backend

Use `pyproject.toml` with these exact dependencies — do not upgrade without testing:
```
fastapi
uvicorn[standard]
anthropic
supabase
asyncpg
pydantic
pydantic-settings
python-jose[cryptography]
httpx
```

Run with: `uvicorn app.main:app --reload --port 8000`

### Next.js Frontend

Initialize with App Router. Install:
```
@supabase/ssr
@supabase/supabase-js
d3
```

Do not use the Pages Router. Do not mix `@supabase/auth-helpers-nextjs` (deprecated) with `@supabase/ssr`. Use only `@supabase/ssr`.

---

## 2. Database Rules

### Supabase Table Creation Order

Create tables in this exact order — foreign key dependencies require it:
1. `users` extension (add columns to `auth.users` via a `profiles` table — see below)
2. `entries`
3. `symbol_edges`
4. `complexes`

### The Profiles Table Pattern

Supabase Auth owns `auth.users`. Do not try to add columns to it directly. Instead, create a `profiles` table in the `public` schema:

```
profiles
  id              uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE
  entry_count     integer DEFAULT 0 NOT NULL
  chat_unlocked   boolean DEFAULT false NOT NULL
  first_entry_at  timestamptz
  created_at      timestamptz DEFAULT now()
```

Create a Supabase database trigger that auto-inserts a `profiles` row whenever a new `auth.users` row is created. Without this trigger, users will exist in auth but have no profile row, and every query to `profiles` will return null.

The trigger function (run in Supabase SQL editor):
```sql
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id)
  VALUES (new.id);
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
```

### The entries Table

```
entries
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid()
  user_id     uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE
  raw_text    text NOT NULL
  entry_type  text NOT NULL CHECK (entry_type IN ('dream', 'psychedelic', 'meditation'))
  analysis    jsonb
  created_at  timestamptz DEFAULT now() NOT NULL
```

`analysis` is nullable — it stores `null` until Claude processes it, and `{"error": "parse_failed"}` if Claude returns malformed JSON.

### The symbol_edges Table

This is the most critical table. Get the schema exactly right.

```
symbol_edges
  id        uuid PRIMARY KEY DEFAULT gen_random_uuid()
  user_id   uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE
  symbol_a  text NOT NULL
  symbol_b  text NOT NULL
  weight    integer DEFAULT 1 NOT NULL
  entry_ids uuid[] DEFAULT '{}' NOT NULL
  UNIQUE (user_id, symbol_a, symbol_b)
```

**The alphabetical ordering rule:** Before any insert or upsert into `symbol_edges`, always sort the pair so that `symbol_a < symbol_b` lexicographically. This is the only way the unique constraint works correctly. `('fire', 'water')` and `('water', 'fire')` are the same edge. If you don't enforce alphabetical order in application code, you will get duplicate rows, and the unique constraint won't catch them.

```python
# Always do this before upsert
symbol_a, symbol_b = sorted([sym1, sym2])
```

**The upsert logic:** On conflict `(user_id, symbol_a, symbol_b)`, increment `weight` by 1 and append the current entry's UUID to `entry_ids`. In PostgreSQL:
```sql
INSERT INTO symbol_edges (user_id, symbol_a, symbol_b, weight, entry_ids)
VALUES ($1, $2, $3, 1, ARRAY[$4]::uuid[])
ON CONFLICT (user_id, symbol_a, symbol_b)
DO UPDATE SET
  weight = symbol_edges.weight + 1,
  entry_ids = array_append(symbol_edges.entry_ids, $4);
```

### The complexes Table

```
complexes
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid()
  user_id      uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE
  name         text NOT NULL
  summary      text NOT NULL
  symbols      text[] NOT NULL
  computed_at  timestamptz DEFAULT now() NOT NULL
```

When recomputing complexes (every 7 entries), delete all existing rows for the user first, then insert fresh ones. Do not accumulate stale complex rows.

### Row Level Security — Enable On Every Table, Day One

Run these in Supabase SQL editor for each table. Do not skip this step and plan to do it later.

```sql
-- profiles
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own profile" ON profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON profiles FOR UPDATE USING (auth.uid() = id);

-- entries
ALTER TABLE entries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can insert own entries" ON entries FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can view own entries" ON entries FOR SELECT USING (auth.uid() = user_id);

-- symbol_edges
ALTER TABLE symbol_edges ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own edges" ON symbol_edges FOR SELECT USING (auth.uid() = user_id);

-- complexes
ALTER TABLE complexes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own complexes" ON complexes FOR SELECT USING (auth.uid() = user_id);
```

The backend uses the service role key which bypasses RLS for writes. The frontend uses the anon key which is subject to RLS. This is intentional.

---

## 3. FastAPI Backend Rules

### App Structure

`main.py` must:
- Create the FastAPI app instance
- Add CORS middleware allowing `http://localhost:3000` (and production URL when deployed)
- Include all routers
- Not contain any business logic

```python
# CORS must come before routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Authentication on Every Route

Every backend route except health checks must validate the Supabase JWT. Create a dependency `get_current_user` in `dependencies.py` that:
1. Reads the `Authorization: Bearer <token>` header
2. Calls `supabase.auth.get_user(token)` to validate
3. Returns the user object, or raises `HTTPException(401)`

Never decode the JWT manually. Let Supabase validate it.

```python
async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")
    token = authorization.split(" ")[1]
    try:
        user = supabase.auth.get_user(token)
        return user.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
```

Apply to all protected routes: `user = Depends(get_current_user)`

### The Entry Submission Pipeline (`POST /entries`)

This is the most complex route. It must execute in this exact order:

1. Validate input with Pydantic
2. Insert raw entry to DB (get the UUID back)
3. Call `analysis.py` → Claude extraction
4. Update the entry row with the analysis JSONB result
5. Call `edges.py` → upsert all symbol pairs from the analysis
6. Call `unlock.py` → check gate conditions, update profile if needed
7. Check if complex detection should run (`entry_count % 7 == 0`)
8. If yes, call `complexes.py` → detect and store complexes
9. Return the full entry (raw text + analysis) to the frontend

**If step 3 fails** (Claude error or parse failure): store `{"error": "parse_failed", "detail": str(e)}` in the analysis field. Skip steps 4-8. Return the entry with the error in the analysis field. Do not return a 500. The entry is saved, the analysis failed — the user should know this gracefully.

**If step 5 fails** (edge upsert error): log the error but do not fail the request. The entry and analysis are saved. Edge building is recoverable.

**Never return a 500** for a Claude failure. The Claude API will occasionally timeout or return unexpected content. Handle it.

### Pydantic Models

Define these in `app/models/` or inline in service files. The most important one:

```python
class Symbol(BaseModel):
    name: str
    category: str
    significance: str

class Archetype(BaseModel):
    name: str
    confidence: float
    evidence: str

class Emotion(BaseModel):
    name: str
    valence: float  # -1.0 to 1.0
    intensity: float  # 0.0 to 1.0

class AnalysisResult(BaseModel):
    symbols: list[Symbol]
    archetypes: list[Archetype]
    emotions: list[Emotion]
    themes: list[str]
    jungian_summary: str
    connections_to_previous: list[str]  # list of entry UUIDs
```

If Claude's response fails Pydantic validation, catch the `ValidationError`, log it with the raw response, and raise it up to the route handler to store as `{"error": "validation_failed"}`.

### SSE Streaming for Chat

Use FastAPI's `StreamingResponse` with `media_type="text/event-stream"`:

```python
async def event_generator():
    async with anthropic_client.messages.stream(...) as stream:
        async for text in stream.text_stream:
            yield f"data: {text}\n\n"
    yield "data: [DONE]\n\n"

return StreamingResponse(event_generator(), media_type="text/event-stream")
```

The frontend listens for `[DONE]` to know the stream has ended. Do not omit this sentinel.

Add these headers to the SSE response to prevent buffering:
```python
headers = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}
```

### Rate Limiting

Implement a simple in-memory rate limiter in `dependencies.py`. No Redis needed at 100 users:

```python
from collections import defaultdict
from datetime import datetime, timedelta

entry_timestamps: dict[str, list[datetime]] = defaultdict(list)

def check_rate_limit(user_id: str):
    now = datetime.utcnow()
    window = now - timedelta(hours=1)
    entry_timestamps[user_id] = [t for t in entry_timestamps[user_id] if t > window]
    if len(entry_timestamps[user_id]) >= 5:
        raise HTTPException(status_code=429, detail="Rate limit: 5 entries per hour")
    entry_timestamps[user_id].append(now)
```

Apply before the Claude call in `POST /entries`.

---

## 4. Claude API Rules

### Always Use the SDK, Never Raw HTTP

```python
from anthropic import Anthropic
client = Anthropic(api_key=settings.anthropic_api_key)
```

### Extraction Call Pattern

```python
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1500,
    system="You are a Jungian analyst...",  # static system prompt
    messages=[
        {"role": "user", "content": prompt}  # user text always in user turn
    ]
)
raw_text = response.content[0].text
```

### JSON Extraction — The Parsing Chain

Claude will occasionally wrap JSON in markdown fences despite instructions. Handle it:

```python
import json, re

def parse_claude_json(raw: str) -> dict:
    # Strip markdown fences if present
    cleaned = re.sub(r'^```(?:json)?\n?', '', raw.strip())
    cleaned = re.sub(r'\n?```$', '', cleaned.strip())
    return json.loads(cleaned)
```

Wrap in try/except. If `json.loads` fails, log `raw` in full (truncated to 500 chars) and raise.

### User Text Is Always Data, Never Instructions

The extraction prompt structure must follow this pattern:

```
SYSTEM: [static Jungian analyst instructions — never changes]

USER:
Entry type: {entry_type}
Entry text:
---
{raw_text}
---
Previous context: {previous_summary}

Return only JSON. No explanation. No markdown.
```

The `raw_text` must be sandwiched between `---` delimiters and placed in the user turn. Never interpolate user text into the system prompt. This prevents prompt injection from dream content.

### Streaming Call Pattern (Chat Only)

```python
with client.messages.stream(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    system=persona_system_prompt,
    messages=[{"role": "user", "content": user_message}]
) as stream:
    for text in stream.text_stream:
        yield f"data: {text}\n\n"
```

### Token Budget

| Call | max_tokens | Why |
|---|---|---|
| Extraction | 1500 | JSON output is structured and bounded |
| Seed extraction | 100 | Returns a tiny JSON array |
| Complex detection | 2000 | 3-5 complexes with summaries |
| Persona chat | 1000 | Conversational response |

Do not set `max_tokens` higher than needed. It costs money and slows responses.

---

## 5. Topology Retrieval Rules

This is the logic that makes the chat feature meaningful. Get it right.

### The Retrieval Pipeline (in `retrieval.py`)

```
Step 1: Extract seed symbols from user message
  → lightweight Claude call (seed_extractor prompt)
  → returns list of 1-3 symbol strings
  → if Claude fails here, fall back to splitting user message into words
    and matching against known symbols in the user's symbol_edges table

Step 2: Find connected symbols
  → for each seed symbol, query symbol_edges WHERE symbol_a = seed OR symbol_b = seed
  → collect all neighbor symbols with their weights
  → rank by weight descending
  → take top 5 unique neighbor symbols

Step 3: Collect entry IDs
  → from all matching symbol_edges rows (seed + top neighbors),
    collect all entry_ids arrays and flatten + deduplicate

Step 4: Fetch entries
  → SELECT id, raw_text, analysis->>'jungian_summary', created_at
    FROM entries WHERE id = ANY($entry_ids) AND user_id = $user_id
  → return these entries as the retrieved context

Step 5: Fetch complexes
  → SELECT * FROM complexes WHERE user_id = $user_id ORDER BY computed_at DESC
  → return all (usually 3-5 rows)
```

### Fallback When Not Enough Edges Exist

Early users (entries 7-15) may not have a rich edge graph yet. If topology retrieval returns fewer than 3 entries, supplement with the most recent entries up to a total of 5. Do not return zero context to the persona prompt.

### What Gets Injected Into the Persona Prompt

Assemble in this order:

```
1. Complexes (all of them) — the structural backbone:
   "Your symbolic complexes are:
   - The Water-Death-Mirror Cluster: [summary]
   - The Shadow-Fire Cluster: [summary]"

2. Retrieved entry excerpts — specific evidence (jungian_summary only, not raw_text):
   "Relevant entries from your history:
   - [date]: [jungian_summary]
   - [date]: [jungian_summary]"

3. User's message — last:
   "The user says: [message]"
```

Total context budget: keep under 6000 tokens to leave 1000 for the response and 1000 buffer.

---

## 6. Frontend Rules

### Supabase Auth in Next.js (App Router)

Use `@supabase/ssr`. Create two client utilities:

`lib/supabase/client.ts` — for use in Client Components:
```typescript
import { createBrowserClient } from '@supabase/ssr'
export const createClient = () =>
  createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
```

`lib/supabase/server.ts` — for use in Server Components and middleware:
```typescript
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
export const createClient = () =>
  createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { get: (name) => cookies().get(name)?.value } }
  )
```

Create `middleware.ts` at the repo root to refresh sessions on every request. Without this, auth tokens expire and users get silently logged out.

### Sending Auth Token to the Backend

Every fetch to the FastAPI backend must include the JWT:

```typescript
const { data: { session } } = await supabase.auth.getSession()
const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/entries`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${session?.access_token}`
  },
  body: JSON.stringify(payload)
})
```

If `session` is null, redirect to login. Never send a request without a token to a protected route.

### SSE Chat — EventSource Pattern

Browser `EventSource` doesn't support custom headers, so the JWT cannot be sent that way. Use `fetch` with a `ReadableStream` instead:

```typescript
const response = await fetch(`${API_URL}/chat/stream`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${session?.access_token}`
  },
  body: JSON.stringify({ message: userMessage })
})

const reader = response.body!.getReader()
const decoder = new TextDecoder()

while (true) {
  const { done, value } = await reader.read()
  if (done) break
  const chunk = decoder.decode(value)
  const lines = chunk.split('\n')
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const text = line.slice(6)
      if (text === '[DONE]') return
      setMessages(prev => /* append text to last message */)
    }
  }
}
```

Do not use `EventSource`. It will not work with JWT auth.

### D3 Graph in React

D3 mutates the DOM directly. React also mutates the DOM. They will fight if you let them. Use a `useRef` to give D3 a DOM node to own entirely:

```typescript
const svgRef = useRef<SVGSVGElement>(null)

useEffect(() => {
  if (!svgRef.current || !graphData) return
  const svg = d3.select(svgRef.current)
  svg.selectAll("*").remove()  // clear before redraw
  // ... all D3 code here
}, [graphData])

return <svg ref={svgRef} width="100%" height="600" />
```

- Clear the SVG on every redraw with `svg.selectAll("*").remove()`
- Never put D3 logic outside the `useEffect`
- Never let React render children inside the SVG that D3 manages

### Environment Variables in Next.js

Variables exposed to the browser must be prefixed with `NEXT_PUBLIC_`:
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Variables without `NEXT_PUBLIC_` are server-only and will be `undefined` in client components. Do not put `ANTHROPIC_API_KEY` or `SUPABASE_SERVICE_ROLE_KEY` in `NEXT_PUBLIC_` variables.

---

## 7. The Edge Building Logic (Critical)

This is isolated because it's the most failure-prone piece.

### Symbol Pair Generation

Given a symbols list from one entry analysis: `["water", "fire", "shadow", "mirror"]`

Generate all unique pairs:
```python
from itertools import combinations

def get_symbol_pairs(symbols: list[str]) -> list[tuple[str, str]]:
    names = [s.name for s in symbols]  # extract name strings
    pairs = []
    for a, b in combinations(names, 2):
        # Always alphabetical order
        pairs.append(tuple(sorted([a, b])))
    return pairs
```

For 4 symbols this produces 6 pairs. For 10 symbols it produces 45 pairs. Entries with very many extracted symbols can produce many pairs — this is fine, it's the intended behavior.

### What To Do If an Entry Has Only 1 Symbol

Skip edge upsert entirely. You need at least 2 symbols to form a pair. Do not error.

### What To Do If an Entry Has 0 Symbols

The extraction failed to find meaningful symbols. This is valid for very short or vague entries. Store the analysis as-is (empty symbols array), skip edge upsert, log a warning. Do not error.

---

## 8. Complex Detection Rules

### When to Run

At the end of `POST /entries`, after incrementing `entry_count`:
- If `entry_count % 7 == 0` (i.e., entry 7, 14, 21, 28...): run complex detection
- Also run on the first unlock threshold pass (entry 7 with >= 7 days) if not already run

### What to Send to Claude

Fetch the full edge list for the user:
```sql
SELECT symbol_a, symbol_b, weight FROM symbol_edges
WHERE user_id = $1 ORDER BY weight DESC
```

Format it as a plain text list for the prompt:
```
water — death: 8 co-occurrences
water — mirror: 6 co-occurrences
fire — shadow: 5 co-occurrences
...
```

### What Claude Returns

Instruct it to return JSON only:
```json
[
  {
    "name": "The Water-Death-Mirror Cluster",
    "summary": "...",
    "symbols": ["water", "death", "mirror"]
  }
]
```

Validate with Pydantic before storing.

### Storage

Delete existing complexes for this user, then insert fresh:
```sql
DELETE FROM complexes WHERE user_id = $1;
-- then insert new rows
```

---

## 9. Common Failure Modes to Prevent

| Failure | Prevention |
|---|---|
| Claude returns JSON wrapped in ` ```json ``` ` | Strip markdown fences before `json.loads()` — always |
| Symbol pair `(water, fire)` and `(fire, water)` both inserted | Sort pairs alphabetically before upsert — always |
| Profile row missing for new user | Auto-create via DB trigger on `auth.users` insert |
| RLS blocks backend writes | Backend uses service role key — never the anon key for writes |
| `EventSource` fails to send auth token | Use `fetch` + `ReadableStream` for SSE — never `EventSource` |
| D3 and React fight over the SVG DOM | D3 owns the `ref` node entirely; clear with `selectAll("*").remove()` on every render |
| `entry_ids` array grows with duplicate UUIDs | The `ON CONFLICT` upsert appends per entry submission — one entry = one append. This is correct. |
| Complex detection runs on entry 7 but edges aren't built yet | Edges are built in step 5, complex detection runs in step 8 — order is enforced by pipeline sequence |
| Chat returns 200 but streams nothing | Check `X-Accel-Buffering: no` header on SSE response |
| Supabase session expires silently | Add `middleware.ts` to refresh tokens on every Next.js request |
| CORS error on first backend call | CORS middleware must be registered before routers in `main.py` |
| Pydantic v1 vs v2 model syntax | This project uses Pydantic v2. Use `model_validate()` not `.parse_obj()`. Use `model_dump()` not `.dict()` |

---

## 10. Definition of Done — Per Phase

### Phase 1 is done when:
- [ ] A new user can register, log in, and see their (empty) journal
- [ ] A user can submit a dream entry (plain text, no analysis yet)
- [ ] The entry appears in their journal list
- [ ] A second user cannot see the first user's entries (RLS verified manually in Supabase table editor)
- [ ] Both backend and frontend deploy successfully to Railway/Render

### Phase 2 is done when:
- [ ] Submitting an entry triggers Claude and returns a structured analysis within 10s
- [ ] The analysis (symbols, archetypes, emotions, jungian_summary) displays correctly in the UI
- [ ] If Claude fails, the UI shows a graceful error — not a blank screen or a 500
- [ ] `symbol_edges` table has rows after submitting 2+ entries with overlapping symbols
- [ ] Alphabetical ordering of edge pairs is verified in the DB (`symbol_a` < `symbol_b` always)

### Phase 3 is done when:
- [ ] `/map` page renders a D3 graph with nodes and edges
- [ ] Nodes are sized by connection weight
- [ ] Hovering a node shows its name and frequency
- [ ] The graph updates when a new entry is submitted (page refresh is fine)

### Phase 4 is done when:
- [ ] Chat is locked (shows progress overlay) until both unlock conditions pass
- [ ] The overlay shows specific counts: "5/7 entries" and "3/7 days"
- [ ] Chat unlocks permanently once both conditions pass
- [ ] Chat responses stream token by token visibly
- [ ] Submitting a message that contains a known symbol (e.g., "water") returns a response grounded in water-related entries, not just the most recent entries
- [ ] Complexes are stored in the DB after entry 7 and visible in the chat context (verify via logs)
- [ ] Gate check happens server-side — manually test by sending a request without the unlock flag set

---

## 11. Deployment Checklist

### Railway / Render

Backend service:
- Build command: `pip install -e .` or `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Set all env vars in the Railway/Render dashboard

Frontend service:
- Framework: Next.js (auto-detected)
- Set `NEXT_PUBLIC_API_URL` to the deployed backend URL (not `localhost`)
- Set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### Supabase

- Enable email auth in Supabase Auth dashboard
- Disable email confirmation for prototype (Settings → Auth → Email → Disable "Confirm email")
- Add the deployed frontend URL to Supabase Auth's allowed redirect URLs

### CORS Update

When deploying, update the FastAPI CORS `allow_origins` to include the production frontend URL alongside localhost. Hardcode it — do not use `allow_origins=["*"]` in production.
