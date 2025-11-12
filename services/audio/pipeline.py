"""Complete audio processing pipeline with error logging."""

import logging
import traceback
from typing import Optional, Callable

from services.audio.converter import AudioConverter
from services.audio.transcriber import SpeechTranscriber
from exceptions import AudioConversionError, TranscriptionError

logger = logging.getLogger(__name__)


class AudioPipeline:
    """
    Complete audio processing pipeline.
    
    Combines conversion and transcription with comprehensive error handling
    and error logging to Google Sheets.
    """

    def __init__(
        self,
        error_logger: Optional[Callable[[str, str, Optional[str], Optional[str]], None]] = None,
        converter: Optional[AudioConverter] = None,
        transcriber: Optional[SpeechTranscriber] = None,
        auto_init: bool = True,
    ):
        """
        Initialize audio pipeline.

        Args:
            error_logger: Function to log errors (error_type, message, context, traceback)
            converter: AudioConverter instance (creates new if not provided and auto_init=True)
            transcriber: SpeechTranscriber instance (creates new if not provided and auto_init=True)
            auto_init: Whether to auto-create components if not provided (default True)
        """
        self.error_logger = error_logger
        
        # Initialize converter
        if converter is not None:
            self.converter = converter
        elif auto_init:
            try:
                self.converter = AudioConverter()
            except AudioConversionError as e:
                logger.error(f"Failed to initialize audio converter: {e}")
                self.converter = None
                if error_logger:
                    error_logger(
                        "audio_init_error",
                        f"Converter initialization failed: {str(e)}",
                        "AudioPipeline.__init__",
                        None,
                    )
        else:
            self.converter = None

        # Initialize transcriber
        if transcriber is not None:
            self.transcriber = transcriber
        elif auto_init:
            try:
                self.transcriber = SpeechTranscriber()
            except TranscriptionError as e:
                logger.error(f"Failed to initialize transcriber: {e}")
                self.transcriber = None
                if error_logger:
                    error_logger(
                        "audio_init_error",
                        f"Transcriber initialization failed: {str(e)}",
                        "AudioPipeline.__init__",
                        None,
                    )
        else:
            self.transcriber = None

    def process_voice_message(
        self,
        audio_file_path: str,
        language: str = "ru",
        cleanup: bool = True,
    ) -> Optional[str]:
        """
        Process voice message: convert and transcribe.

        Args:
            audio_file_path: Path to audio file (any supported format)
            language: Language code ('ru' or 'kz')
            cleanup: Whether to cleanup converted WAV file after transcription

        Returns:
            Transcribed text or None on failure (errors logged to Sheets)
        """
        converted_path = None
        
        try:
            # Check if components are available
            if not self.converter:
                logger.error("Audio converter not available")
                self._log_error(
                    "audio_unavailable",
                    "Audio converter not initialized",
                    f"File: {audio_file_path}",
                )
                return None

            if not self.transcriber:
                logger.error("Speech transcriber not available")
                self._log_error(
                    "audio_unavailable",
                    "Speech transcriber not initialized",
                    f"File: {audio_file_path}",
                )
                return None

            # Step 1: Convert audio to WAV
            logger.info(f"Converting audio: {audio_file_path}")
            converted_path = self.converter.convert_audio(audio_file_path)
            
            if not converted_path:
                logger.error(f"Audio conversion failed: {audio_file_path}")
                self._log_error(
                    "audio_conversion_error",
                    "Failed to convert audio to WAV format",
                    f"Input: {audio_file_path}, Language: {language}",
                )
                return None

            logger.info(f"Audio converted successfully: {converted_path}")

            # Step 2: Transcribe audio
            logger.info(f"Transcribing audio (language: {language})")
            transcript = self.transcriber.transcribe(
                converted_path,
                language=language,
                enable_automatic_punctuation=True,
            )

            if not transcript:
                logger.error(f"Transcription failed: {converted_path}")
                self._log_error(
                    "transcription_error",
                    "Speech-to-text transcription returned no results",
                    f"File: {converted_path}, Language: {language}",
                )
                return None

            logger.info(f"Transcription successful: {len(transcript)} chars")
            return transcript

        except Exception as e:
            logger.error(f"Unexpected error in audio pipeline: {e}", exc_info=True)
            self._log_error(
                "audio_pipeline_error",
                f"Unexpected error: {str(e)}",
                f"File: {audio_file_path}, Language: {language}",
                traceback.format_exc(),
            )
            return None

        finally:
            # Cleanup converted file if requested
            if cleanup and converted_path and self.converter:
                self.converter.cleanup_temp_file(converted_path)

    def _log_error(
        self,
        error_type: str,
        message: str,
        context: Optional[str] = None,
        error_traceback: Optional[str] = None,
    ) -> None:
        """
        Log error to Sheets if error logger is configured.

        Args:
            error_type: Type of error
            message: Error message
            context: Additional context
            error_traceback: Error traceback string
        """
        if self.error_logger:
            try:
                self.error_logger(error_type, message, context, error_traceback)
                logger.debug(f"Error logged to Sheets: {error_type}")
            except Exception as e:
                logger.error(f"Failed to log error to Sheets: {e}")

    def is_available(self) -> bool:
        """
        Check if audio pipeline is available.

        Returns:
            True if both converter and transcriber are initialized
        """
        return self.converter is not None and self.transcriber is not None
