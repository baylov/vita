"""Tests for audio converter module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from services.audio.converter import AudioConverter, convert_audio
from exceptions import AudioConversionError


@pytest.fixture
def mock_audio_segment():
    """Mock AudioSegment for testing."""
    with patch("services.audio.converter.AudioSegment") as mock:
        # Create mock audio instance
        mock_audio = MagicMock()
        mock_audio.duration_seconds = 5.0
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        mock_audio.export.return_value = None
        
        # Configure from_file to return mock audio
        mock.from_file.return_value = mock_audio
        
        yield mock


@pytest.fixture
def temp_audio_file():
    """Create temporary audio file for testing."""
    fd, path = tempfile.mkstemp(suffix=".oga")
    os.write(fd, b"fake audio data")
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


class TestAudioConverter:
    """Test AudioConverter class."""

    def test_initialization_success(self, mock_audio_segment):
        """Test successful initialization."""
        converter = AudioConverter()
        assert converter is not None
        assert converter.OUTPUT_FORMAT == "wav"
        assert converter.OUTPUT_SAMPLE_RATE == 16000
        assert converter.OUTPUT_CHANNELS == 1

    def test_initialization_without_pydub(self):
        """Test initialization fails without pydub."""
        with patch("services.audio.converter.AudioSegment", None):
            with pytest.raises(AudioConversionError) as exc_info:
                AudioConverter()
            assert "pydub library required" in str(exc_info.value)

    def test_convert_audio_success(self, mock_audio_segment, temp_audio_file):
        """Test successful audio conversion."""
        converter = AudioConverter()
        result = converter.convert_audio(temp_audio_file)
        
        assert result is not None
        assert isinstance(result, str)
        assert result.endswith(".wav")
        assert os.path.exists(result)
        
        # Cleanup
        if result:
            os.remove(result)

    def test_convert_audio_file_not_found(self, mock_audio_segment):
        """Test conversion with non-existent file."""
        converter = AudioConverter()
        result = converter.convert_audio("/nonexistent/file.oga")
        
        assert result is None

    def test_convert_audio_unsupported_format(self, mock_audio_segment):
        """Test conversion with unsupported format."""
        # Create temp file with unsupported extension
        fd, path = tempfile.mkstemp(suffix=".xyz")
        os.write(fd, b"data")
        os.close(fd)
        
        try:
            converter = AudioConverter()
            result = converter.convert_audio(path)
            assert result is None
        finally:
            os.remove(path)

    def test_convert_audio_ogg_format(self, mock_audio_segment, temp_audio_file):
        """Test conversion of .ogg file."""
        # Rename to .ogg
        ogg_path = temp_audio_file.replace(".oga", ".ogg")
        os.rename(temp_audio_file, ogg_path)
        
        try:
            converter = AudioConverter()
            result = converter.convert_audio(ogg_path)
            assert result is not None
            
            # Cleanup
            if result:
                os.remove(result)
        finally:
            if os.path.exists(ogg_path):
                os.rename(ogg_path, temp_audio_file)

    def test_convert_audio_m4a_format(self, mock_audio_segment):
        """Test conversion of .m4a file."""
        fd, path = tempfile.mkstemp(suffix=".m4a")
        os.write(fd, b"fake m4a data")
        os.close(fd)
        
        try:
            converter = AudioConverter()
            result = converter.convert_audio(path)
            assert result is not None
            
            # Cleanup
            if result:
                os.remove(result)
        finally:
            os.remove(path)

    def test_convert_audio_load_failure(self, mock_audio_segment, temp_audio_file):
        """Test conversion when audio loading fails."""
        mock_audio_segment.from_file.side_effect = Exception("Load error")
        
        converter = AudioConverter()
        result = converter.convert_audio(temp_audio_file)
        
        assert result is None

    def test_convert_audio_too_short(self, mock_audio_segment, temp_audio_file):
        """Test conversion with audio too short."""
        mock_audio = mock_audio_segment.from_file.return_value
        mock_audio.duration_seconds = 0.05  # Less than 0.1s
        
        converter = AudioConverter()
        result = converter.convert_audio(temp_audio_file)
        
        assert result is None

    def test_convert_audio_very_long(self, mock_audio_segment, temp_audio_file):
        """Test conversion with very long audio (should warn but succeed)."""
        mock_audio = mock_audio_segment.from_file.return_value
        mock_audio.duration_seconds = 700  # > 10 minutes
        
        converter = AudioConverter()
        result = converter.convert_audio(temp_audio_file)
        
        # Should still succeed, just log warning
        assert result is not None
        
        # Cleanup
        if result:
            os.remove(result)

    def test_convert_audio_export_failure(self, mock_audio_segment, temp_audio_file):
        """Test conversion when export fails."""
        mock_audio = mock_audio_segment.from_file.return_value
        mock_audio.export.side_effect = Exception("Export error")
        
        converter = AudioConverter()
        result = converter.convert_audio(temp_audio_file)
        
        assert result is None

    def test_cleanup_temp_file_success(self):
        """Test successful temp file cleanup."""
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        
        assert os.path.exists(path)
        AudioConverter.cleanup_temp_file(path)
        assert not os.path.exists(path)

    def test_cleanup_temp_file_not_exists(self):
        """Test cleanup of non-existent file (should not raise)."""
        AudioConverter.cleanup_temp_file("/nonexistent/file.wav")
        # Should complete without error

    def test_cleanup_temp_file_none(self):
        """Test cleanup with None path (should not raise)."""
        AudioConverter.cleanup_temp_file(None)
        # Should complete without error

    def test_is_format_supported(self, mock_audio_segment):
        """Test format support checking."""
        converter = AudioConverter()
        
        assert converter.is_format_supported("file.oga") is True
        assert converter.is_format_supported("file.ogg") is True
        assert converter.is_format_supported("file.m4a") is True
        assert converter.is_format_supported("file.mp3") is True
        assert converter.is_format_supported("file.wav") is True
        assert converter.is_format_supported("file.xyz") is False
        assert converter.is_format_supported("file.txt") is False

    def test_is_format_supported_case_insensitive(self, mock_audio_segment):
        """Test format checking is case insensitive."""
        converter = AudioConverter()
        
        assert converter.is_format_supported("FILE.OGA") is True
        assert converter.is_format_supported("FILE.M4A") is True

    def test_convenience_function_success(self, mock_audio_segment, temp_audio_file):
        """Test convenience function for successful conversion."""
        result = convert_audio(temp_audio_file)
        
        assert result is not None
        
        # Cleanup
        if result:
            os.remove(result)

    def test_convenience_function_failure(self, mock_audio_segment):
        """Test convenience function with failure."""
        result = convert_audio("/nonexistent/file.oga")
        
        assert result is None

    def test_convenience_function_without_pydub(self):
        """Test convenience function without pydub."""
        with patch("services.audio.converter.AudioSegment", None):
            result = convert_audio("file.oga")
            assert result is None

    def test_supported_formats_constant(self, mock_audio_segment):
        """Test SUPPORTED_FORMATS constant."""
        converter = AudioConverter()
        
        assert ".oga" in converter.SUPPORTED_FORMATS
        assert ".ogg" in converter.SUPPORTED_FORMATS
        assert ".m4a" in converter.SUPPORTED_FORMATS
        assert ".mp3" in converter.SUPPORTED_FORMATS
        assert ".wav" in converter.SUPPORTED_FORMATS

    def test_output_specs_constants(self, mock_audio_segment):
        """Test output specification constants."""
        converter = AudioConverter()
        
        assert converter.OUTPUT_FORMAT == "wav"
        assert converter.OUTPUT_SAMPLE_RATE == 16000
        assert converter.OUTPUT_CHANNELS == 1
        assert converter.OUTPUT_SAMPLE_WIDTH == 2
