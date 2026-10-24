"""
Production AI Service using the Groq chat completions API
"""
import time
import json
import re
from typing import List, Dict, Optional
from groq import AsyncGroq, Groq
from config.settings import settings
from utils.logger import setup_logger
from utils.exceptions import AIException

logger = setup_logger(__name__)
CONVERSATION_INTENTS = {
    "continue", "offer_discounts", "discount_yes", "discount_no",
    "human_transfer", "end_call", "clarify",
}

CONVERSATION_JSON_INSTRUCTION = """Return a valid json object only. Do not include Markdown.
Required schema: {"response":"nonempty spoken reply in the configured language","intent":"continue"}.
The response field must be a nonempty string. The intent field must be one of continue, offer_discounts, discount_yes, discount_no, human_transfer, end_call, clarify.
Use intent for the existing transfer and completion behavior. Do not add transfer_required or end_call booleans."""

MODEL_MIGRATIONS = {
    # Groq retired this model for standard production use on 2026-08-16.
    # Keep old Render environment overrides from continuing to send 404s.
    "llama-3.1-8b-instant": "openai/gpt-oss-20b",
}


def resolve_groq_model_id(model_id: str) -> str:
    configured = str(model_id or "").strip()
    return MODEL_MIGRATIONS.get(configured, configured)


def _sanitize_provider_message(message, customer_text=""):
    """Keep useful provider diagnostics while removing credentials and caller data."""
    safe = str(message or "")
    if customer_text:
        safe = safe.replace(str(customer_text), "[customer text redacted]")
    safe = re.sub(r"(?i)Bearer\s+[A-Za-z0-9._~+/-]+=*", "Bearer [REDACTED]", safe)
    safe = re.sub(r"\bgsk_[A-Za-z0-9_-]+", "[GROQ_KEY_REDACTED]", safe)
    safe = re.sub(
        r"(?i)(api[_-]?key|authorization)(\s*[=:]\s*)([^,;\s}\]]+)",
        r"\1\2[REDACTED]", safe
    )
    safe = re.sub(r"\bCA[a-fA-F0-9]{32}\b", "[CALL_SID_REDACTED]", safe)
    safe = re.sub(r"\b\+?[0-9][0-9 .()/-]{7,}[0-9]\b", "[PHONE_REDACTED]", safe)
    return safe[:600]


def _provider_error_metadata(error, customer_text=""):
    """Extract safe provider diagnostics without logging request content or credentials."""
    body = getattr(error, "body", None)
    details = body.get("error", body) if isinstance(body, dict) else {}
    details = details if isinstance(details, dict) else {}
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", {}) or {}
    provider_message = details.get("message") or "Provider response did not include an error message"
    return {
        "error_type": type(error).__name__,
        "status": getattr(error, "status_code", None),
        "code": str(details.get("code") or getattr(error, "code", "") or "")[:80] or None,
        "provider_type": str(details.get("type") or "")[:80] or None,
        "param": str(details.get("param") or getattr(error, "param", "") or "")[:100] or None,
        "message": _sanitize_provider_message(provider_message, customer_text),
        "request_id": str(headers.get("x-request-id") or headers.get("request-id") or "")[:100] or None,
    }

class AIService:
    """AI Service using Groq chat completions."""
    
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise AIException("GROQ_API_KEY not configured")

        configured_model = str(settings.AI_MODEL or "").strip()
        self.model = resolve_groq_model_id(configured_model)
        if self.model != configured_model:
            warning = getattr(logger, "warning", logger.info)
            warning("Retired Groq model configuration migrated", extra={
                "configured_model": configured_model,
                "active_model": self.model,
                "stage": "model_migration",
            })
        
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.async_client = AsyncGroq(api_key=settings.GROQ_API_KEY, timeout=settings.AI_TIMEOUT)
        self.conversation_history: Dict[str, List[dict]] = {}
        
        self.system_prompt = """You are a helpful voice assistant. 
Keep responses concise, natural, and conversational.
Speak in short, clear sentences perfect for voice.
Avoid long paragraphs or technical jargon unless asked."""
        
        logger.info("✓ AI Service initialized (Groq)")
    
    async def get_response(
        self,
        user_message: str,
        call_id: str = "default",
        context: Optional[dict] = None
    ) -> dict:
        """
        Get AI response with conversation memory
        
        Args:
            user_message: User's text input
            call_id: Unique conversation identifier
            context: Optional additional context
        
        Returns:
            dict with AI response and metadata
        """
        start_time = time.time()
        
        try:
            # Build message history
            messages = self._build_messages(user_message, call_id)
            
            logger.info("Generating AI response", extra={"call_id": call_id, "input_chars": len(user_message)})
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.active_model,
                messages=messages,
                temperature=settings.AI_TEMPERATURE,
                max_tokens=settings.AI_MAX_TOKENS,
                top_p=1,
                stream=False
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Update conversation history
            self._update_history(call_id, user_message, ai_response)
            
            duration = time.time() - start_time
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0
            
            logger.info("AI response generated", extra={"call_id": call_id, "response_chars": len(ai_response), "duration_seconds": round(duration, 3)})
            
            return {
                "success": True,
                "response": ai_response,
                "model": self.active_model,
                "tokens_used": tokens_used,
                "duration": duration
            }

        except Exception as e:
            provider = _provider_error_metadata(e, user_message)
            logger.error("AI request failed", extra={
                "call_id": call_id, "stage": "groq_response", **provider
            })
            return {
                "success": False,
                "response": "I'm having trouble processing that. Could you try again?",
                "error": f"Groq request failed ({provider['error_type']}, HTTP {provider['status'] or 'unknown'})",
                "error_type": provider["error_type"],
                "error_status": provider["status"],
                "error_code": provider["code"],
                "provider_type": provider["provider_type"],
                "error_param": provider["param"],
                "provider_message": provider["message"],
                "request_id": provider["request_id"],
                "duration": time.time() - start_time
            }

    async def get_conversation_response(
        self,
        user_message: str,
        call_id: str,
        system_prompt: str,
        conversation_state: Optional[dict] = None
    ) -> dict:
        """Generate a concise, structured turn for a live phone conversation."""
        start_time = time.time()
        try:
            history = self.conversation_history.get(call_id, [])[-10:]
            state_text = json.dumps(conversation_state or {}, ensure_ascii=False)
            messages = [
                {"role": "system", "content": f"{system_prompt.strip()}\n\n{CONVERSATION_JSON_INSTRUCTION}"},
                *history,
                {"role": "user", "content": f"Conversation state: {state_text}\nCaller said: {user_message}"}
            ]
            result = await self.async_client.chat.completions.create(
                model=self.active_model,
                messages=messages,
                temperature=settings.AI_TEMPERATURE,
                # Groq now documents max_completion_tokens; max_tokens is
                # deprecated. GPT-OSS also spends completion tokens on reasoning.
                max_completion_tokens=max(int(settings.AI_MAX_TOKENS), 512),
                stream=False,
                reasoning_effort="low",
                include_reasoning=False,
                response_format={"type": "json_object"}
            )
            parsed = json.loads(result.choices[0].message.content or "")
            if not isinstance(parsed, dict):
                raise ValueError("Conversation response must be a JSON object")
            answer = parsed.get("response")
            intent = parsed.get("intent")
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("Conversation response requires a nonempty response string")
            if not isinstance(intent, str) or intent.strip().lower() not in CONVERSATION_INTENTS:
                raise ValueError("Conversation response contains an unsupported intent")
            answer = answer.strip()
            intent = intent.strip().lower()
            if intent == "offer_discounts" and not (conversation_state or {}).get("discountAsked"):
                configured_question = str((conversation_state or {}).get("discountQuestion") or "").strip()
                if configured_question:
                    answer = configured_question

            self._update_history(call_id, user_message, answer)
            return {
                "success": True,
                "response": answer,
                "intent": intent,
                "duration": time.time() - start_time,
                "tokens_used": getattr(getattr(result, "usage", None), "total_tokens", 0)
            }
        except Exception as e:
            provider = _provider_error_metadata(e, user_message)
            logger.error("Conversational AI turn failed", extra={
                "call_id": call_id,
                "stage": "groq_response" if provider["status"] is not None else "response_validation",
                "provider_status": provider["status"],
                "provider_code": provider["code"],
                "provider_type": provider["provider_type"],
                "provider_param": provider["param"],
                "provider_message": provider["message"],
                "request_id": provider["request_id"],
                "error_type": provider["error_type"],
            })
            return {
                "success": False,
                "response": "I'm sorry, I'm having trouble right now. Please try again or ask me to connect you to our team.",
                "intent": "clarify",
                "error": f"Groq request failed ({provider['error_type']}, HTTP {provider['status'] or 'unknown'})",
                "error_type": provider["error_type"],
                "error_status": provider["status"],
                "error_code": provider["code"],
                "provider_type": provider["provider_type"],
                "error_param": provider["param"],
                "provider_message": provider["message"],
                "request_id": provider["request_id"],
                "duration": time.time() - start_time
            }
    
    def _build_messages(self, user_message: str, call_id: str) -> List[dict]:
        """Build message list with history"""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation history (last 10 messages)
        if call_id in self.conversation_history:
            history = self.conversation_history[call_id][-10:]
            messages.extend(history)
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def _update_history(self, call_id: str, user_msg: str, ai_msg: str):
        """Update conversation history"""
        if call_id not in self.conversation_history:
            self.conversation_history[call_id] = []
        
        self.conversation_history[call_id].extend([
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": ai_msg}
        ])
        
        # Keep only last 20 messages (10 exchanges)
        if len(self.conversation_history[call_id]) > 20:
            self.conversation_history[call_id] = \
                self.conversation_history[call_id][-20:]
    
    async def get_streaming_response(
        self,
        user_message: str,
        call_id: str = "default"
    ):
        """Stream AI response for real-time output"""
        try:
            messages = self._build_messages(user_message, call_id)
            
            stream = self.client.chat.completions.create(
                model=self.active_model,
                messages=messages,
                temperature=settings.AI_TEMPERATURE,
                max_tokens=settings.AI_MAX_TOKENS,
                stream=True
            )
            
            full_response = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
            
            # Update history after streaming completes
            self._update_history(call_id, user_message, full_response)
            
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            yield f"Error: {str(e)}"
    
    def reset_conversation(self, call_id: str = None):
        """Clear conversation history"""
        if call_id:
            self.conversation_history.pop(call_id, None)
            logger.info(f"Conversation reset: {call_id}")
        else:
            self.conversation_history.clear()
            logger.info("All conversations reset")
    
    def set_system_prompt(self, prompt: str):
        """Update system prompt"""
        self.system_prompt = prompt
        logger.info("System prompt updated")
    
    def get_conversation_length(self, call_id: str) -> int:
        """Get number of messages in conversation"""
        return len(self.conversation_history.get(call_id, []))
    
    def health_check(self) -> bool:
        """Check if service is healthy"""
        try:
            # Simple test call
            response = self.client.chat.completions.create(
                model=self.active_model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except:
            return False

    @property
    def active_model(self) -> str:
        return getattr(self, "model", None) or resolve_groq_model_id(settings.AI_MODEL)
