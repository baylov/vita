# Audio Pipeline Implementation Summary

## Overview

Implemented a complete audio processing pipeline for the VITA system that provides speech-to-text transcription support for Russian and Kazakh voice messages. The pipeline converts various audio formats (Telegram .oga/.ogg, WhatsApp .m4a) into PCM WAV and transcribes them using Google Cloud Speech-to-Text API.

## Implementation Details

### 1. Audio Converter (`services/audio/converter.py`)

**Purpose**: Convert various audio formats to PCM WAV optimized for speech recognition.

**Features**:
- Supports multiple formats: `.oga`, `.ogg`, `.m4a`, `.mp3`, `.wav`
- Converts to 16kHz mono PCM WAV (optimal for speech recognition)
- Temporary file management with automatic cleanup
- Duration validation (min 0.1s, warns if > 10 minutes)
- Graceful error handling - returns None on failure

**Key Methods**:
- `convert_audio(input_path)`: Main conversion function
- `cleanup_temp_file(file_path)`: Clean up temporary files
- `is_format_supported(file_path)`: Check format support

**Dependencies**:
- pydub (Python library)
- ffmpeg (system dependency)

**Tests**: 21 tests covering conversion, format support, error handling

### 2. Speech Transcriber (`services/audio/transcriber.py`)

**Purpose**: Transcribe audio to text using Google Cloud Speech-to-Text API.

**Features**:
- Language mapping: `ru` → `ru-RU`, `kz`/`kk` → `ru-KZ`
- Automatic punctuation enabled by default
- Synchronous recognition for files < 10MB
- Asynchronous recognition for larger files
- Configurable timeout (default 60 seconds)
- Enhanced model usage when available
- Graceful error handling - returns None on failure

**Key Methods**:
- `transcribe(audio_file_path, language, enable_automatic_punctuation)`: Main transcription
- `_transcribe_sync()`: For short audio files
- `_transcribe_async()`: For long audio files
- `_map_language_code()`: Map system codes to Google Cloud codes

**Configuration**:
- `GOOGLE_APPLICATION_CREDENTIALS`: Service account JSON path
- `TRANSCRIPTION_TIMEOUT`: Timeout in seconds

**Tests**: 28 tests covering transcription, language mapping, error handling

### 3. Complete Pipeline (`services/audio/pipeline.py`)

**Purpose**: Integrate conversion and transcription with error logging to Google Sheets.

**Features**:
- Complete processing: convert → transcribe → cleanup
- Integrated error logging to Sheets "Ошибки" worksheet
- Automatic component initialization (optional)
- Availability checking via `is_available()`
- Graceful error handling with fallback indicators

**Key Methods**:
- `process_voice_message(audio_file_path, language, cleanup)`: Complete processing
- `is_available()`: Check if both components are ready
- `_log_error()`: Log errors to Sheets via callback

**Usage**:
```python
from services.audio.pipeline import AudioPipeline
from integrations.google.sheets_manager import GoogleSheetsManager

# Initialize with error logging
sheets = GoogleSheetsManager(spreadsheet_id="your_id")
pipeline = AudioPipeline(error_logger=sheets._log_error)

# Process voice message
transcript = pipeline.process_voice_message(
    audio_file_path="/path/to/voice.oga",
    language="ru",
    cleanup=True,
)

if transcript:
    print(f"Transcription: {transcript}")
else:
    # Fall back to manual mode
    print("Transcription failed, use manual input")
```

**Tests**: 21 tests covering pipeline integration, error handling, cleanup

## Configuration

### Environment Variables

```env
# Google Cloud Speech-to-Text
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account.json
TRANSCRIPTION_TIMEOUT=60
```

### System Dependencies

**ffmpeg** is required for audio conversion:

**Ubuntu/Debian**:
```bash
sudo apt-get install ffmpeg
```

**macOS**:
```bash
brew install ffmpeg
```

**Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### Python Dependencies

Added to `requirements.txt`:
- `pydub>=0.25.1`
- `google-cloud-speech>=2.21.0`

## Exception Handling

New exceptions added to `exceptions.py`:
- `AudioError`: Base exception for audio processing
- `AudioConversionError`: Audio format conversion failure
- `TranscriptionError`: Speech-to-text transcription failure

**Error Handling Strategy**:
1. All external calls wrapped in try/except
2. Errors logged via Python logging module
3. Errors recorded to Google Sheets "Ошибки" worksheet
4. Returns None (not raising exceptions) to enable graceful fallback
5. Calling code can detect failure and trigger manual mode

## Internationalization

Added locale strings to `locales/ru.json` and `locales/kz.json`:

```json
{
  "audio": {
    "conversion_error": "Ошибка конвертации аудио. Попробуйте отправить сообщение текстом.",
    "transcription_error": "Не удалось распознать речь. Пожалуйста, отправьте текстовое сообщение.",
    "unsupported_format": "Неподдерживаемый формат аудио. Используйте голосовые сообщения или текст.",
    "processing": "Обрабатываю голосовое сообщение...",
    "too_short": "Аудио слишком короткое. Пожалуйста, попробуйте снова.",
    "too_long": "Аудио слишком длинное. Максимальная длина: 10 минут."
  }
}
```

## Testing

### Test Coverage

Total: **70 tests** across 3 test files, all passing

1. **test_audio_converter.py** (21 tests):
   - Initialization with/without pydub
   - Conversion success for various formats
   - Error handling (file not found, unsupported format, load/export failures)
   - Duration validation (too short, too long)
   - Temp file cleanup
   - Format support checking
   - Convenience function

2. **test_audio_transcriber.py** (28 tests):
   - Initialization with/without google-cloud-speech
   - Transcription success for Russian and Kazakh
   - Sync vs async method selection based on file size
   - Error handling (file not found, API errors, no results)
   - Language code mapping
   - Punctuation control
   - Multiple results concatenation
   - Timeout handling
   - Convenience function

3. **test_audio_pipeline.py** (21 tests):
   - Full pipeline integration
   - Component availability checking
   - Error handling at each stage
   - Error logging to Sheets
   - Cleanup behavior
   - Multi-language support
   - Component failure handling

### Running Tests

```bash
# All audio tests
pytest tests/test_audio_*.py -v

# Specific test file
pytest tests/test_audio_converter.py -v

# All tests
pytest tests/ -v
```

## Architecture Decisions

### 1. Graceful Degradation
All functions return `None` on failure rather than raising exceptions, allowing calling code to fall back to manual text input mode.

### 2. Separation of Concerns
- Converter: Only handles format conversion
- Transcriber: Only handles speech-to-text
- Pipeline: Orchestrates both with error logging

### 3. Dependency Injection
Pipeline accepts optional converter/transcriber instances for testing and flexibility.

### 4. Auto-initialization
Pipeline can auto-create components (default) or use provided instances, controlled by `auto_init` parameter.

### 5. Cleanup Strategy
Temporary WAV files are automatically cleaned up after transcription unless explicitly disabled.

### 6. Error Logging Integration
Pipeline accepts an optional error logger callback to log to Google Sheets "Ошибки" worksheet.

## Integration Points

### With Google Sheets Manager

```python
from integrations.google.sheets_manager import GoogleSheetsManager

sheets = GoogleSheetsManager(spreadsheet_id="your_id")

# Use _log_error method as error logger
pipeline = AudioPipeline(error_logger=sheets._log_error)
```

### With i18n System

```python
from core.i18n import get_text

# Get localized error messages
error_msg = get_text("audio.transcription_error", language="ru")
```

### With Conversation System

```python
# In conversation handler
if is_voice_message:
    pipeline = AudioPipeline()
    transcript = pipeline.process_voice_message(
        audio_file_path=voice_file,
        language=user_language,
    )
    
    if transcript:
        # Process transcribed text
        handle_text_message(transcript)
    else:
        # Fallback to manual input
        send_message(get_text("audio.transcription_error", user_language))
```

## Performance Considerations

1. **Conversion Speed**: pydub/ffmpeg conversion is fast (< 1s for typical voice messages)
2. **Transcription Latency**: 
   - Sync: 1-3 seconds for short audio
   - Async: 5-15 seconds for longer audio
3. **File Size Limits**:
   - Sync method: Up to 10 MB
   - Async method: Larger files supported
4. **Timeout Configuration**: Configurable via `TRANSCRIPTION_TIMEOUT` environment variable

## Security Considerations

1. **Credentials**: Google Cloud credentials stored in service account JSON (excluded from git)
2. **Temporary Files**: Cleaned up after use, stored in system temp directory
3. **Error Messages**: Sanitized before logging to Sheets
4. **API Keys**: Never logged or exposed in error messages

## Known Limitations

1. **ffmpeg Required**: Audio conversion unavailable without ffmpeg
2. **Google Cloud Required**: Transcription requires Google Cloud Speech-to-Text API access
3. **Language Support**: Currently limited to Russian and Kazakh
4. **Audio Quality**: Poor quality audio may result in low transcription accuracy
5. **Network Dependency**: Requires internet connection for transcription API

## Future Enhancements

Possible improvements for future iterations:

1. Support for additional languages
2. Offline transcription using local models
3. Audio quality pre-validation
4. Confidence score thresholds
5. Alternative transcription providers (fallback)
6. Caching of transcriptions
7. Audio enhancement/denoising preprocessing
8. Speaker diarization for multi-speaker audio

## Documentation

- **README.md**: Updated with audio pipeline usage, configuration, and system dependencies
- **Architecture section**: Added audio services to project structure
- **Installation section**: Added ffmpeg system dependency instructions
- **Configuration section**: Added Google Cloud credentials and timeout settings

## Acceptance Criteria Met

✅ Voice notes in supported formats (.oga, .ogg, .m4a) convert to WAV
✅ Transcription succeeds when Google API is available
✅ On transcription failure, functions return None (not raise exceptions)
✅ Errors logged to Google Sheets "Ошибки" worksheet
✅ All external calls wrapped in try/except with logging
✅ 70 comprehensive tests validating conversion, transcription, and error handling
✅ Tests use mocks for Google Cloud client
✅ ffmpeg system dependency documented in README
✅ Graceful failure indicators trigger manual mode fallback

## Summary

The audio pipeline implementation provides a robust, well-tested foundation for voice message support in the VITA system. The architecture emphasizes graceful degradation, comprehensive error handling, and integration with existing system components (Sheets error logging, i18n, conversation FSM). All 70 tests pass, demonstrating correct behavior across conversion, transcription, and error scenarios.
