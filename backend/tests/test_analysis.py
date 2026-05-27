import unittest

from app.services.analysis import parse_and_map_analysis_result


class AnalysisParserTests(unittest.TestCase):
    def test_parser_maps_symbol_archetype_attributions(self):
        result = parse_and_map_analysis_result(
            """
            {
              "symbols": [{"name": "God", "category": "figure", "significance": "Numinous center."}],
              "archetypes": [{"name": "Self", "confidence": 0.9, "evidence": "God appeared."}],
              "symbol_archetypes": [
                {"symbol": "God", "archetype": "Self", "confidence": 0.9, "evidence": "God as center."}
              ],
              "emotions": [],
              "themes": [],
              "jungian_summary": "The Self appears as a divine image.",
              "connections_to_previous": []
            }
            """
        )

        self.assertEqual(len(result.symbol_archetype_attributions), 1)
        attribution = result.symbol_archetype_attributions[0]
        self.assertEqual(attribution.symbol, "God")
        self.assertEqual(attribution.archetype, "Self")
        self.assertEqual(attribution.confidence, 0.9)


if __name__ == "__main__":
    unittest.main()
