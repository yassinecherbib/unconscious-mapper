"""
Symbolic Complex Detection Prompt

Called by services/complexes.py every 7 entries.

RECOMMENDED TEMPERATURE: 0.3
Rationale: Naming complexes requires a degree of creative synthesis (archetypal names
should be evocative, not generic), but the structural analysis must remain grounded in
the actual edge data. Slightly higher than extraction to allow naming creativity,
but not so high that summaries drift from the evidence.

SCHEMA CHANGE — edges must now include affective data:
    {
        "symbol_a": str,
        "symbol_b": str,
        "weight": int,              # co-occurrence count (frequency)
        "avg_intensity": float,     # mean emotional intensity across co-occurrences (0.0–1.0)
        "avg_valence": float,       # mean emotional valence across co-occurrences (-1.0–1.0)
        "dominant_emotion": str     # most frequently tagged emotion when these symbols co-occur
    }

    avg_intensity and avg_valence are computed in services/complexes.py by joining
    the edges table with the emotions extracted per entry. See services/complexes.py.

    A high-frequency edge with avg_intensity < 0.2 is emotionally dead — two symbols
    that appear together but carry no charge. These should NOT anchor a complex.
    A low-frequency edge with avg_intensity > 0.7 is a hot signal — possibly more
    psychically significant than any high-count but inert pair.
"""


def build_complex_detector_prompt(edges: list[dict]) -> str:
    edge_lines = "\n".join(
        f"{row['symbol_a']} — {row['symbol_b']}: "
        f"{row['weight']} co-occurrences | "
        f"intensity {row.get('avg_intensity', '?'):.2f} | "
        f"valence {row.get('avg_valence', '?'):.2f} | "
        f"dominant emotion: {row.get('dominant_emotion', 'unknown')}"
        for row in edges
    )

    return f"""You are a Jungian analyst examining a user's unconscious symbol co-occurrence graph.
This graph was built from their accumulated dreams, psychedelic experiences, and meditations.

Each edge contains:
- Co-occurrence count (how often two symbols appeared in the same entry)
- Average emotional intensity (0.0 = emotionally inert, 1.0 = overwhelming charge)
- Average emotional valence (-1.0 = strongly negative, 1.0 = strongly positive)
- Dominant emotion (the most frequent emotional tag when these two symbols co-occurred)

Your task is to identify the symbolic complexes buried in this topology.

---
WHAT A COMPLEX IS — AND WHY FREQUENCY ALONE IS WRONG

In Jungian terms, a complex is an autonomous, AFFECTIVELY-CHARGED cluster in the unconscious.
The defining property is emotional charge, not repetition.
Two symbols that appear together 15 times with avg_intensity 0.1 are NOT a complex —
they are a habit, a setting, a background. They co-occur because they share a scene.
Two symbols that appear together 3 times with avg_intensity 0.85 ARE a candidate complex —
something about their conjunction lights up the psyche every time.

CLUSTERING RULE: Weight each edge by (co-occurrence × avg_intensity) to get its
"psychic charge score." Prioritize high-charge edges when forming clusters.
Low-intensity edges (avg_intensity < 0.25) should only be included in a complex if
they bridge two otherwise high-charge symbols.

VALENCE TELLS YOU WHAT KIND OF COMPLEX:
- Consistently negative valence: Dark Shadow complex — threatening, persecutory,
  unmetabolized wound.
- Consistently positive valence: Golden Shadow complex — disowned strengths, suppressed
  vitality or creativity that the ego has not claimed. Do NOT assume positive valence
  means the complex is healthy or integrated. The ego may be encountering the Golden
  Shadow as something "out there" — an idealized figure, an ecstatic state, a sense of
  being chosen or gifted — without actually owning it. That is still projection.
- Mixed valence (high variance): Tension complex — the psyche is holding opposites
  around these symbols. Highest individuation potential; also highest instability.
---

AFFECTIVELY-WEIGHTED EDGE DATA:
{edge_lines}

---
ANALYSIS INSTRUCTIONS

1. PSYCHIC CHARGE SCORING
   Before clustering, mentally compute (weight × avg_intensity) for each edge.
   Use this score — not raw frequency — as your primary clustering signal.
   Note the top 3 highest-charge edges explicitly in your summary as the "affective core"
   of the overall graph.

2. CLUSTER IDENTIFICATION
   Identify 3 to 5 symbolic complexes. Look for:
   - High-charge sub-graphs (symbols bound by emotionally intense co-occurrences)
   - Hub symbols (appear across many high-charge pairs — these are the complex's nuclear symbol)
   - Bridge symbols (link multiple clusters at moderate charge — psychically overdetermined;
     flag as "overdetermined")
   - Inert pairs (high frequency, low intensity) — exclude from complexes; note if relevant
     as "habitual context" rather than psychic structure

3. ARCHETYPAL NAMING
   Name each complex mythopoetically and specifically.
   The name should encode the dominant emotion and the archetype, not just the symbols.
   Good: "The Devouring-Water Cluster", "The Luminous-Exile Axis", "The Locked-Threshold Complex"
   Bad: "Water Complex", "Family Cluster", "Positive Experience Group"

4. GOLDEN SHADOW DETECTION
   A Golden Shadow complex has high positive valence BUT the symbols appear as external,
   idealized, or overwhelming — not as qualities the dreamer embodies.
   Signs: the dreamer encounters beauty, power, or genius in a figure or force that is
   not them. The positive charge is real; the ownership is absent.
   This is NOT the same as an integrated strength. Flag separately:
   golden_shadow: true | false
   golden_shadow_owned: true | false  (true only if evidence shows the dreamer IS the
   powerful figure, not just encountering it)

5. PROJECTION VS INTEGRATION
   For each complex:
   - PROJECTED: energy appears as external figures/forces the dreamer encounters or flees
   - INTEGRATING: dreamer is in dialogue with, transforming, or embodying the energy
   - AMBIGUOUS: insufficient signal

6. INDIVIDUATION RELEVANCE
   One sentence on what this complex's affective signature reveals about the psyche's
   current unfinished business.

---
RETURN FORMAT
Return ONLY a JSON array. No markdown. No preamble. No explanation.

[
  {{
    "name": str,
    "summary": str,
    "symbols": [str],
    "overdetermined_symbols": [str],
    "affective_core": str,            // 1 sentence on the dominant emotion/valence pattern
    "projection_status": str,         // "projection" | "integrating" | "ambiguous"
    "golden_shadow": bool,
    "golden_shadow_owned": bool,      // only meaningful if golden_shadow is true
    "individuation_note": str
  }}
]
"""
