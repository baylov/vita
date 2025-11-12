"""Audio format conversion for voice message preprocessing."""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

from exceptions import AudioConversionError

logger = logging.getLogger(__name__)


class AudioConverter:
    """Converts audio files to PCM WAV format for speech recognition."""

    # Supported input formats
    SUPPORTED_FORMATS = {".oga", ".ogg", ".m4a", ".mp3", ".wav"}

    # Output format specifications
    OUTPUT_FORMAT = "wav"
    OUTPUT_SAMPLE_RATE = 16000  # 16kHz optimal for speech recognition
    OUTPUT_CHANNELS = 1  # Mono
    OUTPUT_SAMPLE_WIDTH = 2  # 16-bit

    def __init__(self):
        """Initialize the audio converter."""
        if AudioSegment is None:
            logger.error("pydub library not installed. Audio conversion unavailable.")
            raise AudioConversionError(
                "pydub library required for audio conversion. Install with: pip install pydub"
            )

    def convert_audio(self, input_path: str) -> Optional[str]:
        """
        Convert audio file to PCM WAV format.

        Converts Telegram .oga/.ogg and WhatsApp .m4a files into PCM WAV
        format optimized for speech recognition (16kHz, mono, 16-bit).

        Args:
            input_path: Path to the input audio file

        Returns:
            Path to converted WAV file, or None if conversion fails

        Raises:
            AudioConversionError: If input file is invalid or conversion fails critically
        """
        try:
            input_file = Path(input_path)

            # Validate input file exists
            if not input_file.exists():
                logger.error(f"Input file does not exist: {input_path}")
                return None

            # Check file extension
            file_ext = input_file.suffix.lower()
            if file_ext not in self.SUPPORTED_FORMATS:
                logger.error(
                    f"Unsupported audio format: {file_ext}. "
                    f"Supported: {', '.join(self.SUPPORTED_FORMATS)}"
                )
                return None

            logger.info(f"Converting audio file: {input_path} ({file_ext})")

            # Load audio file
            audio = self._load_audio(input_path, file_ext)
            if audio is None:
                return None

            # Convert to target format
            audio = audio.set_frame_rate(self.OUTPUT_SAMPLE_RATE)
            audio = audio.set_channels(self.OUTPUT_CHANNELS)
            audio = audio.set_sample_width(self.OUTPUT_SAMPLE_WIDTH)

            # Create temporary output file
            output_file = self._create_temp_output_file()
            if output_file is None:
                return None

            # Export to WAV
            audio.export(
                output_file,
                format=self.OUTPUT_FORMAT,
                parameters=["-acodec", "pcm_s16le"],
            )

            # Get canonical path
            canonical_path = str(Path(output_file).resolve())
            logger.info(
                f"Audio conversion successful: {canonical_path} "
                f"({audio.duration_seconds:.2f}s, {self.OUTPUT_SAMPLE_RATE}Hz)"
            )

            return canonical_path

        except AudioConversionError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during audio conversion: {e}", exc_info=True)
            return None

    def _load_audio(self, input_path: str, file_ext: str) -> Optional[AudioSegment]:
        """
        Load audio file using pydub.

        Args:
            input_path: Path to audio file
            file_ext: File extension (with dot)

        Returns:
            AudioSegment object or None on failure
        """
        try:
            # Map file extension to pydub format
            format_map = {
                ".oga": "ogg",
                ".ogg": "ogg",
                ".m4a": "m4a",
                ".mp3": "mp3",
                ".wav": "wav",
            }

            format_name = format_map.get(file_ext, file_ext[1:])

            # Load audio with appropriate codec
            audio = AudioSegment.from_file(input_path, format=format_name)

            # Validate audio properties
            if audio.duration_seconds < 0.1:
                logger.error("Audio file too short (< 0.1s)")
                return None

            if audio.duration_seconds > 600:  # 10 minutes
                logger.warning(
                    f"Audio file very long ({audio.duration_seconds:.1f}s). "
                    "Processing may take time."
                )

            return audio

        except Exception as e:
            logger.error(f"Failed to load audio file {input_path}: {e}")
            return None

    def _create_temp_output_file(self) -> Optional[str]:
        """
        Create a temporary file for output WAV.

        Returns:
            Path to temporary file or None on failure
        """
        try:
            # Create temp file with .wav extension
            temp_fd, temp_path = tempfile.mkstemp(
                suffix=".wav", prefix="audio_conv_", dir=None
            )

            # Close file descriptor (we only need the path)
            os.close(temp_fd)

            logger.debug(f"Created temporary output file: {temp_path}")
            return temp_path

        except Exception as e:
            logger.error(f"Failed to create temporary output file: {e}")
            return None

    @staticmethod
    def cleanup_temp_file(file_path: Optional[str]) -> None:
        """
        Clean up temporary file after use.

        Args:
            file_path: Path to file to delete (does nothing if None)
        """
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")

    def is_format_supported(self, file_path: str) -> bool:
        """
        Check if file format is supported.

        Args:
            file_path: Path to file to check

        Returns:
            True if format is supported, False otherwise
        """
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.SUPPORTED_FORMATS


def convert_audio(input_path: str) -> Optional[str]:
    """
    Convenience function to convert audio file to PCM WAV.

    Args:
        input_path: Path to input audio file

    Returns:
        Path to converted WAV file, or None if conversion fails
    """
    try:
        converter = AudioConverter()
        return converter.convert_audio(input_path)
    except AudioConversionError as e:
        logger.error(f"Audio conversion error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in convert_audio: {e}")
        return None
