# Google Sheets Integration Manager

A robust bi-directional synchronization manager for Google Sheets integration with an SQL database. This module provides comprehensive CRUD operations, sync capabilities, error handling, and audit logging.

## Features

- **Google Sheets Authentication**: Secure authentication using service account credentials
- **Bi-directional Synchronization**: Push local changes to Sheets and pull remote changes
- **CRUD Operations**: Full support for specialists, schedules, bookings, and day-offs
- **Retry Logic**: Resilient retry mechanism with exponential backoff using tenacity
- **Error Handling**: Custom exceptions and comprehensive error logging
- **Audit Logging**: Track all administrative actions and errors
- **Type Safety**: Full type hints with Pydantic models
- **Internationalization (i18n)**: Full Russian and Kazakh language support for user-facing text
- **Audio Pipeline**: Speech-to-text support for RU/KZ voice messages with automatic format conversion
- **Comprehensive Tests**: Mocked tests covering initialization, retries, sync flows, and i18n

## Installation

### Python Dependencies

```bash
pip install -r requirements.txt
```

### System Dependencies

The audio pipeline requires **ffmpeg** to be installed on your system for audio format conversion:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

**Note:** Audio features (voice message transcription) will be unavailable without ffmpeg.

## Configuration

Set the following environment variables or create a `.env` file:

```env
# Google Sheets Integration
SERVICE_ACCOUNT_JSON_PATH=/path/to/service_account.json
GOOGLE_SHEETS_ID=your_spreadsheet_id

# Gemini AI (optional)
GEMINI_API_KEY=your_gemini_api_key

# Audio Pipeline (optional)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account.json
TRANSCRIPTION_TIMEOUT=60
```

## Usage

### Basic Initialization

```python
from integrations.google.sheets_manager import GoogleSheetsManager

manager = GoogleSheetsManager(
    spreadsheet_id="your_sheet_id",
    service_account_path="/path/to/service_account.json"
)
```

### Reading Data

```python
# Read specialists
specialists = manager.read_specialists()

# Read bookings
bookings = manager.read_bookings()

# Read schedule
schedules = manager.read_schedule()
```

### Writing Data

```python
from models import SpecialistDTO, BookingDTO, DayOffDTO

# Add a specialist
specialist = SpecialistDTO(
    name="Dr. John Doe",
    specialization="Cardiology",
    phone="+1234567890",
    email="john@example.com"
)
result = manager.add_specialist(specialist)

# Update a specialist
updated = manager.update_specialist(specialist_id=1, specialist=specialist)

# Delete a specialist
manager.delete_specialist(specialist_id=1)

# Add a booking
booking = BookingDTO(
    specialist_id=1,
    client_name="Alice",
    booking_datetime=datetime(2025, 1, 15, 10, 0),
    duration_minutes=60
)
manager.add_booking(booking)

# Add a day off
day_off = DayOffDTO(
    specialist_id=1,
    date="2025-01-20",
    reason="Vacation"
)
manager.add_day_off(day_off)
```

### Synchronization

```python
# Push local changes to Sheets
sync_state = manager.sync_push_changes(local_specialists, local_bookings)
print(f"Pushed {sync_state.items_pushed} items")
print(f"Conflicts: {sync_state.conflicts_detected}")
print(f"Errors: {sync_state.errors}")

# Pull remote changes from Sheets
sync_state = manager.sync_pull_changes()
print(f"Pulled {sync_state.items_pulled} items")
```

## Worksheets

The manager automatically ensures the following worksheets exist:

1. **Специалисты** (Specialists) - Stores specialist information
2. **Расписание** (Schedule) - Stores working schedule information
3. **Выходные** (Days Off) - Stores day-off records
4. **Записи** (Bookings) - Stores booking information
5. **Логи Админа** (Admin Logs) - Stores administrative action logs
6. **Ошибки** (Errors) - Stores error logs

## Error Handling

The manager provides custom exceptions for different error scenarios:

- `RecoverableExternalError`: Raised when external API calls fail after retries
- `SheetsInitializationError`: Raised during manager initialization failures
- `SheetsError`: General Sheets operation errors
- `SyncError`: Sync operation failures
- `ConflictError`: Detected conflicts during sync

All errors are automatically logged to the "Ошибки" worksheet.

## Retry Logic

All Sheets API operations are wrapped with retry logic:

- **Max Attempts**: 3
- **Backoff Strategy**: Exponential backoff
- **Initial Delay**: 2 seconds
- **Maximum Delay**: 10 seconds
- **Retry Conditions**: API errors and OS errors

## Testing

Run the test suite:

```bash
pytest
pytest -v  # Verbose output
pytest tests/test_sheets_manager.py -v  # Specific test file
```

## Internationalization (i18n)

The system supports Russian and Kazakh languages for all user-facing text:

```python
from core.i18n import get_text, detect_language

# Detect user's language
language = detect_language(
    telegram_locale="kk",  # Telegram language code
    user_preference="kz"   # Stored user preference
)

# Get localized text
greeting = get_text("greetings.hello", language, name="Иван")
# Russian: "Здравствуйте, Иван!"
# Kazakh: "Сәлеметсіз бе, Иван!"

# Get booking confirmation
confirmation = get_text(
    "confirmations.booking_created",
    language,
    specialist="Доктор Иванов",
    date="2025-01-15",
    time="10:00",
    duration=60
)
```

See [core/README.md](core/README.md) for full i18n documentation.

## Audio Pipeline

The audio pipeline provides speech-to-text transcription for voice messages in Russian and Kazakh:

### Basic Usage

```python
from services.audio.pipeline import AudioPipeline

# Initialize pipeline
pipeline = AudioPipeline()

# Check if available
if pipeline.is_available():
    # Process voice message
    transcript = pipeline.process_voice_message(
        audio_file_path="/path/to/voice.oga",
        language="ru",  # or "kz" for Kazakh
        cleanup=True,   # Cleanup temporary files
    )
    
    if transcript:
        print(f"Transcription: {transcript}")
    else:
        print("Transcription failed, use manual mode")
```

### Converter Only

```python
from services.audio.converter import convert_audio

# Convert audio to WAV format
wav_path = convert_audio("/path/to/voice.oga")

if wav_path:
    print(f"Converted: {wav_path}")
    # Remember to cleanup
    from services.audio.converter import AudioConverter
    AudioConverter.cleanup_temp_file(wav_path)
```

### Transcriber Only

```python
from services.audio.transcriber import transcribe_audio

# Transcribe pre-converted WAV file
transcript = transcribe_audio(
    audio_file_path="/path/to/audio.wav",
    language="kz",
)

if transcript:
    print(f"Transcript: {transcript}")
```

### With Error Logging to Sheets

```python
from services.audio.pipeline import AudioPipeline
from integrations.google.sheets_manager import GoogleSheetsManager

# Initialize sheets manager
sheets = GoogleSheetsManager(spreadsheet_id="your_id")

# Create pipeline with error logging
pipeline = AudioPipeline(
    error_logger=sheets._log_error
)

# Process with automatic error logging
transcript = pipeline.process_voice_message(
    audio_file_path="/path/to/voice.m4a",
    language="ru",
)
```

### Supported Formats

- **Telegram**: `.oga`, `.ogg`
- **WhatsApp**: `.m4a`
- **General**: `.mp3`, `.wav`

All formats are converted to 16kHz mono PCM WAV for optimal speech recognition.

### Language Support

- `ru`: Russian (Google Cloud: `ru-RU`)
- `kz`: Kazakh (Google Cloud: `ru-KZ`)
- `kk`: Kazakh alternative (Google Cloud: `ru-KZ`)

## Data Models

All data is transferred using Pydantic models for type safety:

- `SpecialistDTO`: Specialist information
- `ScheduleDTO`: Schedule information
- `BookingDTO`: Booking information
- `DayOffDTO`: Day-off information
- `AdminActionDTO`: Administrative action log
- `ErrorLogDTO`: Error log entry
- `SyncState`: Sync operation state
- `UserSession`: User session with language preference

## Architecture

- **settings.py**: Configuration management
- **models.py**: Pydantic data models and DTOs
- **exceptions.py**: Custom exception classes
- **core/i18n.py**: Internationalization module
- **core/conversation.py**: Conversation FSM and context management
- **locales/**: Translation files (ru.json, kz.json)
- **integrations/google/sheets_manager.py**: Main manager implementation
- **services/gemini/**: AI-powered request analysis (client.py, analyzer.py)
- **services/audio/**: Audio processing pipeline
  - **converter.py**: Audio format conversion (pydub/ffmpeg)
  - **transcriber.py**: Speech-to-text (Google Cloud Speech-to-Text)
  - **pipeline.py**: Complete processing pipeline with error logging
- **tests/**: Comprehensive test suites
  - **test_sheets_manager.py**: Sheets manager tests
  - **test_i18n.py**: Internationalization tests
  - **test_conversation.py**: Conversation FSM tests
  - **test_gemini_*.py**: Gemini AI service tests
  - **test_audio_*.py**: Audio pipeline tests

## Logging

The manager uses Python's logging module. Configure logging as follows:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("integrations.google.sheets_manager")
```

## License

This project is part of the VITA system.
