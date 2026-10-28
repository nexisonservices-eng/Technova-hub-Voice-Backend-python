"""
Voice Broadcast TTS Endpoint
High-performance batch TTS generation for broadcast campaigns
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, validator
from typing import Optional
import edge_tts
import asyncio
import logging
import re
import uuid
from googletrans import Translator
from config.voice_config import (
    ALLOWED_VOICES, 
    DEFAULT_VOICE, 
    DEFAULT_LANGUAGE,
    validate_voice,
    validate_language,
    get_voice_list_for_api,
    get_voice_validation_error
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tts", tags=["broadcast"])
_translation_cache = {}
_TAMIL_SCRIPT = re.compile(r"[\u0B80-\u0BFF]")


async def translate_for_tamil_tts(text: str, language: str) -> str:
    """Translate non-Tamil prompts before Tamil TTS; pass Tamil text through."""
    if language != "ta-IN" or not text.strip() or _TAMIL_SCRIPT.search(text):
        return text

    cached = _translation_cache.get(text)
    if cached:
        return cached

    try:
        async with Translator(service_urls=["translate.googleapis.com"]) as translator:
            result = await translator.translate(text, src="en", dest="ta")
        translated = str(result.text).strip()
        if not translated:
            raise ValueError("Translation returned empty text")

        if len(_translation_cache) >= 500:
            _translation_cache.pop(next(iter(_translation_cache)))
        _translation_cache[text] = translated
        return translated
    except Exception as exc:
        logger.exception("Tamil translation failed")
        raise HTTPException(
            status_code=502,
            detail="Tamil translation failed; no audio was generated. Please retry."
        ) from exc


class BroadcastTTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    voice: str = Field(default=DEFAULT_VOICE)  # Use centralized default
    provider: str = Field(default="edge")
    language: str = Field(default=DEFAULT_LANGUAGE)  # Use centralized default
    rate: Optional[str] = Field(default="+0%")
    volume: Optional[str] = Field(default="+0%")

    # Validate voice using centralized function
    @validator('voice')
    def validate_voice(cls, v):
        if not validate_voice(v):
            raise ValueError(get_voice_validation_error())
        return v

    # Validate language using centralized function
    @validator('language')
    def validate_language(cls, v, values):
        if not validate_language(v):
            raise ValueError(get_voice_validation_error())
        
        # Validate language matches voice
        if 'voice' in values:
            voice = values['voice']
            voice_info = ALLOWED_VOICES.get(voice)
            if voice_info and voice_info['language'] != v:
                raise ValueError(f'Voice {voice_info["name"]} requires language "{voice_info["language"]}"')
        return v


@router.post("/broadcast")
async def generate_broadcast_tts(request: BroadcastTTSRequest, http_request: Request):
    """
    Generate TTS audio for voice broadcast
    Returns raw audio bytes (MP3 format)
    
    This endpoint is optimized for batch processing:
    - No Whisper STT
    - No AI reasoning
    - Direct TTS generation only
    """
    request_id = (http_request.headers.get("X-Request-ID") or http_request.headers.get("X-Correlation-ID") or str(uuid.uuid4()))[:100]
    language = request.language
    voice = request.voice
    try:
        # Tamil text must be spoken by a Tamil voice even when a client sends
        # its default English voice/language settings.
        contains_tamil = bool(_TAMIL_SCRIPT.search(request.text))
        language = "ta-IN" if contains_tamil else request.language
        if contains_tamil and not voice.startswith("ta-IN-"):
            voice = "ta-IN-PallaviNeural"

        logger.info("Generating TTS", extra={"request_id": request_id, "language": language, "voice": voice, "provider": request.provider})
        speech_text = await translate_for_tamil_tts(request.text, language)

        if request.provider == "edge":
            audio_data = await generate_edge_tts(
                speech_text,
                voice,
                request.rate,
                request.volume
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported TTS provider: {request.provider}"
            )

        logger.info("TTS generated", extra={"language": language, "voice": voice, "provider": request.provider, "audio_bytes": len(audio_data), "format": "mp3"})
        if not audio_data:
            raise HTTPException(status_code=502, detail="TTS provider returned empty audio")

        # Return raw audio bytes
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=broadcast.mp3",
                "Cache-Control": "public, max-age=31536000"  # Cache for 1 year
                ,"X-Request-ID": request_id
            }
        )

    except HTTPException as exc:
        status_code = exc.status_code
        message = exc.detail if status_code < 500 and isinstance(exc.detail, str) else "TTS provider failed to generate audio"
        logger.exception("TTS request failed", extra={"request_id": request_id, "language": language, "voice": voice, "exception_type": type(exc).__name__, "provider": request.provider})
        return JSONResponse(status_code=status_code, content={"success": False, "error": {"code": "tts_request_failed", "message": message, "request_id": request_id}}, headers={"X-Request-ID": request_id})
    except Exception as exc:
        logger.exception("TTS generation failed", extra={"request_id": request_id, "language": language, "voice": voice, "exception_type": type(exc).__name__, "provider": request.provider})
        return JSONResponse(status_code=502, content={"success": False, "error": {"code": "tts_provider_failed", "message": "TTS provider failed to generate audio", "request_id": request_id}}, headers={"X-Request-ID": request_id})


async def generate_edge_tts(
    text: str,
    voice: str,
    rate: str,
    volume: str
) -> bytes:
    """
    Generate TTS using Microsoft Edge TTS
    """
    try:
        communicate = edge_tts.Communicate(
            text,
            voice,
            rate=rate,
            volume=volume
        )

        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        return audio_data

    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg:
            logger.error(f"❌ Edge TTS 403 Forbidden: Microsoft has updated their API. Please ensure edge-tts is >= 6.1.12")
            raise HTTPException(
                status_code=503,
                detail="Edge TTS service is currently unavailable (403 Forbidden). A library update on the server is required."
            )
        logger.exception("Edge TTS provider failed", extra={"exception_type": type(e).__name__})
        raise HTTPException(status_code=502, detail="TTS provider failed to generate audio") from e


@router.get("/voices")
async def list_broadcast_voices():
    """
    List available voices for broadcast
    Limited to 4 specified voices only
    """
    try:
        # Use centralized voice list
        allowed_voices = get_voice_list_for_api()
        return {"voices": allowed_voices, "count": len(allowed_voices)}

    except Exception as e:
        logger.error(f"Failed to list voices: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
