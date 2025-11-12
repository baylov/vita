"""Google Gemini client initialization and configuration."""

import logging
from typing import Optional

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig, SafetySetting
except ImportError:
    genai = None

from settings import settings
from exceptions import GeminiInitializationError

logger = logging.getLogger(__name__)


# Model selection per language
MODELS = {
    "ru": "gemini-pro",
    "kz": "gemini-pro",
}

# Timeout configuration (in seconds)
DEFAULT_REQUEST_TIMEOUT = 30

# Safety settings for content generation
DEFAULT_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_UNSPECIFIED", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
]


class GeminiClient:
    """Google Gemini client wrapper with initialization and shared configuration."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini client.

        Args:
            api_key: Google Gemini API key (defaults to settings.gemini_api_key)

        Raises:
            GeminiInitializationError: If initialization fails or genai is not installed
        """
        if genai is None:
            raise GeminiInitializationError(
                "google-generativeai package is not installed. "
                "Install it with: pip install google-generativeai"
            )

        self.api_key = api_key or settings.gemini_api_key

        if not self.api_key:
            raise GeminiInitializationError(
                "Gemini API key not provided. "
                "Set GEMINI_API_KEY environment variable or pass api_key parameter."
            )

        try:
            genai.configure(api_key=self.api_key)
            logger.info("Gemini client configured successfully")
        except Exception as e:
            logger.error(f"Failed to configure Gemini client: {e}")
            raise GeminiInitializationError(f"Configuration failed: {e}")

    def get_model(self, language: str = "ru") -> str:
        """
        Get the model name for the given language.

        Args:
            language: Language code ('ru' or 'kz')

        Returns:
            Model name to use for the language
        """
        return MODELS.get(language, MODELS["ru"])

    def get_generation_config(
        self,
        temperature: float = 0.7,
        top_p: float = 0.95,
        top_k: int = 40,
        max_output_tokens: int = 500,
    ) -> dict:
        """
        Get generation configuration for API requests.

        Args:
            temperature: Controls randomness (0-2). Higher = more random
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            max_output_tokens: Maximum output length

        Returns:
            Generation config dict
        """
        return {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_output_tokens": max_output_tokens,
        }

    def get_safety_settings(self) -> list[dict]:
        """
        Get default safety settings for content generation.

        Returns:
            List of safety setting dicts
        """
        return DEFAULT_SAFETY_SETTINGS

    def get_request_timeout(self) -> int:
        """
        Get default request timeout in seconds.

        Returns:
            Timeout in seconds
        """
        return DEFAULT_REQUEST_TIMEOUT
