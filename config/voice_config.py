"""
Centralized Voice Configuration for Python TTS Service
Single source of truth for all voice-related settings
"""

# Allowed voices - single source of truth
ALLOWED_VOICES = {
    "en-GB-SoniaNeural": {
        "name": "English (GB) – Female",
        "gender": "Female",
        "locale": "en-GB",
        "language": "en-GB"
    },
    "en-GB-RyanNeural": {
        "name": "English (GB) – Male",
        "gender": "Male",
        "locale": "en-GB",
        "language": "en-GB"
    },
    "en-GB-LibbyNeural": {
        "name": "English (GB) – Female",
        "gender": "Female",
        "locale": "en-GB",
        "language": "en-GB"
    },
    "en-GB-ThomasNeural": {
        "name": "English (GB) – Male",
        "gender": "Male",
        "locale": "en-GB",
        "language": "en-GB"
    },
    "ta-IN-PallaviNeural": {
        "name": "Tamil – Female",
        "gender": "Female",
        "locale": "ta-IN",
        "language": "ta-IN"
    },
    "ta-IN-ValluvarNeural": {
        "name": "Tamil – Male", 
        "gender": "Male",
        "locale": "ta-IN",
        "language": "ta-IN"
    },
    "hi-IN-SwaraNeural": {
        "name": "Hindi – Female",
        "gender": "Female",
        "locale": "hi-IN",
        "language": "hi-IN"
    },
    "hi-IN-MadhurNeural": {
        "name": "Hindi – Male",
        "gender": "Male",
        "locale": "hi-IN", 
        "language": "hi-IN"
    }
}

# Default voice settings
DEFAULT_VOICE = "en-GB-SoniaNeural"  # English (GB) – Female
DEFAULT_LANGUAGE = "en-GB"  # English (GB)

# Provider settings
DEFAULT_PROVIDER = "edge"
ALLOWED_PROVIDERS = ["edge", "elevenlabs"]

# Validation helpers
def validate_voice(voice_id: str) -> bool:
    """Check if voice ID is allowed"""
    return voice_id in ALLOWED_VOICES

def validate_language(language: str) -> bool:
    """Check if language is allowed"""
    return language in ["en-GB", "ta-IN", "hi-IN"]

def get_voice_info(voice_id: str) -> dict:
    """Get voice information by ID"""
    return ALLOWED_VOICES.get(voice_id)

def get_voices_by_language(language: str) -> dict:
    """Get all voices for a specific language"""
    return {
        voice_id: info for voice_id, info in ALLOWED_VOICES.items()
        if info["language"] == language
    }

def get_voice_list_for_api() -> list:
    """Get formatted voice list for API response"""
    return [
        {
            "name": info["name"],
            "short_name": voice_id,
            "gender": info["gender"],
            "locale": info["locale"]
        }
        for voice_id, info in ALLOWED_VOICES.items()
    ]

def get_allowed_voice_ids() -> set:
    """Get set of allowed voice IDs"""
    return set(ALLOWED_VOICES.keys())

# Format validation error message
def get_voice_validation_error() -> str:
    """Get formatted error message with allowed voices"""
    allowed = sorted(ALLOWED_VOICES.keys())
    return f"Voice must be one of: {', '.join(allowed)}"
