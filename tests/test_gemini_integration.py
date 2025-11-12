"""Integration tests for Gemini service components."""

import pytest
from unittest.mock import MagicMock, patch
import json

from services.gemini import (
    GeminiClient,
    GeminiAnalyzer,
    RequestType,
    UrgencyLevel,
    ClassificationResult,
)
from exceptions import GeminiInitializationError, GeminiError


class TestGeminiIntegration:
    """Integration tests for complete Gemini service workflows."""

    @patch("services.gemini.client.genai")
    def test_analyzer_complete_workflow(self, mock_genai):
        """Test complete workflow: init -> classify -> response -> summary."""
        # Setup
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            client.get_model = MagicMock(return_value="gemini-pro")
            client.get_generation_config = MagicMock(return_value={})
            client.get_safety_settings = MagicMock(return_value=[])
            client.get_request_timeout = MagicMock(return_value=30)

            notifier = MagicMock()
            analyzer = GeminiAnalyzer(
                client=client,
                cache_ttl=3600,
                notifier_callback=notifier,
            )

            # Mock responses
            mock_response_classify = MagicMock()
            mock_response_classify.text = json.dumps({
                "request_type": "appointment_booking",
                "urgency": "high",
                "confidence": 0.95,
            })

            mock_response_generate = MagicMock()
            mock_response_generate.text = "You can book through our website."

            mock_response_summary = MagicMock()
            mock_response_summary.text = "Patient wants faster booking process."

            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            mock_model.generate_content.side_effect = [
                mock_response_classify,
                mock_response_generate,
                mock_response_summary,
            ]

            # Execute
            classification = analyzer.classify_request(
                "I want to book an appointment tomorrow", "ru"
            )
            response = analyzer.generate_response("How do I book?", language="ru")
            summary = analyzer.summarize_complaint(
                "The booking process is too complicated...", "ru"
            )

            # Assert
            assert classification.request_type == RequestType.APPOINTMENT_BOOKING
            assert classification.urgency == UrgencyLevel.HIGH
            assert response.text == "You can book through our website."
            assert response.is_fallback is False
            assert summary.text == "Patient wants faster booking process."
            assert summary.is_fallback is False

            # Notifier should not be called for successful operations
            notifier.assert_not_called()

    @patch("services.gemini.client.genai")
    def test_analyzer_handles_api_errors_gracefully(self, mock_genai):
        """Test analyzer handles API errors without crashing."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            client.get_model = MagicMock(return_value="gemini-pro")
            client.get_generation_config = MagicMock(return_value={})
            client.get_safety_settings = MagicMock(return_value=[])
            client.get_request_timeout = MagicMock(return_value=30)

            notifier = MagicMock()
            analyzer = GeminiAnalyzer(client=client, notifier_callback=notifier)

            # Mock API error
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            mock_model.generate_content.side_effect = Exception("API timeout")

            # All three operations should fail gracefully
            classification = analyzer.classify_request("test", "ru")
            assert classification.confidence == 0.0
            assert classification.request_type == RequestType.GENERAL_INQUIRY

            response = analyzer.generate_response("test", language="ru")
            assert response.is_fallback is True
            assert len(response.text) > 0

            summary = analyzer.summarize_complaint("test", "ru")
            assert summary.is_fallback is True
            assert len(summary.text) > 0

            # Notifier should be called 3 times
            assert notifier.call_count == 3

    @patch("services.gemini.client.genai")
    def test_caching_reduces_api_calls(self, mock_genai):
        """Test caching reduces API calls for duplicate messages."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            client.get_model = MagicMock(return_value="gemini-pro")
            client.get_generation_config = MagicMock(return_value={})
            client.get_safety_settings = MagicMock(return_value=[])
            client.get_request_timeout = MagicMock(return_value=30)

            analyzer = GeminiAnalyzer(client=client)

            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "request_type": "appointment_booking",
                "urgency": "medium",
                "confidence": 0.8,
            })

            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            mock_model.generate_content.return_value = mock_response

            message = "I want to book an appointment"

            # First call - API call made
            result1 = analyzer.classify_request(message, "ru")
            assert mock_model.generate_content.call_count == 1

            # Second call - should use cache, no additional API call
            result2 = analyzer.classify_request(message, "ru")
            assert mock_model.generate_content.call_count == 1

            # Results should be identical
            assert result1.request_type == result2.request_type
            assert result1.confidence == result2.confidence

            # Different language should trigger new API call
            result3 = analyzer.classify_request(message, "kz")
            assert mock_model.generate_content.call_count == 2

    @patch("services.gemini.client.genai")
    def test_multiple_languages_support(self, mock_genai):
        """Test analyzer supports both Russian and Kazakh."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            client.get_model = MagicMock(return_value="gemini-pro")
            client.get_generation_config = MagicMock(return_value={})
            client.get_safety_settings = MagicMock(return_value=[])
            client.get_request_timeout = MagicMock(return_value=30)

            analyzer = GeminiAnalyzer(client=client)

            # Setup responses
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "request_type": "appointment_booking",
                "urgency": "high",
                "confidence": 0.9,
            })

            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            mock_model.generate_content.return_value = mock_response

            # Test Russian
            result_ru = analyzer.classify_request("Хочу записаться", "ru")
            assert result_ru.request_type == RequestType.APPOINTMENT_BOOKING

            # Verify model was called for Russian
            mock_model.generate_content.assert_called()
            calls_before = mock_model.generate_content.call_count

            # Test Kazakh
            result_kz = analyzer.classify_request("Ішемін тіңшелік беру", "kz")
            assert result_kz.request_type == RequestType.APPOINTMENT_BOOKING

            # New API call should be made for different language
            assert mock_model.generate_content.call_count > calls_before

    @patch("services.gemini.client.genai")
    def test_context_injection_in_response(self, mock_genai):
        """Test context is properly injected into response generation."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            client.get_model = MagicMock(return_value="gemini-pro")
            client.get_generation_config = MagicMock(return_value={})
            client.get_safety_settings = MagicMock(return_value=[])
            client.get_request_timeout = MagicMock(return_value=30)

            analyzer = GeminiAnalyzer(client=client)

            mock_response = MagicMock()
            mock_response.text = "Your appointment is confirmed."

            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            mock_model.generate_content.return_value = mock_response

            context = {
                "clinic_name": "VITA",
                "available_specialists": ["Cardiologist", "Dermatologist"],
            }

            result = analyzer.generate_response(
                "Confirm my appointment", context=context, language="ru"
            )

            assert result.text == "Your appointment is confirmed."
            assert not result.is_fallback

            # Verify GenerativeModel was called with proper system instruction
            mock_genai.GenerativeModel.assert_called()
            call_kwargs = mock_genai.GenerativeModel.call_args[1]
            assert "system_instruction" in call_kwargs

    @patch("services.gemini.client.genai")
    def test_json_parsing_with_wrapped_response(self, mock_genai):
        """Test parsing JSON wrapped in explanatory text."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            client.get_model = MagicMock(return_value="gemini-pro")
            client.get_generation_config = MagicMock(return_value={})
            client.get_safety_settings = MagicMock(return_value=[])
            client.get_request_timeout = MagicMock(return_value=30)

            analyzer = GeminiAnalyzer(client=client)

            # Response with wrapped JSON
            mock_response = MagicMock()
            mock_response.text = f"""Based on the message, here's the analysis:

{json.dumps({
    "request_type": "complaint",
    "urgency": "high",
    "confidence": 0.85,
})}

The user seems dissatisfied with the service."""

            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            mock_model.generate_content.return_value = mock_response

            result = analyzer.classify_request("I'm unhappy with the wait time", "ru")

            assert result.request_type == RequestType.COMPLAINT
            assert result.urgency == UrgencyLevel.HIGH
            assert result.confidence == 0.85

    def test_cache_expiration(self):
        """Test cache entries expire after TTL."""
        with patch.object(GeminiClient, "__init__", lambda x: None):
            client = GeminiClient()
            analyzer = GeminiAnalyzer(client=client, cache_ttl=1)

            result = ClassificationResult(
                request_type=RequestType.GENERAL_INQUIRY,
                urgency=UrgencyLevel.LOW,
            )
            key = "test_key"

            # Store in cache
            analyzer._set_cache(key, result)
            assert analyzer._get_from_cache(key) is not None

            # Simulate expiration
            import time
            time.sleep(1.1)

            # Should be expired
            assert analyzer._get_from_cache(key) is None
