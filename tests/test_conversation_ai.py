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
resolve_groq_model_id = ai_module.resolve_groq_model_id


class ConversationAITests(unittest.IsolatedAsyncioTestCase):
    def make_service(self, content=None, error=None):
        service = AIService.__new__(AIService)

        def create(**kwargs):
            service.captured_kwargs = kwargs
            service.captured_messages = kwargs["messages"]
            if error:
                raise error
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
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "ValueError")

    async def test_exact_groq_json_mode_400_is_prevented_by_explicit_system_instruction(self):
        class FakeBadRequestError(Exception):
            status_code = 400
            code = None
            body = {"error": {
                "message": "'messages' must contain the word 'json' in some form, to use 'response_format' of type 'json_object'.",
                "type": "invalid_request_error", "param": "messages", "code": None
            }}
            response = SimpleNamespace(headers={"x-request-id": "req-json-mode"})

        service = self.make_service()

        async def groq_json_mode_guard(**kwargs):
            service.captured_kwargs = kwargs
            service.captured_messages = kwargs["messages"]
            if not any("json" in str(message.get("content", "")).lower() for message in kwargs["messages"]):
                raise FakeBadRequestError("Groq rejected JSON mode")
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"response":"TechnovaHub provides IT Services, AI Automation, and Digital Transformation Solutions.","intent":"continue"}'))],
                usage=SimpleNamespace(total_tokens=20),
            )

        service.async_client.chat.completions.create = groq_json_mode_guard
        result = await service.get_conversation_response(
            "What services does TechnovaHub provide?", "CA-json", "Use company facts only"
        )
        system_message = service.captured_messages[0]["content"]
        self.assertIn("json", system_message.lower())
        self.assertIn('"response"', system_message)
        self.assertIn('"intent"', system_message)
        self.assertEqual(service.captured_kwargs["response_format"], {"type": "json_object"})
        self.assertTrue(result["success"])
        self.assertEqual(result["response"], "TechnovaHub provides IT Services, AI Automation, and Digital Transformation Solutions.")

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

    async def test_retired_groq_model_is_migrated_to_supported_model(self):
        self.assertEqual(resolve_groq_model_id("llama-3.1-8b-instant"), "openai/gpt-oss-20b")
        self.assertEqual(resolve_groq_model_id("openai/gpt-oss-20b"), "openai/gpt-oss-20b")
        service = self.make_service('{"response":"Ready","intent":"continue"}')
        service.model = resolve_groq_model_id("llama-3.1-8b-instant")
        await service.get_conversation_response("Hello", "CA-test", "Reply briefly")
        self.assertEqual(service.captured_kwargs["model"], "openai/gpt-oss-20b")

    async def test_groq_404_metadata_is_safe_and_keeps_request_id(self):
        class FakeNotFoundError(Exception):
            status_code = 404
            code = None
            body = {"error": {"message": "model not found; do not echo caller text", "type": "invalid_request_error", "code": "model_not_found"}}
            response = SimpleNamespace(headers={"x-request-id": "req-test-123"})

        service = self.make_service(error=FakeNotFoundError("Authorization: Bearer secret-value"))
        result = await service.get_conversation_response("What services?", "CA-test", "Use company knowledge")
        self.assertFalse(result["success"])
        self.assertEqual(result["error_status"], 404)
        self.assertEqual(result["error_code"], "model_not_found")
        self.assertEqual(result["provider_type"], "invalid_request_error")
        self.assertEqual(result["request_id"], "req-test-123")
        self.assertNotIn("secret-value", result["error"])
        self.assertNotIn("caller text", result["error"])

    async def test_groq_400_logs_safe_provider_message_and_invalid_parameter(self):
        class FakeBadRequestError(Exception):
            status_code = 400
            code = None
            body = {"error": {
                "message": "Unsupported parameter max_tokens for model; key=gsk_secret; prompt=What services does TechnovaHub provide?",
                "type": "invalid_request_error", "code": None, "param": "max_tokens"
            }}
            response = SimpleNamespace(headers={"x-request-id": "req-safe-400"})

        customer_text = "What services does TechnovaHub provide?"
        service = self.make_service(error=FakeBadRequestError("unsafe raw exception"))
        result = await service.get_conversation_response(customer_text, "CA-test", "Use configured company knowledge")
        self.assertFalse(result["success"])
        self.assertEqual(result["error_status"], 400)
        self.assertEqual(result["error_param"], "max_tokens")
        self.assertEqual(result["request_id"], "req-safe-400")
        self.assertIn("Unsupported parameter max_tokens", result["provider_message"])
        self.assertIn("[GROQ_KEY_REDACTED]", result["provider_message"])
        self.assertIn("[customer text redacted]", result["provider_message"])
        self.assertNotIn("gsk_secret", result["provider_message"])
        self.assertNotIn(customer_text, result["provider_message"])

    async def test_technovahub_english_expected_answer_is_returned_in_api_schema(self):
        answer = "TechnovaHub provides IT Services, AI Automation, and Digital Transformation Solutions."
        service = self.make_service('{"response":"' + answer + '","intent":"continue"}')
        result = await service.get_conversation_response(
            "What services does TechnovaHub provide?", "CA-services",
            "Only answer from this company knowledge: TechnovaHub provides IT Services, AI Automation, and Digital Transformation Solutions."
        )
        self.assertEqual(result, {
            "success": True,
            "response": answer,
            "intent": "continue",
            "duration": result["duration"],
            "tokens_used": 12,
        })
        self.assertIn("What services does TechnovaHub provide?", service.captured_messages[-1]["content"])

    async def test_live_turn_uses_async_groq_and_json_mode(self):
        service = self.make_service('{"response":"Vanakkam","intent":"continue"}')
        result = await service.get_conversation_response("வணக்கம்", "CA-test", "Reply in Tamil")
        self.assertTrue(result["success"])
        self.assertEqual(result["response"], "Vanakkam")
        self.assertEqual(service.captured_messages[-1]["role"], "user")
        self.assertEqual(service.captured_kwargs["response_format"], {"type": "json_object"})
        self.assertEqual(service.captured_kwargs["reasoning_effort"], "low")
        self.assertFalse(service.captured_kwargs["include_reasoning"])
        self.assertGreaterEqual(service.captured_kwargs["max_completion_tokens"], 512)
        self.assertNotIn("max_tokens", service.captured_kwargs)

    async def test_exact_technovahub_tamil_tanglish_example_and_follow_up(self):
        import json

        knowledge = "TechnovaHub offers IT Services, AI Automation, and Digital Transformation Solutions."
        first_answer = "TechnovaHub நிறுவனம் IT Services, AI Automation, மற்றும் Digital Transformation Solutions வழங்குகிறது. உங்களுக்கு எந்த service பற்றி தெரிந்துகொள்ள வேண்டும்?"
        second_answer = "AI Automation மூலம் மீண்டும் மீண்டும் செய்யும் வேலைகளை தானியக்கமாக்கி, நேரத்தையும் செலவையும் குறைக்கலாம்."
        responses = [
            '{"response":' + json.dumps(first_answer, ensure_ascii=False) + ',"intent":"continue"}',
            '{"response":' + json.dumps(second_answer, ensure_ascii=False) + ',"intent":"continue"}',
        ]
        service = self.make_service()

        async def create_turn(**kwargs):
            service.captured_kwargs = kwargs
            service.captured_messages = kwargs["messages"]
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=responses.pop(0)))],
                usage=SimpleNamespace(total_tokens=45),
            )

        service.async_client.chat.completions.create = create_turn
        prompt = f"Reply in Tamil. Business information: {knowledge}"
        first = await service.get_conversation_response(
            "Hello, TechnovaHub என்னென்ன services provide பண்றீங்க?", "CA-example", prompt, {"locale": "ta-IN"}
        )
        self.assertEqual(first["response"], first_answer)
        self.assertIn(knowledge, service.captured_messages[0]["content"])

        second = await service.get_conversation_response(
            "AI Automation பற்றி சொல்லுங்க", "CA-example", prompt, {"locale": "ta-IN"}
        )
        self.assertEqual(second["response"], second_answer)
        self.assertEqual(len(service.conversation_history["CA-example"]), 4)
        self.assertIn("Caller said: AI Automation பற்றி சொல்லுங்க", service.captured_messages[-1]["content"])


if __name__ == "__main__":
    unittest.main()
