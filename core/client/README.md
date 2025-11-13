# Client Dialog Handlers

This module implements the primary customer interaction flow for the VITA booking system, supporting both text and voice messages through Telegram.

## Overview

The client handlers manage the complete booking workflow using a Finite State Machine (FSM) pattern, integrating with:
- **Gemini AI** for intent classification and response generation
- **Google Sheets** for data persistence
- **Audio Pipeline** for voice message transcription
- **Notification Service** for admin alerts

## Features

### 1. Text Message Handling
- **Intent Classification**: Uses Gemini to classify user requests (booking, schedule inquiry, complaint, etc.)
- **FSM-Driven Flow**: Guides users through booking steps with state validation
- **Data Collection**: Gathers name, phone, doctor choice, date, and time
- **Input Validation**: Validates all user inputs before state transitions
- **Conflict Detection**: Checks for double-booked time slots
- **Alternative Suggestions**: Offers available times when conflicts occur

### 2. Voice Message Handling
- **Audio Download**: Downloads voice messages from Telegram
- **Transcription**: Converts speech to text using Google Cloud Speech-to-Text
- **Seamless Integration**: Processes transcribed text through same flow as text messages
- **Error Handling**: Falls back gracefully on transcription failures

### 3. Booking Creation
- **Validation**: Ensures all required data is collected
- **Conflict Checking**: Prevents double-booking of time slots
- **Sheets Sync**: Saves bookings to Google Sheets
- **Notifications**: Alerts admins of new bookings
- **Confirmation**: Sends confirmation message to client

### 4. Fallback/Manual Mode
- **Gemini Failures**: Uses fallback classifications when AI is unavailable
- **Sheets Failures**: Informs client and notifies admins for manual follow-up
- **Never Breaks**: Conversation flow continues even when external services fail
- **Admin Notifications**: Immediate alerts when manual intervention needed

## State Machine Flow

```
START
  ↓
WAITING_NAME (collect client name)
  ↓
WAITING_PHONE (collect phone number)
  ↓
WAITING_DOCTOR_CHOICE (select specialist)
  ↓
WAITING_DATE (select appointment date)
  ↓
WAITING_TIME (select appointment time)
  ↓
CONFIRM_BOOKING (confirm or go back)
  ↓
DONE (booking created)
```

## Usage

### Initialize Services

```python
from core.client.handlers import client_router, initialize_services
from services.gemini.analyzer import GeminiAnalyzer
from services.audio.pipeline import AudioPipeline
from integrations.google.sheets_manager import GoogleSheetsManager
from services.notifications.notifier import Notifier

# Initialize dependencies
gemini = GeminiAnalyzer()
audio_pipeline = AudioPipeline()
sheets_manager = GoogleSheetsManager(spreadsheet_id="...")
notifier = Notifier()

# Initialize client handlers
initialize_services(
    gemini_analyzer=gemini,
    audio_pipeline=audio_pipeline,
    sheets_manager=sheets_manager,
    notifier=notifier,
)

# Register router with aiogram dispatcher
dp.include_router(client_router)
```

### Commands

- `/start` - Begin conversation and start booking flow

### Inline Callbacks

- `doctor_{id}` - Select specialist by ID
- `confirm_booking_yes` - Confirm booking
- `confirm_booking_no` - Cancel and go back to date selection

## Intent Types

The system recognizes the following intent types via Gemini classification:

1. **APPOINTMENT_BOOKING** - User wants to make an appointment
2. **SCHEDULE_INQUIRY** - User asks about doctor schedules
3. **SPECIALIST_INQUIRY** - User asks about available specialists
4. **COMPLAINT** - User submits a complaint (escalated to admins)
5. **GENERAL_INQUIRY** - General questions (AI-generated responses)

## Error Handling

### Validation Errors
- Invalid name: Must be 2-100 characters, letters/hyphens/apostrophes only
- Invalid phone: Must be 10-12 digits, Kazakhstan/Russia format
- Invalid date: Must be YYYY-MM-DD, not in past, within 90 days
- Invalid time: Must be HH:MM format

### Service Failures

**Gemini Failure:**
```python
# Falls back to default booking flow
# Notifies admins for complex queries
```

**Sheets Failure:**
```python
# Shows error: "Передам администратору"
# Notifies admins with collected data
# Conversation state preserved
```

**Audio Pipeline Failure:**
```python
# Shows error: "Не удалось распознать речь"
# Asks user to send text message
# Notifies admins of failure
```

## Localization

All responses support Russian (ru) and Kazakh (kz) via the i18n system:

```python
from core.i18n import get_text

message = get_text("prompts.enter_name", language="ru")
# Returns: "Введите ваше имя:"

message = get_text("prompts.enter_name", language="kz")
# Returns: "Атыңызды енгізіңіз:"
```

## Testing

Run the comprehensive test suite:

```bash
pytest tests/test_client_handlers.py -v
```

### Test Coverage

- ✅ Start command and conversation initialization
- ✅ Complete booking flow with valid inputs
- ✅ Booking conflict detection and alternatives
- ✅ Voice message transcription and processing
- ✅ Intent classification (schedule, complaints)
- ✅ Input validation (name, phone, date, time)
- ✅ Gemini service failure fallback
- ✅ Sheets service failure fallback
- ✅ Admin notification on failures
- ✅ Booking cancellation flow

## Architecture

### Dependencies

```
core/client/handlers.py
├── core/conversation.py (FSM and context)
├── core/i18n.py (localization)
├── services/gemini/analyzer.py (AI classification)
├── services/audio/pipeline.py (voice processing)
├── services/repositories.py (data access)
├── services/validators.py (input validation)
├── integrations/google/sheets_manager.py (persistence)
└── services/notifications/notifier.py (admin alerts)
```

### Key Functions

- `cmd_start()` - Handle /start command
- `handle_message()` - Route text messages based on FSM state
- `handle_voice()` - Process voice messages
- `create_booking()` - Create and persist booking
- `check_booking_conflict()` - Detect scheduling conflicts
- `suggest_alternative_times()` - Find available slots
- `notify_admins_for_manual_followup()` - Alert admins on failures

## Notes

- Context is persisted in memory (can be extended to DB)
- All external service calls include error handling
- Admin notifications use immediate alert tier
- Voice messages are deleted after transcription
- Booking conflicts check 60-minute default duration
- Alternative times suggested hourly from 9:00-18:00
