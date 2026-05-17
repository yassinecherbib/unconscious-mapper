"""
Symbolic Complex Detection Prompt

Insert your custom prompt text where indicated.
Called by services/complexes.py every 7 entries.
"""


def build_complex_detector_prompt(edges: list[dict]) -> str:
    edge_lines = "\n".join(
        f"{row['symbol_a']} — {row['symbol_b']}: {row['weight']} co-occurrences"
        for row in edges
    )

    return f"""
(insert symbolic complex detection prompt here)

You are a Jungian analyst identifying symbolic complexes from a user's
unconscious symbol co-occurrence graph.

Given this edge list (symbol pairs and their co-occurrence frequency):

{edge_lines}

Identify 3 to 5 symbolic complexes (clusters). Each complex should:
- Have an evocative archetypal name (e.g. "The Drowning-Mother Cluster")
- Include a paragraph-length Jungian summary of what this cluster reveals
- List the core symbols belonging to this complex

Return ONLY a JSON array. No markdown. No preamble.
[
  {{ "name": str, "summary": str, "symbols": [str] }}
]
"""
