"""
Centralized Configuration Management
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional, List
from pathlib import Path
import json


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    APP_NAME: str = "AI Voice Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 4000

    GROQ_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None

    WHISPER_MODEL: str = "distil-whisper-large-v3-en"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_LANGUAGE: str = "en"

    AI_PROVIDER: str = "groq"
    AI_MODEL: str = "llama-3.1-8b-instant"
    AI_MAX_TOKENS: int = 150
    AI_TEMPERATURE: float = 0.7
    AI_TIMEOUT: int = 30

    TTS_PROVIDER: str = "edge"
    TTS_VOICE: str = "en-GB-SoniaNeural"
    TTS_RATE: str = "+0%"
    TTS_VOLUME: str = "+0%"

    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 100
    WS_MESSAGE_QUEUE_SIZE: int = 100

    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHANNELS: int = 1
    AUDIO_FORMAT: str = "wav"

    MAX_WORKERS: int = 4
    REQUEST_TIMEOUT: int = 60
    MAX_CONCURRENT_REQUESTS: int = 10

    ENABLE_CACHE: bool = False
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 3600

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_DIR: str = "logs"

    CORS_ORIGINS_RAW: str = "*"
    API_KEY_HEADER: str = "X-API-Key"
    ENABLE_AUTH: bool = False
    PYTHON_API_KEY: Optional[str] = None

    # NODE_BACKEND_URL: str = "http://localhost:5000"
    NODE_BACKEND_URL: str = "https://technova-hub-voice-backend-node-hxg7.onrender.com"
    NODE_BACKEND_INTERNAL_API_KEY: Optional[str] = None
    NODE_BACKEND_TIMEOUT: int = 10
    NODE_BACKEND_MAX_RETRIES: int = 3
    NODE_BACKEND_RETRY_DELAY: float = 1.0

    HEALTH_CHECK_TIMEOUT: int = 10
    HEALTH_CHECK_MAX_RETRIES: int = 3
    HEALTH_CHECK_RETRY_DELAY: float = 1.0
    HEALTH_CHECK_RETRY_BACKOFF: float = 2.0

    ENABLE_METRICS: bool = False
    METRICS_PORT: int = 9090

    @property
    def CORS_ORIGINS(self) -> List[str]:
        raw = self.CORS_ORIGINS_RAW
        if not raw:
            return ["*"]

        raw = raw.strip()
        if raw == "*":
            return ["*"]

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(o) for o in parsed if o]
            raise ValueError("Must be a list")
        except (json.JSONDecodeError, ValueError):
            origins = [o.strip() for o in raw.split(',') if o.strip()]
            if origins:
                return origins
            return ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

Path(settings.LOG_DIR).mkdir(exist_ok=True)
Path("models").mkdir(exist_ok=True)
