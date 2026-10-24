import unittest
import importlib.util
import sys
import types
from types import SimpleNamespace
from pathlib import Path


# Import this unit under lightweight dependency shims so its logic tests do not
# require loading the STT/TTS services or making a Groq API connection.
groq_module = types.ModuleType("groq")
groq_module.Groq = object
groq_module.AsyncGroq = object
sys.modules.setdefault("groq", groq_module)

config_package = types.ModuleType("config")
config_package.__path__ = []
sys.modules.setdefault("config", config_package)
settings_module = types.ModuleType("config.settings")
settings_module.settings = SimpleNamespace(AI_MODEL="test-model", AI_TEMPERATURE=0, AI_MAX_TOKENS=200)
sys.modules.setdefault("config.settings", settings_module)

logger_module = types.ModuleType("utils.logger")
logger_module.setup_logger = lambda _name: SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None)
sys.modules.setdefault("utils.logger", logger_module)

utils_package = types.ModuleType("utils")
utils_package.__path__ = []
sys.modules.setdefault("utils", utils_package)
exceptions_module = types.ModuleType("utils.exceptions")
exceptions_module.AIException = type("AIException", (Exception,), {})
sys.modules.setdefault("utils.exceptions", exceptions_module)

service_path = Path(__file__).parents[1] / "services" / "ai_service.py"
spec = importlib.util.spec_from_file_location("conversation_ai_service_under_test", service_path)
ai_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai_module)
AIService = ai_module.AIService


class ConversationAITests(unittest.IsolatedAsyncioTestCase):
    def make_service(self, content=None, error=None):
        service = AIService.__new__(AIService)

        def create(**kwargs):
            if error:
                raise error
            service.captured_kwargs = kwargs
            service.captured_messages = kwargs["messages"]
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                usage=SimpleNamespace(total_tokens=12),
            )

        service.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )
        async def create_async(**kwargs):
            return create(**kwargs)

        service.async_client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create_async))
        )
        service.conversation_history = {}
        return service

    async def test_tamil_unicode_is_preserved_and_history_is_scoped_by_call(self):
        tamil = "\u0ba8\u0bae\u0bb8\u0bcd\u0b95\u0bbe\u0bb0\u0bae\u0bcd"
        service = self.make_service('{"response":"' + tamil + '","intent":"continue"}')
        result = await service.get_conversation_response(tamil, "CA-test", "Reply in Tamil", {"locale": "ta-IN"})

        self.assertTrue(result["success"])
        self.assertEqual(result["response"], tamil)
        self.assertIn(tamil, service.captured_messages[-1]["content"])
        self.assertEqual(service.conversation_history["CA-test"][0]["content"], tamil)

    async def test_intent_is_limited_to_supported_values(self):
        service = self.make_service('{"response":"Hello","intent":"unknown-intent"}')
        result = await service.get_conversation_response("Hello", "CA-test", "Reply in English")
        self.assertEqual(result["intent"], "clarify")

    async def test_configured_discount_question_is_spoken_and_saved_to_history(self):
        question = "Would you like to hear about our current offer?"
        service = self.make_service('{"response":"Would you like a discount?","intent":"offer_discounts"}')
        result = await service.get_conversation_response(
            "Do you have any offers?", "CA-test", "Reply naturally", {"discountAsked": False, "discountQuestion": question}
        )
        self.assertEqual(result["response"], question)
        self.assertEqual(service.conversation_history["CA-test"][-1]["content"], question)

    async def test_provider_failure_is_reported_without_throwing(self):
        service = self.make_service(error=RuntimeError("provider unavailable"))
        result = await service.get_conversation_response("Hello", "CA-test", "Reply in English")
        self.assertFalse(result["success"])
        self.assertEqual(result["intent"], "clarify")
        self.assertEqual(result["error_type"], "RuntimeError")

    async def test_live_turn_uses_async_groq_and_json_mode(self):
        service = self.make_service('{"response":"Vanakkam","intent":"continue"}')
        result = await service.get_conversation_response("வணக்கம்", "CA-test", "Reply in Tamil")
        self.assertTrue(result["success"])
        self.assertEqual(result["response"], "Vanakkam")
        self.assertEqual(service.captured_messages[-1]["role"], "user")
        self.assertEqual(service.captured_kwargs["response_format"], {"type": "json_object"})
        self.assertEqual(service.captured_kwargs["reasoning_effort"], "low")


if __name__ == "__main__":
    unittest.main()
