"""Speech-to-text transcription using Google Cloud Speech-to-Text API."""

import logging
import os
from typing import Optional

try:
    from google.cloud import speech_v1
    from google.cloud.speech_v1 import RecognitionConfig, RecognitionAudio
except ImportError:
    speech_v1 = None
    RecognitionConfig = None
    RecognitionAudio = None

from exceptions import TranscriptionError
from settings import settings

logger = logging.getLogger(__name__)


class SpeechTranscriber:
    """Transcribes audio files using Google Cloud Speech-to-Text API."""

    # Language mapping: system language code -> Google Cloud language code
    LANGUAGE_MAP = {
        "ru": "ru-RU",  # Russian
        "kz": "ru-KZ",  # Kazakh variant of Russian
        "kk": "ru-KZ",  # Kazakh (Telegram code)
    }

    # Maximum audio size for synchronous recognition (1 minute)
    MAX_SYNC_DURATION_SECONDS = 60
    MAX_SYNC_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialize the speech transcriber.

        Args:
            credentials_path: Path to Google Cloud service account JSON
            timeout: Request timeout in seconds (default from settings)

        Raises:
            TranscriptionError: If Google Cloud Speech library not available
        """
        if speech_v1 is None:
            logger.error("google-cloud-speech library not installed")
            raise TranscriptionError(
                "google-cloud-speech library required. "
                "Install with: pip install google-cloud-speech"
            )

        self.credentials_path = (
            credentials_path or settings.google_cloud_credentials_path
        )
        self.timeout = timeout or settings.transcription_timeout
        self.client = None

        # Set credentials environment variable if provided
        if self.credentials_path and os.path.exists(self.credentials_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
            logger.info(f"Using Google Cloud credentials: {self.credentials_path}")
        else:
            logger.warning(
                f"Credentials file not found: {self.credentials_path}. "
                "Relying on default credentials."
            )

    def _get_client(self) -> Optional[speech_v1.SpeechClient]:
        """
        Get or create Speech client.

        Returns:
            SpeechClient instance or None on failure
        """
        if self.client is not None:
            return self.client

        try:
            self.client = speech_v1.SpeechClient()
            logger.info("Google Cloud Speech client initialized")
            return self.client
        except Exception as e:
            logger.error(f"Failed to initialize Speech client: {e}")
            return None

    def transcribe(
        self,
        audio_file_path: str,
        language: str = "ru",
        enable_automatic_punctuation: bool = True,
    ) -> Optional[str]:
        """
        Transcribe audio file to text.

        Args:
            audio_file_path: Path to audio file (must be WAV format)
            language: Language code ('ru' or 'kz')
            enable_automatic_punctuation: Enable automatic punctuation

        Returns:
            Transcribed text or None on failure
        """
        try:
            # Validate audio file
            if not os.path.exists(audio_file_path):
                logger.error(f"Audio file not found: {audio_file_path}")
                return None

            # Get file size
            file_size = os.path.getsize(audio_file_path)
            logger.info(
                f"Transcribing audio: {audio_file_path} "
                f"({file_size / 1024:.1f} KB, language: {language})"
            )

            # Get Speech client
            client = self._get_client()
            if client is None:
                logger.error("Speech client not available")
                return None

            # Map language code
            google_language_code = self._map_language_code(language)

            # Choose recognition method based on file size
            if file_size <= self.MAX_SYNC_FILE_SIZE_BYTES:
                return self._transcribe_sync(
                    client,
                    audio_file_path,
                    google_language_code,
                    enable_automatic_punctuation,
                )
            else:
                return self._transcribe_async(
                    client,
                    audio_file_path,
                    google_language_code,
                    enable_automatic_punctuation,
                )

        except Exception as e:
            logger.error(f"Error during transcription: {e}", exc_info=True)
            return None

    def _transcribe_sync(
        self,
        client: speech_v1.SpeechClient,
        audio_file_path: str,
        language_code: str,
        enable_punctuation: bool,
    ) -> Optional[str]:
        """
        Synchronous transcription for short audio files.

        Args:
            client: Speech client instance
            audio_file_path: Path to audio file
            language_code: Google Cloud language code
            enable_punctuation: Enable automatic punctuation

        Returns:
            Transcribed text or None on failure
        """
        try:
            # Read audio file
            with open(audio_file_path, "rb") as audio_file:
                content = audio_file.read()

            # Create recognition audio
            audio = RecognitionAudio(content=content)

            # Configure recognition
            config = RecognitionConfig(
                encoding=RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language_code,
                enable_automatic_punctuation=enable_punctuation,
                model="default",
                use_enhanced=True,
            )

            # Perform recognition
            logger.debug(f"Starting synchronous recognition (language: {language_code})")
            response = client.recognize(
                config=config,
                audio=audio,
                timeout=self.timeout,
            )

            # Extract transcript
            transcript = self._extract_transcript(response)
            if transcript:
                logger.info(f"Transcription successful: {len(transcript)} characters")
            else:
                logger.warning("No transcript produced")

            return transcript

        except Exception as e:
            logger.error(f"Synchronous transcription failed: {e}", exc_info=True)
            return None

    def _transcribe_async(
        self,
        client: speech_v1.SpeechClient,
        audio_file_path: str,
        language_code: str,
        enable_punctuation: bool,
    ) -> Optional[str]:
        """
        Asynchronous transcription for long audio files.

        Args:
            client: Speech client instance
            audio_file_path: Path to audio file
            language_code: Google Cloud language code
            enable_punctuation: Enable automatic punctuation

        Returns:
            Transcribed text or None on failure
        """
        try:
            # Read audio file in chunks
            with open(audio_file_path, "rb") as audio_file:
                content = audio_file.read()

            # Create recognition audio
            audio = RecognitionAudio(content=content)

            # Configure recognition with chunked upload support
            config = RecognitionConfig(
                encoding=RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language_code,
                enable_automatic_punctuation=enable_punctuation,
                model="default",
                use_enhanced=True,
            )

            # Perform long-running recognition
            logger.debug(f"Starting asynchronous recognition (language: {language_code})")
            operation = client.long_running_recognize(
                config=config,
                audio=audio,
                timeout=self.timeout,
            )

            # Wait for operation to complete
            logger.info("Waiting for long-running transcription to complete...")
            response = operation.result(timeout=self.timeout * 2)

            # Extract transcript
            transcript = self._extract_transcript(response)
            if transcript:
                logger.info(f"Async transcription successful: {len(transcript)} characters")
            else:
                logger.warning("No transcript produced from async operation")

            return transcript

        except Exception as e:
            logger.error(f"Asynchronous transcription failed: {e}", exc_info=True)
            return None

    def _extract_transcript(self, response) -> Optional[str]:
        """
        Extract transcript text from recognition response.

        Args:
            response: Speech recognition response

        Returns:
            Transcribed text or None if no results
        """
        if not response.results:
            logger.warning("No results in recognition response")
            return None

        # Concatenate all alternatives (taking the best one from each result)
        transcripts = []
        for result in response.results:
            if result.alternatives:
                # Take the first (best) alternative
                best_alternative = result.alternatives[0]
                transcripts.append(best_alternative.transcript)
                logger.debug(
                    f"Alternative confidence: {best_alternative.confidence:.2f}"
                )

        full_transcript = " ".join(transcripts).strip()
        return full_transcript if full_transcript else None

    def _map_language_code(self, language: str) -> str:
        """
        Map system language code to Google Cloud language code.

        Args:
            language: System language code ('ru', 'kz', 'kk')

        Returns:
            Google Cloud language code
        """
        mapped = self.LANGUAGE_MAP.get(language.lower(), "ru-RU")
        logger.debug(f"Language mapping: {language} -> {mapped}")
        return mapped


def transcribe_audio(
    audio_file_path: str,
    language: str = "ru",
    credentials_path: Optional[str] = None,
) -> Optional[str]:
    """
    Convenience function to transcribe audio file.

    Args:
        audio_file_path: Path to audio file (WAV format)
        language: Language code ('ru' or 'kz')
        credentials_path: Optional Google Cloud credentials path

    Returns:
        Transcribed text or None on failure
    """
    try:
        transcriber = SpeechTranscriber(credentials_path=credentials_path)
        return transcriber.transcribe(audio_file_path, language=language)
    except TranscriptionError as e:
        logger.error(f"Transcription error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in transcribe_audio: {e}")
        return None
