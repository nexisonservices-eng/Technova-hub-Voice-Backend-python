"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    services: dict
    version: str

class AudioProcessRequest(BaseModel):
    call_id: str = Field(..., description="Unique call identifier")
    audio_data: str = Field(..., description="Base64 or hex encoded audio")
    format: str = Field(default="wav", description="Audio format")
    language: Optional[str] = Field(default="en", description="Language code")

class TranscriptionResponse(BaseModel):
    success: bool
    text: str
    language: str
    confidence: Optional[float] = None
    duration: float

class AIResponse(BaseModel):
    success: bool
    response: str
    model: str
    tokens_used: Optional[int] = None
    duration: float

class TTSResponse(BaseModel):
    success: bool
    audio_data: str
    format: str
    duration: float

class PipelineResponse(BaseModel):
    success: bool
    call_id: str
    transcription: str
    ai_response: str
    audio_data: str
    audio_format: str
    total_duration: float
    breakdown: dict

class WebSocketMessage(BaseModel):
    type: str
    call_id: str
    data: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    code: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)