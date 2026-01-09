"""
Main AI Pipeline: STT → AI → TTS
Orchestrates the complete voice processing flow
"""
import time
from typing import Dict
from services.stt_service import STTService
from services.ai_service import AIService
from services.tts_service import TTSService
from utils.logger import setup_logger
from utils.exceptions import AIServiceException

logger = setup_logger(__name__)

class AIPipeline:
    """Complete AI processing pipeline"""
    
    def __init__(self):
        self.stt = STTService()
        self.ai = AIService()
        self.tts = TTSService()
        logger.info("✓ AI Pipeline initialized")
    
    async def process_audio(
        self,
        audio_data: bytes,
        call_id: str,
        language: str = "en"
    ) -> Dict:
        """
        Complete pipeline: Audio → Text → AI → Speech
        
        Args:
            audio_data: Input audio bytes
            call_id: Unique call identifier
            language: Language code
        
        Returns:
            Complete pipeline response with all stages
        """
        start_time = time.time()
        
        try:
            # Stage 1: Speech-to-Text
            logger.info(f"[{call_id}] Stage 1: STT")
            stt_result = await self.stt.transcribe_audio(audio_data, language)
            
            if not stt_result["success"]:
                return self._error_response(
                    call_id,
                    "STT failed",
                    stt_result.get("error", "Unknown error")
                )
            
            user_text = stt_result["text"]
            logger.info(f"[{call_id}] User: {user_text}")
            
            # Stage 2: AI Processing
            logger.info(f"[{call_id}] Stage 2: AI")
            ai_result = await self.ai.get_response(user_text, call_id)
            
            if not ai_result["success"]:
                return self._error_response(
                    call_id,
                    "AI failed",
                    ai_result.get("error", "Unknown error")
                )
            
            ai_response = ai_result["response"]
            logger.info(f"[{call_id}] AI: {ai_response}")
            
            # Stage 3: Text-to-Speech
            logger.info(f"[{call_id}] Stage 3: TTS")
            tts_result = await self.tts.text_to_speech_bytes(ai_response)
            
            if not tts_result["success"]:
                return self._error_response(
                    call_id,
                    "TTS failed",
                    tts_result.get("error", "Unknown error")
                )
            
            total_duration = time.time() - start_time
            
            logger.info(f"[{call_id}] ✓ Pipeline completed in {total_duration:.2f}s")
            
            return {
                "success": True,
                "call_id": call_id,
                "transcription": user_text,
                "ai_response": ai_response,
                "audio_data": tts_result["audio_data"].hex(),
                "audio_format": tts_result["format"],
                "total_duration": total_duration,
                "breakdown": {
                    "stt_duration": stt_result["duration"],
                    "ai_duration": ai_result["duration"],
                    "tts_duration": tts_result["duration"]
                },
                "metadata": {
                    "language": stt_result["language"],
                    "confidence": stt_result.get("confidence", 0),
                    "tokens_used": ai_result.get("tokens_used", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"[{call_id}] Pipeline error: {str(e)}")
            return self._error_response(call_id, "Pipeline error", str(e))
    
    async def process_text(self, text: str, call_id: str) -> Dict:
        """
        Process text input directly (skip STT)
        
        Args:
            text: User input text
            call_id: Unique call identifier
        
        Returns:
            AI response with audio
        """
        start_time = time.time()
        
        try:
            # Stage 1: AI Processing
            logger.info(f"[{call_id}] Processing text: {text}")
            ai_result = await self.ai.get_response(text, call_id)
            
            if not ai_result["success"]:
                return self._error_response(call_id, "AI failed", ai_result.get("error"))
            
            ai_response = ai_result["response"]
            
            # Stage 2: Text-to-Speech
            tts_result = await self.tts.text_to_speech_bytes(ai_response)
            
            if not tts_result["success"]:
                return self._error_response(call_id, "TTS failed", tts_result.get("error"))
            
            total_duration = time.time() - start_time
            
            return {
                "success": True,
                "call_id": call_id,
                "ai_response": ai_response,
                "audio_data": tts_result["audio_data"].hex(),
                "audio_format": tts_result["format"],
                "total_duration": total_duration,
                "breakdown": {
                    "ai_duration": ai_result["duration"],
                    "tts_duration": tts_result["duration"]
                }
            }
            
        except Exception as e:
            logger.error(f"[{call_id}] Text processing error: {str(e)}")
            return self._error_response(call_id, "Processing error", str(e))
    
    def reset_conversation(self, call_id: str = None):
        """Reset conversation history"""
        self.ai.reset_conversation(call_id)
    
    def health_check(self) -> Dict:
        """Check health of all services"""
        return {
            "stt": self.stt.health_check(),
            "ai": self.ai.health_check(),
            "tts": self.tts.health_check()
        }
    
    def _error_response(self, call_id: str, stage: str, error: str) -> Dict:
        """Generate error response"""
        return {
            "success": False,
            "call_id": call_id,
            "stage": stage,
            "error": error
        }