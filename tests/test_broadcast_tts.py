import unittest
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

# Keep the route tests independent from network/provider packages.
edge_tts_module = types.ModuleType("edge_tts")
edge_tts_module.Communicate = object
sys.modules.setdefault("edge_tts", edge_tts_module)
googletrans_module = types.ModuleType("googletrans")
googletrans_module.Translator = object
sys.modules.setdefault("googletrans", googletrans_module)
config_module = types.ModuleType("config")
config_module.__path__ = [str(Path(__file__).parents[1] / "config")]
sys.modules.setdefault("config", config_module)

from routers import broadcast_tts


class BroadcastTTSTests(unittest.IsolatedAsyncioTestCase):
    def request(self, text, voice="ta-IN-PallaviNeural", language="ta-IN"):
        return broadcast_tts.BroadcastTTSRequest(text=text, voice=voice, language=language)

    async def test_tamil_request_passes_selected_voice_and_language_to_provider(self):
        http_request = SimpleNamespace(headers={"X-Request-ID": "req-tamil"})
        with patch.object(broadcast_tts, "translate_for_tamil_tts", new=AsyncMock(return_value="வணக்கம்")), \
             patch.object(broadcast_tts, "generate_edge_tts", new=AsyncMock(return_value=b"mp3")) as generate:
            response = await broadcast_tts.generate_broadcast_tts(
                self.request("வணக்கம்"), http_request
            )
        self.assertEqual(response.body, b"mp3")
        self.assertEqual(generate.await_args.args[:2], ("வணக்கம்", "ta-IN-PallaviNeural"))
        self.assertEqual(response.headers["x-request-id"], "req-tamil")

    async def test_provider_failure_returns_structured_json_and_does_not_return_audio(self):
        http_request = SimpleNamespace(headers={"X-Request-ID": "req-fail"})
        with patch.object(broadcast_tts, "translate_for_tamil_tts", new=AsyncMock(return_value="வணக்கம்")), \
             patch.object(broadcast_tts, "generate_edge_tts", new=AsyncMock(side_effect=HTTPException(status_code=502, detail="provider error"))):
            response = await broadcast_tts.generate_broadcast_tts(
                self.request("வணக்கம்"), http_request
            )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.body, b'{"success":false,"error":{"code":"tts_request_failed","message":"TTS provider failed to generate audio","request_id":"req-fail"}}')

    async def test_translation_outage_does_not_block_tamil_voice_audio_generation(self):
        with patch.object(broadcast_tts, "Translator", side_effect=RuntimeError("translation unavailable")):
            result = await broadcast_tts.translate_for_tamil_tts("Your appointment is confirmed", "ta-IN", "req-translate")
        self.assertEqual(result, "Your appointment is confirmed")


if __name__ == "__main__":
    unittest.main()
