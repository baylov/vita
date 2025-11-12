"""Tests for audio transcriber module."""

import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

import pytest

from services.audio.transcriber import SpeechTranscriber, transcribe_audio
from exceptions import TranscriptionError


@pytest.fixture
def mock_speech_client():
    """Mock Google Cloud Speech client."""
    with patch("services.audio.transcriber.speech_v1") as mock_speech:
        # Create mock client
        mock_client = MagicMock()
        
        # Mock recognition response
        mock_result = MagicMock()
        mock_alternative = MagicMock()
        mock_alternative.transcript = "Тестовый текст"
        mock_alternative.confidence = 0.95
        mock_result.alternatives = [mock_alternative]
        
        mock_response = MagicMock()
        mock_response.results = [mock_result]
        
        # Configure recognize method
        mock_client.recognize.return_value = mock_response
        
        # Configure long_running_recognize
        mock_operation = MagicMock()
        mock_operation.result.return_value = mock_response
        mock_client.long_running_recognize.return_value = mock_operation
        
        # Configure SpeechClient constructor
        mock_speech.SpeechClient.return_value = mock_client
        
        # Mock config classes
        mock_speech.RecognitionConfig = MagicMock()
        mock_speech.RecognitionAudio = MagicMock()
        
        yield mock_speech


@pytest.fixture
def temp_wav_file():
    """Create temporary WAV file for testing."""
    fd, path = tempfile.mkstemp(suffix=".wav")
    # Write minimal WAV header + data
    os.write(fd, b"RIFF" + b"\x00" * 36 + b"data" + b"\x00" * 100)
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


class TestSpeechTranscriber:
    """Test SpeechTranscriber class."""

    def test_initialization_success(self, mock_speech_client):
        """Test successful initialization."""
        transcriber = SpeechTranscriber()
        assert transcriber is not None
        assert transcriber.timeout > 0

    def test_initialization_without_library(self):
        """Test initialization fails without google-cloud-speech."""
        with patch("services.audio.transcriber.speech_v1", None):
            with pytest.raises(TranscriptionError) as exc_info:
                SpeechTranscriber()
            assert "google-cloud-speech library required" in str(exc_info.value)

    def test_initialization_custom_timeout(self, mock_speech_client):
        """Test initialization with custom timeout."""
        transcriber = SpeechTranscriber(timeout=120)
        assert transcriber.timeout == 120

    def test_initialization_custom_credentials(self, mock_speech_client):
        """Test initialization with custom credentials path."""
        transcriber = SpeechTranscriber(credentials_path="/custom/path.json")
        assert transcriber.credentials_path == "/custom/path.json"

    def test_transcribe_success_russian(self, mock_speech_client, temp_wav_file):
        """Test successful transcription in Russian."""
        transcriber = SpeechTranscriber()
        result = transcriber.transcribe(temp_wav_file, language="ru")
        
        assert result is not None
        assert result == "Тестовый текст"

    def test_transcribe_success_kazakh(self, mock_speech_client, temp_wav_file):
        """Test successful transcription in Kazakh."""
        transcriber = SpeechTranscriber()
        result = transcriber.transcribe(temp_wav_file, language="kz")
        
        assert result is not None
        assert result == "Тестовый текст"

    def test_transcribe_file_not_found(self, mock_speech_client):
        """Test transcription with non-existent file."""
        transcriber = SpeechTranscriber()
        result = transcriber.transcribe("/nonexistent/file.wav", language="ru")
        
        assert result is None

    def test_transcribe_small_file_sync(self, mock_speech_client, temp_wav_file):
        """Test transcription uses sync method for small files."""
        transcriber = SpeechTranscriber()
        result = transcriber.transcribe(temp_wav_file, language="ru")
        
        assert result is not None
        
        # Verify sync method was used
        client = mock_speech_client.SpeechClient.return_value
        assert client.recognize.called
        assert not client.long_running_recognize.called

    def test_transcribe_large_file_async(self, mock_speech_client):
        """Test transcription uses async method for large files."""
        # Create large temporary file
        fd, path = tempfile.mkstemp(suffix=".wav")
        # Write > 10MB
        os.write(fd, b"\x00" * (11 * 1024 * 1024))
        os.close(fd)
        
        try:
            transcriber = SpeechTranscriber()
            result = transcriber.transcribe(path, language="ru")
            
            assert result is not None
            
            # Verify async method was used
            client = mock_speech_client.SpeechClient.return_value
            assert client.long_running_recognize.called
        finally:
            os.remove(path)

    def test_transcribe_no_results(self, mock_speech_client, temp_wav_file):
        """Test transcription with no results."""
        # Configure empty response
        mock_response = MagicMock()
        mock_response.results = []
        
        client = mock_speech_client.SpeechClient.return_value
        client.recognize.return_value = mock_response
        
        transcriber = SpeechTranscriber()
        result = transcriber.transcribe(temp_wav_file, language="ru")
        
        assert result is None

    def test_transcribe_no_alternatives(self, mock_speech_client, temp_wav_file):
        """Test transcription with no alternatives."""
        # Configure response with no alternatives
        mock_result = MagicMock()
        mock_result.alternatives = []
        
        mock_response = MagicMock()
        mock_response.results = [mock_result]
        
        client = mock_speech_client.SpeechClient.return_value
        client.recognize.return_value = mock_response
        
        transcriber = SpeechTranscriber()
        result = transcriber.transcribe(temp_wav_file, language="ru")
        
        assert result is None

    def test_transcribe_multiple_results(self, mock_speech_client, temp_wav_file):
        """Test transcription with multiple results."""
        # Configure multiple results
        mock_result1 = MagicMock()
        mock_alternative1 = MagicMock()
        mock_alternative1.transcript = "Первая часть"
        mock_alternative1.confidence = 0.95
        mock_result1.alternatives = [mock_alternative1]
        
        mock_result2 = MagicMock()
        mock_alternative2 = MagicMock()
        mock_alternative2.transcript = "вторая часть"
        mock_alternative2.confidence = 0.90
        mock_result2.alternatives = [mock_alternative2]
        
        mock_response = MagicMock()
        mock_response.results = [mock_result1, mock_result2]
        
        client = mock_speech_client.SpeechClient.return_value
        client.recognize.return_value = mock_response
        
        transcriber = SpeechTranscriber()
        result = transcriber.transcribe(temp_wav_file, language="ru")
        
        assert result == "Первая часть вторая часть"

    def test_transcribe_api_error(self, mock_speech_client, temp_wav_file):
        """Test transcription with API error."""
        client = mock_speech_client.SpeechClient.return_value
        client.recognize.side_effect = Exception("API Error")
        
        transcriber = SpeechTranscriber()
        result = transcriber.transcribe(temp_wav_file, language="ru")
        
        assert result is None

    def test_transcribe_client_init_failure(self, mock_speech_client, temp_wav_file):
        """Test transcription when client initialization fails."""
        mock_speech_client.SpeechClient.side_effect = Exception("Init error")
        
        transcriber = SpeechTranscriber()
        result = transcriber.transcribe(temp_wav_file, language="ru")
        
        assert result is None

    def test_transcribe_with_punctuation_enabled(self, mock_speech_client, temp_wav_file):
        """Test transcription with punctuation enabled."""
        transcriber = SpeechTranscriber()
        result = transcriber.transcribe(
            temp_wav_file,
            language="ru",
            enable_automatic_punctuation=True,
        )
        
        assert result is not None

    def test_transcribe_with_punctuation_disabled(self, mock_speech_client, temp_wav_file):
        """Test transcription with punctuation disabled."""
        transcriber = SpeechTranscriber()
        result = transcriber.transcribe(
            temp_wav_file,
            language="ru",
            enable_automatic_punctuation=False,
        )
        
        assert result is not None

    def test_language_mapping_russian(self, mock_speech_client):
        """Test language code mapping for Russian."""
        transcriber = SpeechTranscriber()
        mapped = transcriber._map_language_code("ru")
        assert mapped == "ru-RU"

    def test_language_mapping_kazakh_kz(self, mock_speech_client):
        """Test language code mapping for Kazakh (kz)."""
        transcriber = SpeechTranscriber()
        mapped = transcriber._map_language_code("kz")
        assert mapped == "ru-KZ"

    def test_language_mapping_kazakh_kk(self, mock_speech_client):
        """Test language code mapping for Kazakh (kk)."""
        transcriber = SpeechTranscriber()
        mapped = transcriber._map_language_code("kk")
        assert mapped == "ru-KZ"

    def test_language_mapping_default(self, mock_speech_client):
        """Test language code mapping defaults to ru-RU."""
        transcriber = SpeechTranscriber()
        mapped = transcriber._map_language_code("unknown")
        assert mapped == "ru-RU"

    def test_language_mapping_case_insensitive(self, mock_speech_client):
        """Test language mapping is case insensitive."""
        transcriber = SpeechTranscriber()
        assert transcriber._map_language_code("RU") == "ru-RU"
        assert transcriber._map_language_code("KZ") == "ru-KZ"

    def test_extract_transcript_empty_results(self, mock_speech_client):
        """Test transcript extraction with empty results."""
        transcriber = SpeechTranscriber()
        
        mock_response = MagicMock()
        mock_response.results = []
        
        result = transcriber._extract_transcript(mock_response)
        assert result is None

    def test_extract_transcript_whitespace_only(self, mock_speech_client):
        """Test transcript extraction with whitespace only."""
        transcriber = SpeechTranscriber()
        
        mock_result = MagicMock()
        mock_alternative = MagicMock()
        mock_alternative.transcript = "   "
        mock_alternative.confidence = 0.5  # Add confidence as a float
        mock_result.alternatives = [mock_alternative]
        
        mock_response = MagicMock()
        mock_response.results = [mock_result]
        
        result = transcriber._extract_transcript(mock_response)
        assert result is None

    def test_async_transcription_timeout(self, mock_speech_client):
        """Test async transcription with timeout."""
        # Create large file
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.write(fd, b"\x00" * (11 * 1024 * 1024))
        os.close(fd)
        
        try:
            # Mock operation result to raise timeout
            mock_operation = MagicMock()
            mock_operation.result.side_effect = Exception("Timeout")
            
            client = mock_speech_client.SpeechClient.return_value
            client.long_running_recognize.return_value = mock_operation
            
            transcriber = SpeechTranscriber(timeout=5)
            result = transcriber.transcribe(path, language="ru")
            
            assert result is None
        finally:
            os.remove(path)

    def test_convenience_function_success(self, mock_speech_client, temp_wav_file):
        """Test convenience function for successful transcription."""
        result = transcribe_audio(temp_wav_file, language="ru")
        
        assert result is not None
        assert result == "Тестовый текст"

    def test_convenience_function_failure(self, mock_speech_client):
        """Test convenience function with failure."""
        result = transcribe_audio("/nonexistent/file.wav", language="ru")
        
        assert result is None

    def test_convenience_function_without_library(self):
        """Test convenience function without google-cloud-speech."""
        with patch("services.audio.transcriber.speech_v1", None):
            result = transcribe_audio("file.wav", language="ru")
            assert result is None

    def test_convenience_function_custom_credentials(self, mock_speech_client, temp_wav_file):
        """Test convenience function with custom credentials."""
        result = transcribe_audio(
            temp_wav_file,
            language="kz",
            credentials_path="/custom/path.json",
        )
        
        assert result is not None
