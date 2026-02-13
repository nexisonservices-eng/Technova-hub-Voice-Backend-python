"""
Voice Broadcast TTS Endpoint
High-performance batch TTS generation for broadcast campaigns
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, validator
from typing import Optional
import edge_tts
import asyncio
import logging
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
async def generate_broadcast_tts(request: BroadcastTTSRequest):
    """
    Generate TTS audio for voice broadcast
    Returns raw audio bytes (MP3 format)
    
    This endpoint is optimized for batch processing:
    - No Whisper STT
    - No AI reasoning
    - Direct TTS generation only
    """
    try:
        logger.info(f"Generating TTS: {request.text[:50]}... (voice: {request.voice})")

        if request.provider == "edge":
            audio_data = await generate_edge_tts(
                request.text,
                request.voice,
                request.rate,
                request.volume
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported TTS provider: {request.provider}"
            )

        logger.info(f"TTS generated: {len(audio_data)} bytes")

        # Return raw audio bytes
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=broadcast.mp3",
                "Cache-Control": "public, max-age=31536000"  # Cache for 1 year
            }
        )

    except Exception as e:
        logger.error(f"TTS generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Edge TTS error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)


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