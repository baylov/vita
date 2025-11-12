"""Tests for Gemini client module."""

import pytest
from unittest.mock import MagicMock, patch

from services.gemini.client import (
    GeminiClient,
    MODELS,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_SAFETY_SETTINGS,
)
from exceptions import GeminiInitializationError


class TestGeminiClient:
    """Tests for GeminiClient."""

    @patch("services.gemini.client.genai")
    def test_initialization_with_api_key(self, mock_genai):
        """Test successful initialization with API key."""
        client = GeminiClient(api_key="test-key")
        assert client.api_key == "test-key"
        mock_genai.configure.assert_called_once_with(api_key="test-key")

    @patch("services.gemini.client.genai", None)
    def test_initialization_without_genai_installed(self):
        """Test initialization fails when genai is not installed."""
        with pytest.raises(GeminiInitializationError):
            GeminiClient(api_key="test-key")

    @patch("services.gemini.client.genai")
    @patch("services.gemini.client.settings")
    def test_initialization_from_settings(self, mock_settings, mock_genai):
        """Test initialization uses settings.gemini_api_key."""
        mock_settings.gemini_api_key = "settings-key"
        client = GeminiClient()
        assert client.api_key == "settings-key"
        mock_genai.configure.assert_called_once_with(api_key="settings-key")

    @patch("services.gemini.client.genai")
    @patch("services.gemini.client.settings")
    def test_initialization_without_api_key_raises_error(self, mock_settings, mock_genai):
        """Test initialization fails without API key."""
        mock_settings.gemini_api_key = None
        with pytest.raises(GeminiInitializationError):
            GeminiClient()

    @patch("services.gemini.client.genai")
    def test_initialization_configure_error(self, mock_genai):
        """Test initialization fails when genai.configure raises error."""
        mock_genai.configure.side_effect = Exception("Configuration failed")
        with pytest.raises(GeminiInitializationError):
            GeminiClient(api_key="test-key")

    @patch("services.gemini.client.genai")
    def test_get_model_russian(self, mock_genai):
        """Test get_model returns correct model for Russian."""
        client = GeminiClient(api_key="test-key")
        model = client.get_model("ru")
        assert model == "gemini-pro"

    @patch("services.gemini.client.genai")
    def test_get_model_kazakh(self, mock_genai):
        """Test get_model returns correct model for Kazakh."""
        client = GeminiClient(api_key="test-key")
        model = client.get_model("kz")
        assert model == "gemini-pro"

    @patch("services.gemini.client.genai")
    def test_get_model_default(self, mock_genai):
        """Test get_model defaults to Russian model."""
        client = GeminiClient(api_key="test-key")
        model = client.get_model("en")
        assert model == "gemini-pro"

    @patch("services.gemini.client.genai")
    def test_get_generation_config_defaults(self, mock_genai):
        """Test get_generation_config with default parameters."""
        client = GeminiClient(api_key="test-key")
        config = client.get_generation_config()
        assert config["temperature"] == 0.7
        assert config["top_p"] == 0.95
        assert config["top_k"] == 40
        assert config["max_output_tokens"] == 500

    @patch("services.gemini.client.genai")
    def test_get_generation_config_custom(self, mock_genai):
        """Test get_generation_config with custom parameters."""
        client = GeminiClient(api_key="test-key")
        config = client.get_generation_config(
            temperature=0.5,
            top_p=0.9,
            top_k=20,
            max_output_tokens=1000,
        )
        assert config["temperature"] == 0.5
        assert config["top_p"] == 0.9
        assert config["top_k"] == 20
        assert config["max_output_tokens"] == 1000

    @patch("services.gemini.client.genai")
    def test_get_safety_settings(self, mock_genai):
        """Test get_safety_settings returns list."""
        client = GeminiClient(api_key="test-key")
        settings = client.get_safety_settings()
        assert isinstance(settings, list)
        assert len(settings) > 0
        assert all("category" in s and "threshold" in s for s in settings)

    @patch("services.gemini.client.genai")
    def test_get_request_timeout(self, mock_genai):
        """Test get_request_timeout returns correct value."""
        client = GeminiClient(api_key="test-key")
        timeout = client.get_request_timeout()
        assert timeout == DEFAULT_REQUEST_TIMEOUT
        assert timeout == 30
