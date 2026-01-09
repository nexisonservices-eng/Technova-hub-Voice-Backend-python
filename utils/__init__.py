"""Utilities module"""
from .logger import setup_logger
from .exceptions import *

__all__ = [
    'setup_logger',
    'AIServiceException',
    'STTException',
    'AIException',
    'TTSException',
    'RateLimitException',
    'AuthenticationException',
    'TimeoutException'
]