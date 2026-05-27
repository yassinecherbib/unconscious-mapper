import unittest
from datetime import datetime, timezone

from app.services.graph import build_graph_payload


NOW = datetime(2026, 5, 27, tzinfo=timezone.utc)


class GraphPayloadTests(unittest.TestCase):
    def test_legacy_edges_still_return_symbol_graph(self):
        payload = build_graph_payload(
            [{"symbol_a": "dog", "symbol_b": "dark beach", "weight": 2, "entry_ids": []}],
            [],
            now=NOW,
        )

        symbols = {node["id"]: node for node in payload["nodes"] if node["type"] == "symbol"}
        self.assertEqual(symbols["dog"]["value"], 2)
        self.assertEqual(symbols["dark beach"]["value"], 2)
        self.assertEqual(payload["edges"][0]["type"], "cooccurrence")
        self.assertEqual(payload["edges"][0]["decayed_value"], 2.0)

    def test_explicit_attributions_create_archetype_nodes_and_edges(self):
        payload = build_graph_payload(
            [{"symbol_a": "God", "symbol_b": "fighting", "weight": 1, "entry_ids": ["e1"]}],
            [{
                "id": "e1",
                "created_at": "2026-05-27T00:00:00Z",
                "analysis": {
                    "symbols": [{"name": "God"}, {"name": "fighting"}],
                    "archetypes": [{"name": "Self", "confidence": 0.9}],
                    "symbol_archetype_attributions": [
                        {"symbol": "God", "archetype": "Self", "confidence": 0.9, "evidence": "center"},
                    ],
                },
            }],
            now=NOW,
        )

        symbol = next(node for node in payload["nodes"] if node["id"] == "God")
        archetype = next(node for node in payload["nodes"] if node["id"] == "archetype:Self")
        edge = next(edge for edge in payload["edges"] if edge["type"] == "attribution")
        self.assertEqual(symbol["dominant_archetype"], "Self")
        self.assertEqual(symbol["dominant_confidence"], 0.9)
        self.assertEqual(archetype["label"], "Self")
        self.assertEqual(edge["source"], "God")
        self.assertEqual(edge["target"], "archetype:Self")

    def test_legacy_inference_links_symbols_to_entry_archetypes_at_reduced_confidence(self):
        payload = build_graph_payload(
            [{"symbol_a": "dog", "symbol_b": "dark beach", "weight": 1, "entry_ids": ["e1"]}],
            [{
                "id": "e1",
                "created_at": "2026-05-27T00:00:00Z",
                "analysis": {
                    "symbols": [{"name": "dog"}, {"name": "dark beach"}],
                    "archetypes": [{"name": "Shadow", "confidence": 0.8}],
                },
            }],
            now=NOW,
        )

        edge = next(edge for edge in payload["edges"] if edge["type"] == "attribution" and edge["source"] == "dog")
        self.assertEqual(edge["target"], "archetype:Shadow")
        self.assertAlmostEqual(edge["confidence"], 0.36)

    def test_recency_decay_uses_30_day_half_life(self):
        payload = build_graph_payload(
            [{"symbol_a": "dog", "symbol_b": "beach", "weight": 2, "entry_ids": ["new", "old"]}],
            [
                {"id": "new", "created_at": "2026-05-27T00:00:00Z", "analysis": {}},
                {"id": "old", "created_at": "2026-04-27T00:00:00Z", "analysis": {}},
            ],
            now=NOW,
        )

        edge = payload["edges"][0]
        self.assertEqual(edge["decayed_value"], 1.5)
        self.assertEqual(edge["recency_weight"], 0.75)

    def test_bridge_nodes_are_flagged_when_they_connect_three_components(self):
        payload = build_graph_payload(
            [
                {"symbol_a": "grandma house", "symbol_b": "God", "weight": 1, "entry_ids": []},
                {"symbol_a": "grandma house", "symbol_b": "fighting", "weight": 1, "entry_ids": []},
                {"symbol_a": "grandma house", "symbol_b": "dog", "weight": 1, "entry_ids": []},
            ],
            [],
            now=NOW,
        )

        bridge = next(node for node in payload["nodes"] if node["id"] == "grandma house")
        self.assertTrue(bridge["is_bridge"])
        self.assertEqual(bridge["bridge_score"], 3)


if __name__ == "__main__":
    unittest.main()
