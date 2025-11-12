"""Tests for Gemini analyzer module."""

import json
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta, timezone

from services.gemini.analyzer import (
    GeminiAnalyzer,
    RequestType,
    UrgencyLevel,
    ClassificationResult,
    ResponseResult,
    CachedClassification,
)
from services.gemini.client import GeminiClient
from exceptions import GeminiError


class TestClassificationResult:
    """Tests for ClassificationResult."""

    def test_classification_result_creation(self):
        """Test creating classification result."""
        result = ClassificationResult(
            request_type=RequestType.APPOINTMENT_BOOKING,
            urgency=UrgencyLevel.HIGH,
            specialist_suggestion="Dentist",
            confidence=0.95,
            reasoning="User wants to book an appointment",
        )
        assert result.request_type == RequestType.APPOINTMENT_BOOKING
        assert result.urgency == UrgencyLevel.HIGH
        assert result.specialist_suggestion == "Dentist"
        assert result.confidence == 0.95

    def test_classification_result_to_dict(self):
        """Test converting classification result to dict."""
        result = ClassificationResult(
            request_type=RequestType.COMPLAINT,
            urgency=UrgencyLevel.MEDIUM,
            specialist_suggestion=None,
            confidence=0.7,
        )
        result_dict = result.to_dict()
        assert result_dict["request_type"] == "complaint"
        assert result_dict["urgency"] == "medium"
        assert result_dict["specialist_suggestion"] is None
        assert result_dict["confidence"] == 0.7


class TestResponseResult:
    """Tests for ResponseResult."""

    def test_response_result_success(self):
        """Test creating successful response result."""
        result = ResponseResult(text="Hello, how can I help?", is_fallback=False)
        assert result.text == "Hello, how can I help?"
        assert result.is_fallback is False
        assert result.error is None

    def test_response_result_fallback(self):
        """Test creating fallback response result."""
        result = ResponseResult(
            text="Transmitting to admin",
            is_fallback=True,
            error="API timeout",
        )
        assert result.text == "Transmitting to admin"
        assert result.is_fallback is True
        assert result.error == "API timeout"


class TestCachedClassification:
    """Tests for CachedClassification."""

    def test_cache_not_expired(self):
        """Test cache expiration check for fresh entry."""
        result = ClassificationResult(
            request_type=RequestType.GENERAL_INQUIRY,
            urgency=UrgencyLevel.LOW,
        )
        cached = CachedClassification(result, ttl_seconds=3600)
        assert not cached.is_expired()

    def test_cache_expired(self):
        """Test cache expiration check for old entry."""
        result = ClassificationResult(
            request_type=RequestType.GENERAL_INQUIRY,
            urgency=UrgencyLevel.LOW,
        )
        cached = CachedClassification(result, ttl_seconds=1)
        # Set created_at to past
        cached.created_at = datetime.now(timezone.utc) - timedelta(seconds=2)
        assert cached.is_expired()


class TestGeminiAnalyzer:
    """Tests for GeminiAnalyzer."""

    @patch("services.gemini.analyzer.genai")
    def test_analyzer_initialization_with_client(self, mock_genai):
        """Test analyzer initialization with provided client."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            analyzer = GeminiAnalyzer(client=client)
            assert analyzer.client == client

    @patch("services.gemini.client.genai")
    def test_analyzer_initialization_creates_client(self, mock_genai):
        """Test analyzer creates client if not provided."""
        with patch("services.gemini.analyzer.GeminiClient") as mock_client_class:
            mock_client_class.return_value = MagicMock()
            analyzer = GeminiAnalyzer(api_key="test-key")
            assert analyzer.client is not None

    @patch("services.gemini.client.genai")
    def test_analyzer_initialization_with_custom_ttl(self, mock_genai):
        """Test analyzer initialization with custom cache TTL."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            analyzer = GeminiAnalyzer(client=client, cache_ttl=7200)
            assert analyzer.cache_ttl == 7200

    @patch("services.gemini.client.genai")
    def test_analyzer_initialization_with_notifier(self, mock_genai):
        """Test analyzer initialization with notifier callback."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            notifier = MagicMock()
            analyzer = GeminiAnalyzer(client=client, notifier_callback=notifier)
            assert analyzer.notifier_callback == notifier

    @patch("services.gemini.client.genai")
    def test_get_cache_key(self, mock_genai):
        """Test cache key generation."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            analyzer = GeminiAnalyzer(client=client)
            key1 = analyzer._get_cache_key("test message", "ru")
            key2 = analyzer._get_cache_key("test message", "kz")
            key3 = analyzer._get_cache_key("different message", "ru")
            
            assert isinstance(key1, str)
            assert key1 != key2  # Different language
            assert key1 != key3  # Different message
            assert "ru" in key1
            assert "kz" in key2

    @patch("services.gemini.client.genai")
    def test_cache_operations(self, mock_genai):
        """Test cache set and get operations."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            analyzer = GeminiAnalyzer(client=client)
            
            result = ClassificationResult(
                request_type=RequestType.APPOINTMENT_BOOKING,
                urgency=UrgencyLevel.HIGH,
            )
            key = "test_key"
            
            # Cache should be empty initially
            assert analyzer._get_from_cache(key) is None
            
            # Set in cache
            analyzer._set_cache(key, result)
            
            # Should retrieve from cache
            cached = analyzer._get_from_cache(key)
            assert cached == result

    @patch("services.gemini.client.genai")
    def test_clear_cache(self, mock_genai):
        """Test clearing classification cache."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            analyzer = GeminiAnalyzer(client=client)
            
            result = ClassificationResult(
                request_type=RequestType.GENERAL_INQUIRY,
                urgency=UrgencyLevel.LOW,
            )
            key = "test_key"
            analyzer._set_cache(key, result)
            
            # Clear cache
            analyzer.clear_cache()
            
            # Cache should be empty
            assert analyzer._get_from_cache(key) is None

    @patch("services.gemini.client.genai")
    def test_trigger_notifier(self, mock_genai):
        """Test notifier callback is triggered on error."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            notifier = MagicMock()
            analyzer = GeminiAnalyzer(client=client, notifier_callback=notifier)
            
            analyzer._trigger_notifier("Test error message")
            
            notifier.assert_called_once_with("gemini", "Test error message")

    @patch("services.gemini.client.genai")
    def test_trigger_notifier_without_callback(self, mock_genai):
        """Test analyzer works without notifier callback."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            analyzer = GeminiAnalyzer(client=client, notifier_callback=None)
            
            # Should not raise error
            analyzer._trigger_notifier("Test error")

    @patch("services.gemini.analyzer.genai")
    @patch.object(GeminiClient, "get_model")
    @patch.object(GeminiClient, "get_generation_config")
    @patch.object(GeminiClient, "get_safety_settings")
    @patch.object(GeminiClient, "get_request_timeout")
    def test_classify_request_success(
        self,
        mock_timeout,
        mock_safety,
        mock_config,
        mock_model,
        mock_genai,
    ):
        """Test successful request classification."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            analyzer = GeminiAnalyzer(client=client)
            
            mock_model.return_value = "gemini-pro"
            mock_config.return_value = {"temperature": 0.3}
            mock_safety.return_value = []
            mock_timeout.return_value = 30
            
            # Mock Gemini response
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "request_type": "appointment_booking",
                "urgency": "high",
                "specialist_suggestion": "Dentist",
                "confidence": 0.95,
                "reasoning": "User wants to book appointment",
            })
            
            mock_model_instance = MagicMock()
            mock_model_instance.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model_instance
            
            result = analyzer.classify_request("I want to book an appointment", "ru")
            
            assert result.request_type == RequestType.APPOINTMENT_BOOKING
            assert result.urgency == UrgencyLevel.HIGH
            assert result.specialist_suggestion == "Dentist"
            assert result.confidence == 0.95

    @patch("services.gemini.analyzer.genai")
    @patch.object(GeminiClient, "get_model")
    @patch.object(GeminiClient, "get_generation_config")
    @patch.object(GeminiClient, "get_safety_settings")
    @patch.object(GeminiClient, "get_request_timeout")
    def test_classify_request_cache_hit(
        self,
        mock_timeout,
        mock_safety,
        mock_config,
        mock_model,
        mock_genai,
    ):
        """Test classification uses cache on second call."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            analyzer = GeminiAnalyzer(client=client)
            
            mock_model.return_value = "gemini-pro"
            mock_config.return_value = {"temperature": 0.3}
            mock_safety.return_value = []
            mock_timeout.return_value = 30
            
            # Mock Gemini response
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "request_type": "appointment_booking",
                "urgency": "high",
                "confidence": 0.95,
            })
            
            mock_model_instance = MagicMock()
            mock_model_instance.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model_instance
            
            message = "I want to book an appointment"
            
            # First call
            result1 = analyzer.classify_request(message, "ru")
            
            # Second call should use cache
            result2 = analyzer.classify_request(message, "ru")
            
            # Only one API call should be made
            assert mock_model_instance.generate_content.call_count == 1
            assert result1.request_type == result2.request_type

    @patch("services.gemini.analyzer.genai")
    @patch.object(GeminiClient, "get_model")
    def test_classify_request_failure_fallback(self, mock_model, mock_genai):
        """Test classification falls back on API error."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            notifier = MagicMock()
            analyzer = GeminiAnalyzer(client=client, notifier_callback=notifier)
            
            mock_model.return_value = "gemini-pro"
            
            # Mock API error
            mock_model_instance = MagicMock()
            mock_model_instance.generate_content.side_effect = Exception("API timeout")
            mock_genai.GenerativeModel.return_value = mock_model_instance
            
            result = analyzer.classify_request("I want to book", "ru")
            
            # Should return fallback
            assert result.request_type == RequestType.GENERAL_INQUIRY
            assert result.confidence == 0.0
            
            # Notifier should be triggered
            notifier.assert_called_once()

    @patch("services.gemini.analyzer.genai")
    @patch.object(GeminiClient, "get_model")
    @patch.object(GeminiClient, "get_generation_config")
    @patch.object(GeminiClient, "get_safety_settings")
    @patch.object(GeminiClient, "get_request_timeout")
    def test_generate_response_success(
        self,
        mock_timeout,
        mock_safety,
        mock_config,
        mock_model,
        mock_genai,
    ):
        """Test successful response generation."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            analyzer = GeminiAnalyzer(client=client)
            
            mock_model.return_value = "gemini-pro"
            mock_config.return_value = {"temperature": 0.7}
            mock_safety.return_value = []
            mock_timeout.return_value = 30
            
            # Mock Gemini response
            mock_response = MagicMock()
            mock_response.text = "You can book an appointment by visiting our website."
            
            mock_model_instance = MagicMock()
            mock_model_instance.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model_instance
            
            result = analyzer.generate_response(
                "How do I book an appointment?",
                context={"clinic": "VITA"},
                language="ru",
            )
            
            assert result.text == "You can book an appointment by visiting our website."
            assert result.is_fallback is False
            assert result.error is None

    @patch("services.gemini.analyzer.genai")
    def test_generate_response_failure_fallback(self, mock_genai):
        """Test response generation falls back on API error."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            notifier = MagicMock()
            analyzer = GeminiAnalyzer(client=client, notifier_callback=notifier)
            
            # Mock API error
            mock_model_instance = MagicMock()
            mock_model_instance.generate_content.side_effect = Exception("API error")
            mock_genai.GenerativeModel.return_value = mock_model_instance
            
            result = analyzer.generate_response("Any message", language="ru")
            
            # Should return fallback
            assert result.is_fallback is True
            assert result.error is not None
            assert len(result.text) > 0

    @patch("services.gemini.analyzer.genai")
    @patch.object(GeminiClient, "get_model")
    @patch.object(GeminiClient, "get_generation_config")
    @patch.object(GeminiClient, "get_safety_settings")
    @patch.object(GeminiClient, "get_request_timeout")
    def test_summarize_complaint_success(
        self,
        mock_timeout,
        mock_safety,
        mock_config,
        mock_model,
        mock_genai,
    ):
        """Test successful complaint summarization."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            analyzer = GeminiAnalyzer(client=client)
            
            mock_model.return_value = "gemini-pro"
            mock_config.return_value = {"temperature": 0.5}
            mock_safety.return_value = []
            mock_timeout.return_value = 30
            
            # Mock Gemini response
            mock_response = MagicMock()
            mock_response.text = "Patient complained about long wait times."
            
            mock_model_instance = MagicMock()
            mock_model_instance.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model_instance
            
            long_text = "A very long complaint about wait times..." * 10
            result = analyzer.summarize_complaint(long_text, language="ru")
            
            assert result.text == "Patient complained about long wait times."
            assert result.is_fallback is False

    @patch("services.gemini.analyzer.genai")
    def test_summarize_complaint_failure_fallback(self, mock_genai):
        """Test complaint summarization falls back on API error."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            notifier = MagicMock()
            analyzer = GeminiAnalyzer(client=client, notifier_callback=notifier)
            
            # Mock API error
            mock_model_instance = MagicMock()
            mock_model_instance.generate_content.side_effect = Exception("API error")
            mock_genai.GenerativeModel.return_value = mock_model_instance
            
            result = analyzer.summarize_complaint("Long text...", language="ru")
            
            # Should return fallback
            assert result.is_fallback is True
            assert result.error is not None

    @patch.object(GeminiClient, "__init__", lambda x: None)
    def test_get_classification_prompt_russian(self):
        """Test classification prompt for Russian."""
        client = GeminiClient()
        analyzer = GeminiAnalyzer(client=client)
        prompt = analyzer._get_classification_prompt("ru")
        assert "request_type" in prompt
        assert "urgency" in prompt
        assert len(prompt) > 0

    @patch.object(GeminiClient, "__init__", lambda x: None)
    def test_get_classification_prompt_kazakh(self):
        """Test classification prompt for Kazakh."""
        client = GeminiClient()
        analyzer = GeminiAnalyzer(client=client)
        prompt = analyzer._get_classification_prompt("kz")
        assert "request_type" in prompt or len(prompt) > 0

    @patch.object(GeminiClient, "__init__", lambda x: None)
    def test_get_response_prompt(self):
        """Test response prompt generation."""
        client = GeminiClient()
        analyzer = GeminiAnalyzer(client=client)
        prompt = analyzer._get_response_prompt("ru", context=None)
        assert len(prompt) > 0

    @patch.object(GeminiClient, "__init__", lambda x: None)
    def test_get_summary_prompt(self):
        """Test summary prompt generation."""
        client = GeminiClient()
        analyzer = GeminiAnalyzer(client=client)
        prompt = analyzer._get_summary_prompt("ru")
        assert len(prompt) > 0

    @patch.object(GeminiClient, "__init__", lambda x: None)
    def test_parse_classification_response_valid_json(self):
        """Test parsing valid JSON classification response."""
        client = GeminiClient()
        analyzer = GeminiAnalyzer(client=client)
        
        response_text = json.dumps({
            "request_type": "appointment_booking",
            "urgency": "high",
            "specialist_suggestion": "Doctor",
            "confidence": 0.9,
            "reasoning": "Test",
        })
        
        result = analyzer._parse_classification_response(response_text, "ru")
        
        assert result.request_type == RequestType.APPOINTMENT_BOOKING
        assert result.urgency == UrgencyLevel.HIGH

    @patch.object(GeminiClient, "__init__", lambda x: None)
    def test_parse_classification_response_invalid_json(self):
        """Test parsing invalid JSON falls back gracefully."""
        client = GeminiClient()
        analyzer = GeminiAnalyzer(client=client)
        
        response_text = "This is not JSON"
        
        result = analyzer._parse_classification_response(response_text, "ru")
        
        assert result.request_type == RequestType.GENERAL_INQUIRY
        assert result.urgency == UrgencyLevel.MEDIUM

    @patch.object(GeminiClient, "__init__", lambda x: None)
    def test_parse_classification_response_wrapped_json(self):
        """Test parsing JSON wrapped in text."""
        client = GeminiClient()
        analyzer = GeminiAnalyzer(client=client)
        
        response_text = f"""Here is the classification:
        {json.dumps({
            "request_type": "complaint",
            "urgency": "medium",
            "confidence": 0.75,
        })}
        Done!"""
        
        result = analyzer._parse_classification_response(response_text, "ru")
        
        assert result.request_type == RequestType.COMPLAINT
        assert result.urgency == UrgencyLevel.MEDIUM
