import asyncio
import unittest
from types import SimpleNamespace

import app.services.amplification as amplification


class _FakeModels:
    def __init__(self, response_text=None, delay=0):
        self.response_text = response_text
        self.delay = delay
        self.calls = []

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.delay:
            await asyncio.sleep(self.delay)
        return SimpleNamespace(text=self.response_text)


class AmplificationServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_parse_recovers_json_inside_preamble_and_fence(self):
        result = amplification.parse_and_map_amplification_result(
            'Here is the JSON requested:\n```json\n'
            '{"symbols_to_amplify":[{"symbol":"one male","question":"What comes to mind?"}]}\n'
            '```'
        )

        self.assertEqual(
            result,
            [{"symbol": "one male", "question": "What comes to mind?"}],
        )

    async def test_amplification_uses_flash_lite_model(self):
        fake_models = _FakeModels(
            '{"symbols_to_amplify":[{"symbol":"room","question":"What does this room evoke?"}]}'
        )
        original_client = amplification._client
        amplification._client = SimpleNamespace(aio=SimpleNamespace(models=fake_models))
        try:
            result = await amplification.get_amplification_questions("a room", "dream", {})
        finally:
            amplification._client = original_client

        self.assertEqual(result, [{"symbol": "room", "question": "What does this room evoke?"}])
        self.assertEqual(fake_models.calls[0]["model"], "gemini-3.1-flash-lite")
        config = fake_models.calls[0]["config"]
        self.assertEqual(config.http_options.timeout, 19000)

    async def test_amplification_timeout_uses_fallback_questions(self):
        fake_models = _FakeModels(
            '{"symbols_to_amplify":[{"symbol":"room","question":"What does this room evoke?"}]}',
            delay=0.05,
        )
        original_client = amplification._client
        original_timeout = amplification.AMPLIFICATION_TIMEOUT_SECONDS
        amplification._client = SimpleNamespace(aio=SimpleNamespace(models=fake_models))
        amplification.AMPLIFICATION_TIMEOUT_SECONDS = 0.01
        try:
            result = await amplification.get_amplification_questions("a room", "dream", {})
        finally:
            amplification._client = original_client
            amplification.AMPLIFICATION_TIMEOUT_SECONDS = original_timeout

        self.assertEqual(result, [{"symbol": "room", "question": "What associations do you have with room?"}])

    def test_fallback_questions_detect_obvious_ambiguous_symbols(self):
        result = amplification._fallback_amplification_questions(
            "An angry man stood in a dark room while a quiet woman watched.",
            {},
        )

        self.assertEqual(
            result,
            [
                {"symbol": "angry man", "question": "What comes to mind when you think about angry man?"},
                {"symbol": "quiet woman", "question": "What comes to mind when you think about quiet woman?"},
                {"symbol": "dark room", "question": "What does dark room feel like or remind you of?"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
