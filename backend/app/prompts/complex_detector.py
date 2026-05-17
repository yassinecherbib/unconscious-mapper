"""
Symbolic Complex Detection Prompt — updated for affective edge data.

Drop-in replacement for the original placeholder version.
See extracted/complex_detector.py for full docstring and rationale.

SCHEMA CHANGE: edges must now include avg_intensity, avg_valence, dominant_emotion.
These are populated by the updated upsert_edges_with_affect() function.
"""


def build_complex_detector_prompt(edges: list[dict]) -> str:
    edge_lines = "\n".join(
        f"{row['symbol_a']} — {row['symbol_b']}: "
        f"{row['weight']} co-occurrences | "
        f"intensity {row.get('avg_intensity', 0.0):.2f} | "
        f"valence {row.get('avg_valence', 0.0):.2f} | "
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
they are a habit, a setting, a background.
Two symbols that appear together 3 times with avg_intensity 0.85 ARE a candidate complex.

CLUSTERING RULE: Weight each edge by (co-occurrence × avg_intensity) to get its
"psychic charge score." Prioritize high-charge edges when forming clusters.
Low-intensity edges (avg_intensity < 0.25) should only be included if they bridge
two otherwise high-charge symbols.

VALENCE TELLS YOU WHAT KIND OF COMPLEX:
- Consistently negative valence: Dark Shadow complex — threatening, unmetabolized wound.
- Consistently positive valence: Golden Shadow complex — disowned strengths the ego has not claimed.
  Do NOT assume positive valence means integrated. The ego may be encountering Golden Shadow
  as something "out there" — that is still projection.
- Mixed valence (high variance): Tension complex — psyche holding opposites. Highest individuation potential.
---

AFFECTIVELY-WEIGHTED EDGE DATA:
{edge_lines}

---
ANALYSIS INSTRUCTIONS

1. PSYCHIC CHARGE SCORING
   Before clustering, compute (weight × avg_intensity) for each edge.
   Use this score — not raw frequency — as your primary clustering signal.

2. CLUSTER IDENTIFICATION
   Identify 3 to 5 symbolic complexes. Look for:
   - High-charge sub-graphs
   - Hub symbols (appear across many high-charge pairs — the complex's nuclear symbol)
   - Bridge symbols linking multiple clusters (flag as overdetermined)
   - Inert pairs (high frequency, low intensity) — exclude from complexes

3. ARCHETYPAL NAMING
   Name each complex mythopoetically and specifically.
   Good: "The Devouring-Water Cluster", "The Luminous-Exile Axis"
   Bad: "Water Complex", "Family Cluster"

4. GOLDEN SHADOW DETECTION
   High positive valence BUT symbols appear as external/idealized/overwhelming.
   golden_shadow: true | false
   golden_shadow_owned: true only if the dreamer IS the powerful figure, not just encountering it.

5. PROJECTION VS INTEGRATION
   projection: energy appears as external figures/forces the dreamer encounters or flees
   integrating: dreamer is in dialogue with, transforming, or embodying the energy
   ambiguous: insufficient signal

6. INDIVIDUATION RELEVANCE
   One sentence on what this complex's affective signature reveals about the psyche's
   current unfinished business.

---
Return ONLY a JSON array. No markdown. No preamble. No explanation.

[
  {{
    "name": str,
    "summary": str,
    "symbols": [str],
    "overdetermined_symbols": [str],
    "affective_core": str,
    "projection_status": str,
    "golden_shadow": bool,
    "golden_shadow_owned": bool,
    "individuation_note": str
  }}
]
"""
