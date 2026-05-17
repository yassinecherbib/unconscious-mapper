# edits.md
# Unconscious Mind Mapper — Full System Edits
# All changes required to integrate the new prompt system end-to-end

---

## How to read this file

Each section is ordered by build phase. Within each section:
- **DB changes** run first (Supabase SQL editor)
- **Backend changes** run second
- **Frontend changes** run last

Prompt files that have been fully rewritten are referenced by filename only.
Code blocks appear only where the change is a specific snippet, not a full file replacement.

---

## Prompt files — drop these in directly

All live in `backend/app/prompts/`.

| File | Action | Condition |
|------|--------|-----------|
| `extractor.py` | Replace existing | None — pure drop-in |
| `seed_extractor.py` | Replace existing | None — pure drop-in |
| `persona.py` | Replace existing | None — pure drop-in |
| `complex_detector.py` | Replace existing | Changes 1–3 must be done first or affective fields arrive empty |
| `amplification.py` | Add new file | New — does not exist yet |
| `longitudinal_analyzer.py` | Add new file | New — does not exist yet |
| `integration_risk.py` | Add new file | New — does not exist yet |

One file goes in `services/`, not `prompts/`:

| File | Action | Destination |
|------|--------|-------------|
| `season_detector.py` | Add new file | `backend/app/services/season_detector.py` — pure Python signal logic, no Claude call |

---

## Phase 1 — Database schema changes

Run all of these in the Supabase SQL editor before touching any code.

### 1.1 — symbol_edges: add affective columns

```sql
ALTER TABLE symbol_edges
  ADD COLUMN avg_intensity    FLOAT  DEFAULT 0.0,
  ADD COLUMN avg_valence      FLOAT  DEFAULT 0.0,
  ADD COLUMN dominant_emotion TEXT   DEFAULT NULL,
  ADD COLUMN emotion_counts   JSONB  DEFAULT '{}'::jsonb;
```

Existing rows get `avg_intensity = 0.0`. The complex detector treats these as
inert — correct behavior. Do not backfill.

### 1.2 — complexes: add new output fields

```sql
ALTER TABLE complexes
  ADD COLUMN overdetermined_symbols  TEXT[]   DEFAULT ARRAY[]::TEXT[],
  ADD COLUMN affective_core          TEXT     DEFAULT NULL,
  ADD COLUMN projection_status       TEXT     DEFAULT 'ambiguous',
  ADD COLUMN golden_shadow           BOOLEAN  DEFAULT FALSE,
  ADD COLUMN golden_shadow_owned     BOOLEAN  DEFAULT FALSE,
  ADD COLUMN individuation_note      TEXT     DEFAULT NULL;
```

These are returned by the new `complex_detector.py` and consumed by `persona.py`.
Without them, the persona prompt receives null for projection status and golden shadow flags.

### 1.3 — users: add longitudinal tracking column

```sql
ALTER TABLE users
  ADD COLUMN last_longitudinal_at TIMESTAMPTZ DEFAULT NULL;
```

Updated after every successful longitudinal analysis run.

### 1.4 — New table: personal_symbol_associations

```sql
CREATE TABLE personal_symbol_associations (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        REFERENCES auth.users NOT NULL,
    symbol       TEXT        NOT NULL,
    association  TEXT        NOT NULL,
    entry_id     UUID        REFERENCES entries(id),
    created_at   TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, symbol)
    -- ON CONFLICT (user_id, symbol) DO UPDATE SET association = EXCLUDED.association
    -- lets users refine their associations over time
);
```

Enable RLS: `user_id = auth.uid()` on all operations. Same pattern as all other tables.

### 1.5 — JSONB analysis field: new shape

The `entries.analysis` JSONB column must now accommodate additional top-level fields.
No migration needed (JSONB is schemaless), but update `db-schema.md` to reflect:

```json
{
  "symbols": [...],
  "archetypes": [
    { "name": "Shadow", "confidence": 0.85, "evidence": "...", "projection_status": "projection" }
  ],
  "emotions": [...],
  "themes": [...],
  "jungian_summary": "...",
  "connections_to_previous": [...],
  "compensation_axis": { "summary": "...", "insufficient_material": false },
  "ego_strength_signal": { "score": 3, "rationale": "..." },
  "lysis_assessment": { "result": "unresolved", "interpretation": "..." },
  "amplification_questions": [{ "symbol": "...", "question": "..." }],
  "integration_risk": {
    "spiritual_inflation": { "present": false, "severity": null, "evidence": null },
    "ego_dissolution_without_regrounding": { "present": false, "severity": null, "evidence": null },
    "shadow_bypassing": { "present": false, "form": null, "severity": null, "evidence": null },
    "premature_closure": { "present": false, "severity": null, "evidence": null },
    "integration_guidance": "...",
    "overall_risk_level": "none"
  }
}
```

---

## Phase 2 — Backend: services and API changes

### 2.1 — services/analysis.py: update Pydantic schema

Add three new models and update `AnalysisResult` and `Archetype`:

```python
from typing import Optional, Literal

class Archetype(BaseModel):
    name: str
    confidence: float
    evidence: str
    projection_status: Literal["projection", "integrating", "ambiguous"]  # NEW

class CompensationAxis(BaseModel):                                         # NEW
    summary: str
    insufficient_material: bool = False

class EgoStrengthSignal(BaseModel):                                        # NEW
    score: int        # 1–6
    rationale: str

class LysisAssessment(BaseModel):                                          # NEW
    result: Literal["resolved", "unresolved", "ambiguous", "not_applicable"]
    interpretation: str

class AnalysisResult(BaseModel):
    symbols: list[Symbol]
    archetypes: list[Archetype]
    emotions: list[Emotion]
    themes: list[str]
    jungian_summary: str
    connections_to_previous: list[str]
    compensation_axis: Optional[CompensationAxis] = None                   # NEW
    ego_strength_signal: Optional[EgoStrengthSignal] = None               # NEW
    lysis_assessment: Optional[LysisAssessment] = None                    # NEW
```

Add these helpers below the model definitions:

```python
def get_ego_score(analysis: AnalysisResult) -> Optional[int]:
    return analysis.ego_strength_signal.score if analysis.ego_strength_signal else None

def get_dominant_archetypes(analysis: AnalysisResult) -> list[str]:
    return [a.name for a in analysis.archetypes if a.confidence >= 0.6]

def get_lysis(analysis: AnalysisResult) -> Optional[str]:
    return analysis.lysis_assessment.result if analysis.lysis_assessment else None
```

### 2.2 — services/edges.py: update upsert to write affective data

Replace the existing upsert function signature and SQL entirely.

New function name: `upsert_edges_with_affect`
New parameters: add `emotions: list[dict]` alongside the existing args.

The upsert now:
- Computes entry-level `avg_intensity` and `avg_valence` from the emotions list
- Uses incremental running average formula: `old_avg + (new_value - old_avg) / new_count`
- Updates `emotion_counts` JSONB and re-derives `dominant_emotion` on each conflict

Full replacement code is in `MIGRATION_GUIDE.md` → CHANGE 2.

Call site in `api/entries.py`: pass `analysis.emotions` (as list of dicts) into this function
after the extractor returns and Pydantic validation passes.

### 2.3 — services/complexes.py: update edge query and storage

Two changes:

**A. Replace the SELECT query:**
```python
# Old
SELECT symbol_a, symbol_b, weight FROM symbol_edges WHERE user_id = $1 ORDER BY weight DESC LIMIT 200

# New
SELECT symbol_a, symbol_b, weight,
       ROUND(avg_intensity::numeric, 2) AS avg_intensity,
       ROUND(avg_valence::numeric, 2)   AS avg_valence,
       COALESCE(dominant_emotion, 'unknown') AS dominant_emotion
FROM symbol_edges WHERE user_id = $1
ORDER BY (weight * avg_intensity) DESC
LIMIT 200
```

**B. Convert rows to dicts before passing to the prompt:**
```python
edge_dicts = [dict(row) for row in edges]
prompt = build_complex_detector_prompt(edge_dicts)
```

**C. Update the INSERT into complexes table** to include the new columns:
`overdetermined_symbols`, `affective_core`, `projection_status`,
`golden_shadow`, `golden_shadow_owned`, `individuation_note`.

Parse these from the Claude response (already in the new `complex_detector.py` JSON output)
before writing to DB.

**D. Update the detection trigger:**
Current: `entry_count % 7 == 0`
New: keep the `% 7` as a floor, but also trigger on season shift. See 2.5 below.

### 2.4 — services/amplification.py (new file)

Create `backend/app/services/amplification.py`.

This service:
1. Fetches the user's top 20 known associations from `personal_symbol_associations`
2. Calls `build_amplification_prompt()` from `prompts/amplification.py`
3. Makes a fast Claude call (`max_tokens=300`, `temperature=0.3`, no streaming)
4. Returns `{symbols_to_amplify: [{symbol, question}]}`
5. Stores the questions in the entry's `analysis` JSONB under `amplification_questions`

### 2.5 — services/unlock.py: add longitudinal trigger

The chat unlock gate (`entry_count >= 7 AND days_since_first >= 7`) stays unchanged.

Add this function alongside the existing gate check:

```python
from app.services.season_detector import should_trigger_longitudinal

def check_longitudinal_trigger(entries: list[dict], last_analysis_at: Optional[str]) -> dict:
    return should_trigger_longitudinal(entries, last_analysis_at)
```

Call this at the end of the entry submission pipeline in `api/entries.py`, after the
existing unlock check. If `should_trigger` is true, call `services/longitudinal.py`
to run the arc analysis. Defer this — don't make the user wait. Run it after the
entry response is returned (background task or async fire-and-forget).

After a successful longitudinal run, update `users.last_longitudinal_at = now()`.

### 2.6 — services/longitudinal.py (new file)

Create `backend/app/services/longitudinal.py`.

This service:
1. Fetches all user entries sorted ASC, extracting: `created_at`, `entry_type`,
   `ego_strength_signal.score`, `lysis_assessment.result`, `themes`, `jungian_summary`,
   and `dominant_archetypes` (via `get_dominant_archetypes()` helper from analysis.py)
2. Calls `build_longitudinal_analyzer_prompt()` from `prompts/longitudinal_analyzer.py`
3. Makes a Claude call (`temperature=0.3`, non-streaming)
4. Stores the result. Options:
   - Add a `longitudinal_analyses` table (cleanest — queryable history)
   - Or store in `users` table as a JSONB column `latest_arc_analysis` (simpler for v1)
   - Recommendation for v1: JSONB column on users. Add a table in v2 if arc history is needed.
5. Updates `users.last_longitudinal_at`

### 2.7 — services/integration_risk.py (new file)

Create `backend/app/services/integration_risk.py`.

This service:
1. Triggered at end of entry pipeline, after extraction and edge upsert
2. Trigger condition: `entry_type == "psychedelic"` OR `(entry_type == "meditation" AND ego_score <= 2)`
3. Fetches last 3–5 `jungian_summary` strings from the user's previous entries
4. Calls `build_integration_risk_prompt()` from `prompts/integration_risk.py`
5. Makes a Claude call (`temperature=0.2`, non-streaming)
6. Stores result in the entry's `analysis` JSONB under the `integration_risk` key
7. Only `integration_guidance` is ever surfaced to the frontend. `overall_risk_level`
   and individual flag objects are stored but never exposed in the API response.

### 2.8 — api/entries.py: full updated pipeline

Updated `POST /entries` flow after all changes:

```
1.  Pydantic input validation                             [unchanged]
2.  Store raw entry (analysis = null)                     [unchanged]
3.  Fetch top 20 personal_symbol_associations             [NEW]
4.  Run amplification.py → get questions                  [NEW]
5.  Store amplification_questions in analysis JSONB       [NEW]
6.  Fetch previous entries summary for extractor context  [unchanged]
7.  Run extractor.py (with personal associations injected if available) [updated]
8.  Validate against updated Pydantic schema              [updated]
9.  Store full analysis JSONB                             [unchanged]
10. Run upsert_edges_with_affect()                        [updated]
11. Increment entry_count, set first_entry_at if null     [unchanged]
12. Check chat unlock gate                                [unchanged]
13. Check longitudinal trigger → fire async if true       [NEW]
14. If entry_count % 7 == 0 OR season shift: run complexes.py [updated trigger]
15. If psychedelic or meditation+ego<=2: run integration_risk.py [NEW]
16. Return analysis to frontend                           [unchanged structure, new fields]
```

### 2.9 — api/entries.py: new endpoint

```python
@router.post("/entries/{entry_id}/amplify")
async def submit_amplification(
    entry_id: uuid.UUID,
    payload: list[AmplificationAnswer],  # [{symbol: str, answer: str}]
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    # 1. Validate entry belongs to user
    # 2. Upsert each answer into personal_symbol_associations
    #    ON CONFLICT (user_id, symbol) DO UPDATE SET association = EXCLUDED.association
    # 3. Update entry's analysis JSONB: mark those symbols as answered
    # 4. Return 200
```

### 2.10 — api/graph.py: new endpoint for complex overlay

```python
@router.get("/complexes")
async def get_complexes(user=Depends(get_current_user), db=Depends(get_db)):
    # Returns user's current complexes from complexes table
    # Frontend uses this for the symbol graph complex overlay
    # Include: name, symbols[], projection_status, golden_shadow
```

### 2.11 — api/arc.py (new file)

```python
@router.get("/arc")
async def get_arc(user=Depends(get_current_user), db=Depends(get_db)):
    # Returns latest longitudinal analysis from users.latest_arc_analysis JSONB
    # If null (no analysis run yet): return {"available": false}
    # If available: return full arc object + {"available": true}
```

---

## Phase 3 — No backend changes

`graph.py` reads `symbol_edges` as before. The affective columns are additive —
nothing breaks. Phase 3 frontend changes are listed below.

---

## Phase 4 — Backend: chat service update

### 4.1 — services/chat.py: pass new complex fields to persona

The `build_persona_prompt()` function in `persona.py` now reads `projection_status`
and `golden_shadow` from each complex dict. These come from the `complexes` table.

Update the complexes fetch query to include the new columns:

```python
# Old SELECT
SELECT name, summary, symbols FROM complexes WHERE user_id = $1

# New SELECT
SELECT name, summary, symbols, overdetermined_symbols, affective_core,
       projection_status, golden_shadow, golden_shadow_owned, individuation_note
FROM complexes WHERE user_id = $1
```

### 4.2 — api/chat.py: seed_entry query param

The SSE chat endpoint needs to accept an optional `seed_entry` query param:

```python
@router.get("/chat/stream")
async def chat_stream(
    message: str,
    seed_entry: Optional[uuid.UUID] = None,   # NEW optional param
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    # If seed_entry is provided: skip seed symbol extraction,
    # use that entry's symbols directly as retrieval seeds in retrieval.py
    # If not: run seed_extractor.py as normal
```

---

## Frontend — new components

All live in `frontend/app/components/`.

### EgoStrengthIndicator.tsx (new)
- Props: `score: number` (1–6)
- Render: 6 small circles, filled up to score value
- Color: score 1–2 muted red, 3–4 amber, 5–6 soft green
- Tooltip on each circle: show the scale label for that score only
  (1=absent, 2=overwhelmed, 3=failing, 4=holding, 5=engaging, 6=integrating)
- Keep it visually subtle — this is a signal indicator, not a game score

### FollowUpThread.tsx (new)
- Props: `questions: [{symbol, question}]`, `entryId: string`, `onAnswered: () => void`
- Renders inside the entry detail page, below the analysis
- Each question has its own text input and a "save" button
- Saves independently via `POST /entries/{id}/amplify` — one answer at a time
- "Skip — these questions will return" link below the section
- Does not render if `questions` array is empty (all symbols already known)

### IntegrationGuidance.tsx (new)
- Props: `guidance: string`
- Renders only when `integration_guidance` is present in the entry analysis
- Subtle styling: muted border-left, small text, italicized
- Static disclaimer below the text: "This is a symbolic compass, not clinical advice."
- Never receives or renders risk scores or flag names

### ArcChart.tsx (new)
- Props: `scores: number[]`, `dates: string[]`, `entryTypes: string[]`
- Line chart of ego strength over time
- Built with Recharts (already in stack)
- Dots colored by entry type: dream / psychedelic / meditation
- Tooltip on hover: date, score label, lysis result if available
- No gridlines. Dark background. Minimal axis labels.

### IndividuationArcView.tsx (new)
- Full layout component for the `/arc` page
- Sections (in order): ArcChart, current season badge, dominant themes, next threshold, archetype evolution
- Season badge text values: "breakthrough" | "regression" | "stuck" | "integrating" | "archetype shift" | "first reading"
- `next_threshold` text: italicized, no label — reads as a statement from the analyst
- Only renders when `GET /arc` returns `available: true`

---

## Frontend — updated components

### EntryCard.tsx

Add below the `jungian_summary`:

1. **Compensation axis** — render `compensation_axis.summary` in italics if present and
   `insufficient_material` is false. No label. Reads as continuation of analyst voice.

2. **Ego strength indicator** — render `<EgoStrengthIndicator score={ego_strength_signal.score} />`
   if present. Place to the right of the summary, not below it.

3. **Lysis badge** — dreams only (`entry_type === "dream"`). Small pill:
   - "resolved" → muted green
   - "unresolved" → muted amber
   - "ambiguous" → muted gray
   - Tooltip: `lysis_assessment.interpretation` text
   - Don't render for psychedelic or meditation entries

4. **Archetype projection labels** — in the archetypes list, add secondary label next to each:
   - `projection_status === "projection"` → small muted text "projected"
   - `projection_status === "integrating"` → small muted text "integrating"
   - `"ambiguous"` → render nothing

### SymbolGraph.tsx

Three additions to the D3 rendering logic:

1. **Edge color by dominant emotion**
   Map `dominant_emotion` to a color:
   - fear / threat → muted red (`#7f3f3f`)
   - grief / loss → muted blue (`#3f5f7f`)
   - awe / numinous → muted gold (`#7f6f3f`)
   - anger → muted orange (`#7f5f3f`)
   - love / connection → muted rose (`#7f4f5f`)
   - unknown / null → muted gray (`#4f4f4f`)
   No legend. Tooltip on edge hover: `[symbol_a] — [symbol_b] | [weight]x | [dominant_emotion]`

2. **Edge opacity by psychic charge**
   Replace the current weight-normalized opacity with:
   `opacity = normalize(weight * avg_intensity, min=0.1, max=0.85)`
   Inert high-frequency edges fade. Hot low-frequency edges become visible.
   Fetch `avg_intensity` from `GET /graph` — add it to the edge objects returned.

3. **Complex overlay toggle**
   Add a "Show complexes" button above the graph canvas.
   On toggle: fetch `GET /complexes`, draw a D3 convex hull around each complex's symbol nodes.
   Each complex gets a distinct muted color. Complex name appears on hull hover.
   Use `d3.polygonHull()` on the node positions of each complex's symbols.

   State:
   ```tsx
   const [showComplexes, setShowComplexes] = useState(false)
   const [complexes, setComplexes] = useState([])

   useEffect(() => {
     if (showComplexes && complexes.length === 0) {
       fetch('/complexes').then(r => r.json()).then(setComplexes)
     }
   }, [showComplexes])
   ```

### ChatWindow.tsx

One change: when navigated to via `?seed_entry={id}`, pass the seed_entry param
in the `GET /chat/stream` request. No visible UI change — the seeding is invisible.

Add to the SSE request URL construction:
```tsx
const seedEntry = searchParams.get('seed_entry')
const url = `/chat/stream?message=${encodeURIComponent(msg)}${seedEntry ? `&seed_entry=${seedEntry}` : ''}`
```

### LockedOverlay.tsx

Currently shows two unlock conditions (entries, days).
Add a third section for the arc page, visually separated:

```
Subconscious chat
  [✓ or ●] 5 of 7 entries
  [✓ or ●] 3 of 7 days

Individuation arc    ← new section
  [✓ or ●] First season shift not yet detected
```

The arc condition reads from a new `arc_available` flag returned by `GET /arc`.
When arc is available, the nav link appears — no overlay for it.

---

## Frontend — new pages and routes

### app/arc/page.tsx (new)

- Fetches `GET /arc` on mount
- If `available: false`: render nothing (page doesn't exist in nav yet)
- If `available: true`: render `<IndividuationArcView />`
- Title: "Your Arc" or no title — let the chart speak

### app/journal/[id]/page.tsx (updated)

Add below the existing analysis sections:

1. `<FollowUpThread />` — if `amplification_questions` array is non-empty
2. `<IntegrationGuidance />` — if `integration_risk.integration_guidance` is present
3. "Talk to your subconscious about this" button — routes to `/chat?seed_entry={id}`
   Only renders if `chat_unlocked === true`

---

## Navigation updates

### Add "Arc" link to main nav

Condition: only render this nav link if `GET /arc` returns `available: true`.
Before that: link is absent entirely (not locked, not grayed out — just not there).

Position in nav: between "Map" and "Chat"

```
Journal  |  Map  |  Arc  |  Chat
```

---

## Repository structure changes (final state)

```
backend/app/
  prompts/
    extractor.py              ← replaced
    seed_extractor.py         ← replaced
    persona.py                ← replaced
    complex_detector.py       ← replaced
    amplification.py          ← NEW
    longitudinal_analyzer.py  ← NEW
    integration_risk.py       ← NEW

  services/
    analysis.py               ← updated (Pydantic schema + helpers)
    edges.py                  ← updated (affective upsert)
    complexes.py              ← updated (query + storage + trigger)
    unlock.py                 ← updated (longitudinal trigger added)
    amplification.py          ← NEW
    longitudinal.py           ← NEW
    integration_risk.py       ← NEW
    season_detector.py        ← NEW

  api/
    entries.py                ← updated (pipeline + new /amplify endpoint)
    graph.py                  ← updated (add /complexes endpoint)
    chat.py                   ← updated (seed_entry param)
    arc.py                    ← NEW

frontend/app/
  arc/
    page.tsx                  ← NEW

  journal/[id]/
    page.tsx                  ← updated (follow-up thread, integration guidance, chat CTA)

  components/
    EntryCard.tsx             ← updated
    SymbolGraph.tsx           ← updated
    ChatWindow.tsx            ← updated (seed_entry param)
    LockedOverlay.tsx         ← updated (arc condition)
    EgoStrengthIndicator.tsx  ← NEW
    FollowUpThread.tsx        ← NEW
    IntegrationGuidance.tsx   ← NEW
    ArcChart.tsx              ← NEW
    IndividuationArcView.tsx  ← NEW
```

---

## Build order (recommended)

Do not start Phase 4 before Phase 2 is complete. The edges table is the foundation.

```
Phase 1: All DB migrations (1.1 → 1.5) in one session
Phase 2: analysis.py schema → edges.py upsert → extractor.py drop-in
         → amplification service → entries.py pipeline update
Phase 3: SymbolGraph affective coloring + complex overlay (uses /complexes endpoint)
Phase 4: complexes.py update → chat.py update → persona.py drop-in
         → unlock.py longitudinal trigger → longitudinal.py service
         → integration_risk.py service → arc.py endpoint
         → all new frontend components + /arc page
```
