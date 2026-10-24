"""
Production AI Service with FREE Groq API
Groq is 10x faster than GPT-4 and completely FREE
"""
import time
import json
from typing import List, Dict, Optional
from groq import AsyncGroq, Groq
from config.settings import settings
from utils.logger import setup_logger
from utils.exceptions import AIException

logger = setup_logger(__name__)

class AIService:
    """AI Service using Groq (FREE and FAST)"""
    
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise AIException("GROQ_API_KEY not configured")
        
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
                model=settings.AI_MODEL,
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
                "model": settings.AI_MODEL,
                "tokens_used": tokens_used,
                "duration": duration
            }

        except Exception as e:
            logger.error("AI request failed", extra={"call_id": call_id, "error_type": type(e).__name__})
            return {
                "success": False,
                "response": "I'm having trouble processing that. Could you try again?",
                "error": str(e),
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
                {"role": "system", "content": system_prompt},
                *history,
                {"role": "user", "content": f"Conversation state: {state_text}\nCaller said: {user_message}"}
            ]
            result = await self.async_client.chat.completions.create(
                model=settings.AI_MODEL,
                messages=messages,
                temperature=settings.AI_TEMPERATURE,
                max_tokens=settings.AI_MAX_TOKENS,
                top_p=1,
                stream=False,
                reasoning_effort="low",
                response_format={"type": "json_object"}
            )
            parsed = json.loads(result.choices[0].message.content or "{}")
            answer = str(parsed.get("response") or "I'm sorry, I didn't catch that. Could you say that another way?").strip()
            intent = str(parsed.get("intent") or "clarify").strip().lower()
            allowed_intents = {"continue", "offer_discounts", "discount_yes", "discount_no", "human_transfer", "end_call", "clarify"}
            if intent not in allowed_intents:
                intent = "clarify"
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
            logger.error(
                "Conversational AI turn failed",
                extra={"call_id": call_id, "error_type": type(e).__name__,
                       "provider_status": getattr(e, "status_code", None),
                       "provider_code": str(getattr(e, "code", "") or "")[:60] or None},
            )
            return {
                "success": False,
                "response": "I'm sorry, I'm having trouble right now. Please try again or ask me to connect you to our team.",
                "intent": "clarify",
                "error": str(e),
                "error_type": type(e).__name__,
                "error_status": getattr(e, "status_code", None),
                "error_code": str(getattr(e, "code", "") or "")[:60] or None,
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
                model=settings.AI_MODEL,
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
                model=settings.AI_MODEL,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except:
            return False
