# UI Changes Required
# What to add, update, or restructure in the frontend to consume the new prompt outputs

---

## 1. EntryCard.tsx — display new extractor fields

### Currently shows
- symbols, archetypes, emotions, jungian_summary

### Add these sections

**Ego Strength Signal**
A simple 1–6 visual indicator. Not a progress bar (too clinical).
Use 6 small glyphs — filled vs unfilled. Label the score but don't explain the scale
to the user inline; let the tooltip handle it.

```tsx
// Component: EgoStrengthIndicator.tsx (new)
// Props: score: number (1–6)
// Render: 6 small circles, filled up to score
// Tooltip on hover: show the scale label for that score only
//   1 = "absent", 2 = "overwhelmed", 3 = "failing",
//   4 = "holding", 5 = "engaging", 6 = "integrating"
// Color: score 1-2 muted red, 3-4 amber, 5-6 soft green
// This is the only quantitative element users see — keep it subtle
```

**Compensation Axis**
Single sentence, italicized, below the jungian_summary.
No label. It reads as a continuation of the analyst's voice.
If `insufficient_material: true`, don't render it at all.

```tsx
{analysis.compensation_axis && !analysis.compensation_axis.insufficient_material && (
  <p className="text-sm italic text-muted-foreground mt-2">
    {analysis.compensation_axis.summary}
  </p>
)}
```

**Lysis Assessment** (dreams only)
One line below the summary. Small badge: "resolved" | "unresolved" | "ambiguous"
Color: resolved = muted green, unresolved = muted amber, ambiguous = muted gray
On hover: show the interpretation text.
Don't show this for psychedelic or meditation entries.

**Archetype projection status**
In the archetypes list, each archetype already shows name + confidence.
Add a small secondary label: "projected" or "integrating" in muted text.
Ambiguous = show nothing.

```tsx
// In the archetype pill/row:
{archetype.projection_status !== "ambiguous" && (
  <span className="text-xs text-muted-foreground ml-1">
    {archetype.projection_status}
  </span>
)}
```

---

## 2. journal/[id]/page.tsx — full entry view

### Add: Follow-up Thread section

This is the amplification feature expressed as UI. Below the full analysis,
add a collapsible section: "Dig deeper."

```
┌─────────────────────────────────────────────┐
│ ANALYSIS                                     │
│ [jungian_summary]                            │
│ [compensation_axis]                          │
│ [symbols] [archetypes] [emotions]            │
│ [ego_strength] [lysis]                       │
├─────────────────────────────────────────────┤
│ ↓  The analyst has questions                 │  ← collapsible, closed by default
│                                              │
│  "What does [black dog] remind you of       │
│   in your waking life?"                     │
│  [text input]  [save]                       │
│                                             │
│  "What does [the locked room] feel like     │
│   when you think about it now?"             │
│  [text input]  [save]                       │
│                                             │
│  [Skip — these questions will return]       │  ← skipping is fine, not permanent
└─────────────────────────────────────────────┘
```

Each answer saves independently via `POST /entries/{id}/amplify`.
The "skip" note matters — don't make it feel like failing. The questions
recur in future amplification calls until the symbol has a known association.

**State logic:**
- Questions come from the amplification prompt output, stored in the entry's
  analysis JSONB under `amplification_questions`
- Already-answered symbols (from `personal_symbol_associations` table) don't
  show questions again
- If all symbols are already known, this section doesn't render

---

## 3. New component: IntegrationGuidance.tsx

For psychedelic and high-intensity meditation entries only.
Renders the `integration_guidance` field from `integration_risk.py` output.

```
┌─────────────────────────────────────────────┐
│ Integration note                            │  ← subtle header, not alarming
│                                             │
│  [integration_guidance text]                │
│                                             │
│  Note: this is a symbolic compass,          │  ← always present disclaimer
│  not clinical advice.                       │
└─────────────────────────────────────────────┘
```

**What NOT to show:**
- `overall_risk_level` — never surface this score to the user
- Individual risk flags (`spiritual_inflation`, etc.) — too clinical, too alarming
- Only `integration_guidance` reaches the UI

Placement: bottom of the entry view, below the follow-up thread. It should feel
like a quiet note, not a warning banner. Muted styling.

---

## 4. New page: /arc (or /progress)

Consumes `longitudinal_analyzer.py` output. Unlocks after the first longitudinal
analysis runs (same gate as chat, roughly).

```
┌─────────────────────────────────────────────┐
│  YOUR INDIVIDUATION ARC                     │
│                                             │
│  [Ego Strength over time — line chart]      │
│  x-axis: entry dates                        │
│  y-axis: ego score 1–6                      │
│  Dots colored by entry_type                 │
│  Tooltip on hover: entry date + lysis       │
│                                             │
├─────────────────────────────────────────────┤
│  Current season                             │
│  [season_signal badge]                      │  ← "breakthrough" / "stuck" / etc.
│  [individuation_assessment paragraph]       │
│                                             │
├─────────────────────────────────────────────┤
│  Recurring themes                           │
│  [dominant_themes as pill tags]             │
│                                             │
├─────────────────────────────────────────────┤
│  Next threshold                             │
│  [next_threshold text, italicized]          │
│                                             │
├─────────────────────────────────────────────┤
│  Archetype movement                         │
│  [archetype_evolution paragraph]            │
└─────────────────────────────────────────────┘
```

**Nav:** Add "Arc" to the main nav after the user's first longitudinal analysis runs.
Before that: don't show the link at all. Not a locked overlay — just absent.

**The ego strength chart is the most important element on this page.**
It's the only place users see their individuation progress quantified.
Keep it simple: line chart, dots, no gridlines, dark background. Recharts works.

---

## 5. Updates to SymbolGraph.tsx (map page)

The D3 graph currently uses only `weight` for edge thickness.
New data available: `avg_intensity` and `dominant_emotion` per edge.

### Add: Affective edge coloring
Color edges by `dominant_emotion`:
- Fear/threat: muted red
- Grief/loss: muted blue
- Awe/numinous: muted gold
- Anger: muted orange
- Love/connection: muted rose
- Ambiguous/unknown: muted gray

Don't label the colors in a legend. Let users discover the pattern.
A tooltip on edge hover: "[symbol_a] — [symbol_b] | [weight]x | [dominant_emotion]"

### Add: Affective intensity as edge opacity
Currently: edge opacity normalized from weight.
New: opacity = (weight × avg_intensity) normalized — psychic charge, not frequency.
Inert high-frequency edges visually fade. Hot low-frequency edges become visible.
This makes the graph show what matters psychically, not just what's common.

### Add: Complex overlay toggle
A button: "Show complexes"
When active: draw a soft convex hull around each complex's symbols.
Color-coded by complex. Label with the complex name on hover.
Uses the `complexes` table data already fetched for the chat context.

```tsx
// SymbolGraph.tsx — add toggle state
const [showComplexes, setShowComplexes] = useState(false)

// Fetch complexes from /complexes endpoint (new endpoint needed)
// Draw D3 hull around each complex's symbol nodes when toggle is on
```

This makes the symbol map go from "pretty visualization" to
"this is what my unconscious is actually organized around."

---

## 6. ChatWindow.tsx — minor updates

The persona prompt now passes `projection_status` and `golden_shadow` per complex
into the AI context. The UI doesn't need to change for this — it's invisible to
the user. But one UX addition matters:

### Add: Entry-specific chat entrypoint

From any entry view (`journal/[id]`), add a button:
"Talk to your subconscious about this entry"

This navigates to `/chat` with the entry's UUID as a query param:
`/chat?seed_entry={id}`

In `chat.py` (backend), if `seed_entry` is provided, skip the seed symbol
extraction step and instead use that entry's symbols directly as retrieval seeds.
The conversation starts already anchored to that specific entry's symbolic material.

This is the most important UX addition. Users who just read an intense analysis
want to go deeper immediately — not navigate to a separate chat and re-establish
context from scratch.

---

## 7. LockedOverlay.tsx — update unlock conditions display

Currently shows: "5 of 7 entries" and "3 of 7 days"

Add: a third line showing the arc page unlock status separately.
Arc page unlocks on first longitudinal analysis (separate from chat unlock).

```tsx
// Three conditions shown:
// [✓] Subconscious chat: 7 entries + 7 days
// [ ] Individuation arc: first season shift detected
// Both use the same visual progress style — specific counts, never vague
```

---

## Summary: new files and changed files

### New components
- `EgoStrengthIndicator.tsx`
- `IntegrationGuidance.tsx`
- `FollowUpThread.tsx` (the amplification question UI)
- `ArcChart.tsx` (ego strength line chart for /arc page)
- `IndividuationArcView.tsx` (full /arc page layout)

### Changed components
- `EntryCard.tsx` — add ego score, compensation axis, lysis badge, projection status
- `SymbolGraph.tsx` — affective edge coloring, intensity-based opacity, complex overlay
- `ChatWindow.tsx` — add seed_entry query param handling
- `LockedOverlay.tsx` — add arc page unlock condition

### New pages
- `app/arc/page.tsx` — individuation arc view

### New API endpoints needed (frontend-facing)
- `GET /complexes` — returns user's current complexes (for symbol graph overlay)
- `POST /entries/{id}/amplify` — stores personal symbol associations
- `GET /arc` — returns latest longitudinal analysis result
  (or compute on-demand if not yet run — add to migration guide)
