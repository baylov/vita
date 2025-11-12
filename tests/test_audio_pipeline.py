"""Tests for complete audio pipeline."""

import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

import pytest

from services.audio.pipeline import AudioPipeline
from exceptions import AudioConversionError, TranscriptionError


@pytest.fixture
def mock_converter():
    """Mock AudioConverter."""
    mock = MagicMock()
    mock.convert_audio.return_value = "/tmp/converted.wav"
    mock.cleanup_temp_file.return_value = None
    return mock


@pytest.fixture
def mock_transcriber():
    """Mock SpeechTranscriber."""
    mock = MagicMock()
    mock.transcribe.return_value = "Распознанный текст"
    return mock


@pytest.fixture
def mock_error_logger():
    """Mock error logger function."""
    return Mock()


@pytest.fixture
def temp_audio_file():
    """Create temporary audio file for testing."""
    fd, path = tempfile.mkstemp(suffix=".oga")
    os.write(fd, b"fake audio data")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


class TestAudioPipeline:
    """Test AudioPipeline class."""

    def test_initialization_success(self, mock_converter, mock_transcriber):
        """Test successful initialization."""
        pipeline = AudioPipeline(
            converter=mock_converter,
            transcriber=mock_transcriber,
        )
        
        assert pipeline.converter is not None
        assert pipeline.transcriber is not None

    def test_initialization_with_error_logger(
        self, mock_converter, mock_transcriber, mock_error_logger
    ):
        """Test initialization with error logger."""
        pipeline = AudioPipeline(
            error_logger=mock_error_logger,
            converter=mock_converter,
            transcriber=mock_transcriber,
        )
        
        assert pipeline.error_logger == mock_error_logger

    def test_initialization_converter_failure(self, mock_transcriber, mock_error_logger):
        """Test initialization when converter fails."""
        with patch("services.audio.pipeline.AudioConverter") as mock_conv_class:
            mock_conv_class.side_effect = AudioConversionError("Init failed")
            
            pipeline = AudioPipeline(
                error_logger=mock_error_logger,
                transcriber=mock_transcriber,
            )
            
            assert pipeline.converter is None
            assert pipeline.transcriber is not None
            assert mock_error_logger.called

    def test_initialization_transcriber_failure(self, mock_converter, mock_error_logger):
        """Test initialization when transcriber fails."""
        with patch("services.audio.pipeline.SpeechTranscriber") as mock_trans_class:
            mock_trans_class.side_effect = TranscriptionError("Init failed")
            
            pipeline = AudioPipeline(
                error_logger=mock_error_logger,
                converter=mock_converter,
            )
            
            assert pipeline.converter is not None
            assert pipeline.transcriber is None
            assert mock_error_logger.called

    def test_process_voice_message_success(
        self, mock_converter, mock_transcriber, temp_audio_file
    ):
        """Test successful voice message processing."""
        pipeline = AudioPipeline(
            converter=mock_converter,
            transcriber=mock_transcriber,
        )
        
        result = pipeline.process_voice_message(temp_audio_file, language="ru")
        
        assert result == "Распознанный текст"
        assert mock_converter.convert_audio.called
        assert mock_transcriber.transcribe.called
        assert mock_converter.cleanup_temp_file.called

    def test_process_voice_message_kazakh(
        self, mock_converter, mock_transcriber, temp_audio_file
    ):
        """Test voice message processing in Kazakh."""
        pipeline = AudioPipeline(
            converter=mock_converter,
            transcriber=mock_transcriber,
        )
        
        result = pipeline.process_voice_message(temp_audio_file, language="kz")
        
        assert result == "Распознанный текст"
        
        # Verify language was passed correctly
        call_args = mock_transcriber.transcribe.call_args
        assert call_args[1]["language"] == "kz"

    def test_process_voice_message_no_cleanup(
        self, mock_converter, mock_transcriber, temp_audio_file
    ):
        """Test voice message processing without cleanup."""
        pipeline = AudioPipeline(
            converter=mock_converter,
            transcriber=mock_transcriber,
        )
        
        result = pipeline.process_voice_message(
            temp_audio_file,
            language="ru",
            cleanup=False,
        )
        
        assert result == "Распознанный текст"
        assert not mock_converter.cleanup_temp_file.called

    def test_process_voice_message_converter_unavailable(
        self, mock_transcriber, temp_audio_file, mock_error_logger
    ):
        """Test processing when converter is unavailable."""
        pipeline = AudioPipeline(
            converter=None,
            transcriber=mock_transcriber,
            error_logger=mock_error_logger,
            auto_init=False,
        )
        
        result = pipeline.process_voice_message(temp_audio_file, language="ru")
        
        assert result is None
        assert mock_error_logger.called
        assert not mock_transcriber.transcribe.called

    def test_process_voice_message_transcriber_unavailable(
        self, mock_converter, temp_audio_file, mock_error_logger
    ):
        """Test processing when transcriber is unavailable."""
        pipeline = AudioPipeline(
            converter=mock_converter,
            transcriber=None,
            error_logger=mock_error_logger,
            auto_init=False,
        )
        
        result = pipeline.process_voice_message(temp_audio_file, language="ru")
        
        assert result is None
        assert mock_error_logger.called
        assert not mock_converter.convert_audio.called

    def test_process_voice_message_conversion_failure(
        self, mock_converter, mock_transcriber, temp_audio_file, mock_error_logger
    ):
        """Test processing when conversion fails."""
        mock_converter.convert_audio.return_value = None
        
        pipeline = AudioPipeline(
            converter=mock_converter,
            transcriber=mock_transcriber,
            error_logger=mock_error_logger,
        )
        
        result = pipeline.process_voice_message(temp_audio_file, language="ru")
        
        assert result is None
        assert mock_error_logger.called
        assert not mock_transcriber.transcribe.called
        assert not mock_converter.cleanup_temp_file.called

    def test_process_voice_message_transcription_failure(
        self, mock_converter, mock_transcriber, temp_audio_file, mock_error_logger
    ):
        """Test processing when transcription fails."""
        mock_transcriber.transcribe.return_value = None
        
        pipeline = AudioPipeline(
            converter=mock_converter,
            transcriber=mock_transcriber,
            error_logger=mock_error_logger,
        )
        
        result = pipeline.process_voice_message(temp_audio_file, language="ru")
        
        assert result is None
        assert mock_error_logger.called
        assert mock_converter.cleanup_temp_file.called

    def test_process_voice_message_unexpected_error(
        self, mock_converter, mock_transcriber, temp_audio_file, mock_error_logger
    ):
        """Test processing with unexpected error."""
        mock_converter.convert_audio.side_effect = Exception("Unexpected error")
        
        pipeline = AudioPipeline(
            converter=mock_converter,
            transcriber=mock_transcriber,
            error_logger=mock_error_logger,
        )
        
        result = pipeline.process_voice_message(temp_audio_file, language="ru")
        
        assert result is None
        assert mock_error_logger.called

    def test_process_voice_message_cleanup_on_error(
        self, mock_converter, mock_transcriber, temp_audio_file
    ):
        """Test cleanup happens even on transcription error."""
        mock_transcriber.transcribe.return_value = None
        
        pipeline = AudioPipeline(
            converter=mock_converter,
            transcriber=mock_transcriber,
        )
        
        result = pipeline.process_voice_message(temp_audio_file, language="ru")
        
        assert result is None
        assert mock_converter.cleanup_temp_file.called

    def test_is_available_both_ready(self, mock_converter, mock_transcriber):
        """Test is_available when both components are ready."""
        pipeline = AudioPipeline(
            converter=mock_converter,
            transcriber=mock_transcriber,
        )
        
        assert pipeline.is_available() is True

    def test_is_available_converter_missing(self, mock_transcriber):
        """Test is_available when converter is missing."""
        pipeline = AudioPipeline(
            converter=None,
            transcriber=mock_transcriber,
            auto_init=False,
        )
        
        assert pipeline.is_available() is False

    def test_is_available_transcriber_missing(self, mock_converter):
        """Test is_available when transcriber is missing."""
        pipeline = AudioPipeline(
            converter=mock_converter,
            transcriber=None,
            auto_init=False,
        )
        
        assert pipeline.is_available() is False

    def test_is_available_both_missing(self):
        """Test is_available when both components are missing."""
        pipeline = AudioPipeline(
            converter=None,
            transcriber=None,
            auto_init=False,
        )
        
        assert pipeline.is_available() is False

    def test_error_logger_called_with_correct_args(
        self, mock_converter, mock_transcriber, temp_audio_file, mock_error_logger
    ):
        """Test error logger is called with correct arguments."""
        mock_converter.convert_audio.return_value = None
        
        pipeline = AudioPipeline(
            converter=mock_converter,
            transcriber=mock_transcriber,
            error_logger=mock_error_logger,
        )
        
        pipeline.process_voice_message(temp_audio_file, language="ru")
        
        # Verify error logger was called
        assert mock_error_logger.called
        call_args = mock_error_logger.call_args[0]
        
        # Check arguments
        assert call_args[0] == "audio_conversion_error"  # error_type
        assert isinstance(call_args[1], str)  # message
        assert temp_audio_file in call_args[2]  # context

    def test_error_logger_failure_handled(
        self, mock_converter, mock_transcriber, temp_audio_file
    ):
        """Test that error logger failures don't break pipeline."""
        # Create error logger that raises exception
        error_logger = Mock(side_effect=Exception("Logger error"))
        
        mock_converter.convert_audio.return_value = None
        
        pipeline = AudioPipeline(
            converter=mock_converter,
            transcriber=mock_transcriber,
            error_logger=error_logger,
        )
        
        # Should not raise exception even though logger fails
        result = pipeline.process_voice_message(temp_audio_file, language="ru")
        
        assert result is None

    def test_cleanup_not_called_on_conversion_failure(
        self, mock_converter, mock_transcriber, temp_audio_file
    ):
        """Test cleanup is not called when conversion fails (no file to clean)."""
        mock_converter.convert_audio.return_value = None
        
        pipeline = AudioPipeline(
            converter=mock_converter,
            transcriber=mock_transcriber,
        )
        
        pipeline.process_voice_message(temp_audio_file, language="ru")
        
        # cleanup_temp_file should not be called because converted_path is None
        assert not mock_converter.cleanup_temp_file.called

    def test_multiple_languages_supported(
        self, mock_converter, mock_transcriber, temp_audio_file
    ):
        """Test pipeline supports multiple languages."""
        pipeline = AudioPipeline(
            converter=mock_converter,
            transcriber=mock_transcriber,
        )
        
        # Test Russian
        result_ru = pipeline.process_voice_message(temp_audio_file, language="ru")
        assert result_ru == "Распознанный текст"
        
        # Test Kazakh
        result_kz = pipeline.process_voice_message(temp_audio_file, language="kz")
        assert result_kz == "Распознанный текст"
