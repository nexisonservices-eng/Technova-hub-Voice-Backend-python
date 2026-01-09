"""
Custom exceptions for better error handling
"""

class AIServiceException(Exception):
    """Base exception for AI service"""
    def __init__(self, message: str, code: str = "SERVICE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class STTException(AIServiceException):
    """Speech-to-Text specific errors"""
    def __init__(self, message: str):
        super().__init__(message, "STT_ERROR")


class AIException(AIServiceException):
    """AI processing errors"""
    def __init__(self, message: str):
        super().__init__(message, "AI_ERROR")


class TTSException(AIServiceException):
    """Text-to-Speech errors"""
    def __init__(self, message: str):
        super().__init__(message, "TTS_ERROR")


class RateLimitException(AIServiceException):
    """Rate limiting errors"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, "RATE_LIMIT")


class AuthenticationException(AIServiceException):
    """Authentication errors"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_ERROR")


class TimeoutException(AIServiceException):
    """Timeout errors"""
    def __init__(self, message: str = "Request timeout"):
        super().__init__(message, "TIMEOUT")