"""Integration tests for client dialog handlers."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from aiogram.types import Message, User, Chat, CallbackQuery, Voice, File

from core.client.handlers import (
    client_router,
    initialize_services,
    cmd_start,
    handle_message,
    handle_voice,
    handle_doctor_callback,
    handle_booking_yes,
    handle_booking_no,
    create_booking,
    check_booking_conflict,
    suggest_alternative_times,
)
from core.conversation import (
    get_storage,
    reset_storage,
    ConversationState,
    CollectedInfo,
)
from models import SpecialistDTO, BookingDTO, ScheduleDTO
from services.gemini.analyzer import GeminiAnalyzer, ClassificationResult, RequestType, UrgencyLevel
from services.audio.pipeline import AudioPipeline
from integrations.google.sheets_manager import GoogleSheetsManager
from services.notifications.notifier import Notifier
from settings import settings


@pytest.fixture
def mock_user():
    """Create mock Telegram user."""
    user = Mock(spec=User)
    user.id = 123456
    user.language_code = "ru"
    user.username = "testuser"
    return user


@pytest.fixture
def mock_chat():
    """Create mock Telegram chat."""
    chat = Mock(spec=Chat)
    chat.id = 123456
    chat.type = "private"
    return chat


@pytest.fixture
def mock_message(mock_user, mock_chat):
    """Create mock Telegram message."""
    message = Mock(spec=Message)
    message.from_user = mock_user
    message.chat = mock_chat
    message.text = "Test message"
    message.answer = AsyncMock()
    message.bot = AsyncMock()
    return message


@pytest.fixture
def mock_callback_query(mock_user, mock_message):
    """Create mock callback query."""
    callback = Mock(spec=CallbackQuery)
    callback.from_user = mock_user
    callback.message = mock_message
    callback.data = "test_callback"
    callback.answer = AsyncMock()
    return callback


@pytest.fixture
def mock_gemini_analyzer():
    """Create mock Gemini analyzer."""
    analyzer = Mock(spec=GeminiAnalyzer)
    
    # Mock classify_request
    analyzer.classify_request.return_value = ClassificationResult(
        request_type=RequestType.APPOINTMENT_BOOKING,
        urgency=UrgencyLevel.MEDIUM,
        confidence=0.9,
    )
    
    # Mock generate_response
    from services.gemini.analyzer import ResponseResult
    analyzer.generate_response.return_value = ResponseResult(
        text="Спасибо за ваше сообщение!",
        is_fallback=False,
    )
    
    # Mock summarize_complaint
    analyzer.summarize_complaint.return_value = ResponseResult(
        text="Жалоба на качество обслуживания",
        is_fallback=False,
    )
    
    return analyzer


@pytest.fixture
def mock_audio_pipeline():
    """Create mock audio pipeline."""
    pipeline = Mock(spec=AudioPipeline)
    pipeline.is_available.return_value = True
    pipeline.process_voice_message.return_value = "Я хочу записаться к врачу"
    return pipeline


@pytest.fixture
def mock_sheets_manager():
    """Create mock sheets manager."""
    manager = Mock(spec=GoogleSheetsManager)
    
    # Mock read_specialists
    manager.read_specialists.return_value = [
        SpecialistDTO(
            id=1,
            name="Доктор Иванов",
            specialization="Терапевт",
            phone="+77771234567",
            is_active=True,
        ),
        SpecialistDTO(
            id=2,
            name="Доктор Петров",
            specialization="Кардиолог",
            phone="+77771234568",
            is_active=True,
        ),
    ]
    
    # Mock read_bookings
    manager.read_bookings.return_value = []
    
    # Mock read_schedule
    manager.read_schedule.return_value = [
        ScheduleDTO(
            id=1,
            specialist_id=1,
            day_of_week=0,  # Monday
            start_time="09:00",
            end_time="17:00",
            is_available=True,
        ),
    ]
    
    # Mock add_booking
    def add_booking_side_effect(booking):
        booking.id = 100
        booking.created_at = datetime.now(timezone.utc)
        booking.updated_at = datetime.now(timezone.utc)
        return booking
    
    manager.add_booking.side_effect = add_booking_side_effect
    
    return manager


@pytest.fixture
def mock_notifier():
    """Create mock notifier."""
    notifier = Mock(spec=Notifier)
    notifier.send_immediate_alert = AsyncMock(return_value=True)
    return notifier


@pytest.fixture(autouse=True)
def setup_services(mock_gemini_analyzer, mock_audio_pipeline, mock_sheets_manager, mock_notifier):
    """Set up services before each test."""
    reset_storage()
    initialize_services(
        gemini_analyzer=mock_gemini_analyzer,
        audio_pipeline=mock_audio_pipeline,
        sheets_manager=mock_sheets_manager,
        notifier=mock_notifier,
    )
    
    # Patch settings.admin_ids globally for all tests
    with patch("core.client.handlers.settings.admin_ids", [999888777]):
        yield
    
    reset_storage()


# ============================================================================
# TEST START COMMAND
# ============================================================================


@pytest.mark.asyncio
async def test_cmd_start(mock_message):
    """Test /start command initializes conversation."""
    await cmd_start(mock_message)
    
    # Check that greeting was sent
    assert mock_message.answer.call_count >= 2
    
    # Check conversation state
    storage = get_storage()
    context = await storage.load(mock_message.from_user.id)
    assert context is not None
    assert context.current_state == ConversationState.WAITING_NAME


# ============================================================================
# TEST BOOKING FLOW SUCCESS
# ============================================================================


@pytest.mark.asyncio
async def test_booking_flow_success(mock_message, mock_sheets_manager):
    """Test complete booking flow with valid inputs."""
    user_id = mock_message.from_user.id
    storage = get_storage()
    
    # 1. Start
    await cmd_start(mock_message)
    context = await storage.load(user_id)
    assert context.current_state == ConversationState.WAITING_NAME
    
    # 2. Enter name
    mock_message.text = "Иван Иванов"
    await handle_message(mock_message)
    context = await storage.load(user_id)
    assert context.current_state == ConversationState.WAITING_PHONE
    assert context.collected_info.name == "Иван Иванов"
    
    # 3. Enter phone
    mock_message.text = "+77771234567"
    await handle_message(mock_message)
    context = await storage.load(user_id)
    assert context.current_state == ConversationState.WAITING_DOCTOR_CHOICE
    assert context.collected_info.phone == "+77771234567"
    
    # 4. Choose doctor via callback
    mock_callback = Mock(spec=CallbackQuery)
    mock_callback.from_user = mock_message.from_user
    mock_callback.message = mock_message
    mock_callback.data = "doctor_1"
    mock_callback.answer = AsyncMock()
    
    await handle_doctor_callback(mock_callback)
    context = await storage.load(user_id)
    assert context.current_state == ConversationState.WAITING_DATE
    assert context.collected_info.doctor_id == 1
    
    # 5. Enter date
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    mock_message.text = tomorrow
    await handle_message(mock_message)
    context = await storage.load(user_id)
    assert context.current_state == ConversationState.WAITING_TIME
    assert context.collected_info.booking_date == tomorrow
    
    # 6. Enter time
    mock_message.text = "14:30"
    await handle_message(mock_message)
    context = await storage.load(user_id)
    assert context.current_state == ConversationState.CONFIRM_BOOKING
    assert context.collected_info.booking_time == "14:30"
    
    # 7. Confirm booking
    mock_callback.data = "confirm_booking_yes"
    await handle_booking_yes(mock_callback)
    
    # Check booking was created
    assert mock_sheets_manager.add_booking.called


@pytest.mark.asyncio
async def test_booking_conflict_detected(mock_message, mock_sheets_manager):
    """Test that booking conflicts are detected and alternatives suggested."""
    user_id = mock_message.from_user.id
    storage = get_storage()
    
    # Set up existing booking
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    existing_booking = BookingDTO(
        id=1,
        specialist_id=1,
        client_name="Existing Client",
        booking_datetime=tomorrow.replace(hour=14, minute=30, second=0, microsecond=0),
        duration_minutes=60,
        status="confirmed",
    )
    mock_sheets_manager.read_bookings.return_value = [existing_booking]
    
    # Navigate to time input
    await storage.update(
        user_id,
        state=ConversationState.WAITING_TIME,
        collected_info=CollectedInfo(
            name="Иван",
            phone="+77771234567",
            doctor_id=1,
            doctor_name="Доктор Иванов",
            booking_date=tomorrow.strftime("%Y-%m-%d"),
        ),
    )
    
    # Try to book conflicting time
    mock_message.text = "14:30"
    await handle_message(mock_message)
    
    # Should show error about unavailable slot
    assert any("занято" in str(call.args[0]).lower() or "unavailable" in str(call.args[0]).lower() 
               for call in mock_message.answer.call_args_list)
    
    # Should still be in WAITING_TIME state
    context = await storage.load(user_id)
    assert context.current_state == ConversationState.WAITING_TIME


# ============================================================================
# TEST VOICE HANDLING
# ============================================================================


@pytest.mark.asyncio
async def test_handle_voice_success(mock_message, mock_audio_pipeline):
    """Test voice message processing with successful transcription."""
    # Create mock voice message
    mock_voice = Mock(spec=Voice)
    mock_voice.file_id = "test_file_id"
    mock_voice.duration = 5
    
    mock_message.voice = mock_voice
    mock_message.text = None
    
    # Mock bot file operations
    mock_file = Mock(spec=File)
    mock_file.file_path = "voice/file_123.oga"
    mock_message.bot.get_file = AsyncMock(return_value=mock_file)
    mock_message.bot.download_file = AsyncMock()
    
    status_msg = Mock()
    status_msg.edit_text = AsyncMock()
    status_msg.delete = AsyncMock()
    mock_message.answer = AsyncMock(return_value=status_msg)
    
    # Mock transcription result
    mock_audio_pipeline.process_voice_message.return_value = "Я хочу записаться к врачу"
    
    with patch("core.client.handlers.handle_message", new=AsyncMock()) as mock_handle:
        await handle_voice(mock_message)
        
        # Check that transcription was attempted
        assert mock_audio_pipeline.process_voice_message.called
        
        # Check that transcribed text was processed
        assert mock_handle.called


@pytest.mark.asyncio
async def test_handle_voice_transcription_failure(mock_message, mock_audio_pipeline, mock_notifier):
    """Test voice message handling when transcription fails."""
    # Create mock voice message
    mock_voice = Mock(spec=Voice)
    mock_voice.file_id = "test_file_id"
    mock_message.voice = mock_voice
    
    # Mock bot operations
    mock_file = Mock(spec=File)
    mock_file.file_path = "voice/file_123.oga"
    mock_message.bot.get_file = AsyncMock(return_value=mock_file)
    mock_message.bot.download_file = AsyncMock()
    
    status_msg = Mock()
    status_msg.edit_text = AsyncMock()
    mock_message.answer = AsyncMock(return_value=status_msg)
    
    # Mock transcription failure
    mock_audio_pipeline.process_voice_message.return_value = None
    
    await handle_voice(mock_message)
    
    # Should show error message
    assert status_msg.edit_text.called
    
    # Should notify admins
    assert mock_notifier.send_immediate_alert.called


# ============================================================================
# TEST INTENT CLASSIFICATION
# ============================================================================


@pytest.mark.asyncio
async def test_handle_schedule_inquiry(mock_message, mock_gemini_analyzer):
    """Test schedule inquiry classification and response."""
    # Mock classification as schedule inquiry
    mock_gemini_analyzer.classify_request.return_value = ClassificationResult(
        request_type=RequestType.SCHEDULE_INQUIRY,
        urgency=UrgencyLevel.LOW,
        confidence=0.9,
    )
    
    user_id = mock_message.from_user.id
    storage = get_storage()
    await storage.update(user_id, state=ConversationState.START)
    
    mock_message.text = "Какое расписание у врачей?"
    await handle_message(mock_message)
    
    # Should show schedule information
    assert mock_message.answer.called
    response_text = mock_message.answer.call_args[0][0]
    assert "Расписание" in response_text or "расписание" in response_text


@pytest.mark.asyncio
async def test_handle_complaint_escalation(mock_message, mock_gemini_analyzer, mock_notifier):
    """Test complaint classification and admin notification."""
    # Mock classification as complaint
    mock_gemini_analyzer.classify_request.return_value = ClassificationResult(
        request_type=RequestType.COMPLAINT,
        urgency=UrgencyLevel.HIGH,
        confidence=0.95,
    )
    
    user_id = mock_message.from_user.id
    storage = get_storage()
    await storage.update(user_id, state=ConversationState.START)
    
    mock_message.text = "Я недоволен обслуживанием!"
    await handle_message(mock_message)
    
    # Should acknowledge complaint
    assert mock_message.answer.called
    
    # Should notify admins
    assert mock_notifier.send_immediate_alert.called
    call_args = mock_notifier.send_immediate_alert.call_args[0][0]
    assert call_args.event_type == "complaint_received"


# ============================================================================
# TEST VALIDATION
# ============================================================================


@pytest.mark.asyncio
async def test_invalid_name_validation(mock_message):
    """Test name validation rejects invalid inputs."""
    user_id = mock_message.from_user.id
    storage = get_storage()
    
    await storage.update(user_id, state=ConversationState.WAITING_NAME)
    
    # Invalid name (too short)
    mock_message.text = "A"
    await handle_message(mock_message)
    
    # Should show error and remain in same state
    context = await storage.load(user_id)
    assert context.current_state == ConversationState.WAITING_NAME
    assert mock_message.answer.called


@pytest.mark.asyncio
async def test_invalid_phone_validation(mock_message):
    """Test phone validation rejects invalid inputs."""
    user_id = mock_message.from_user.id
    storage = get_storage()
    
    await storage.update(
        user_id,
        state=ConversationState.WAITING_PHONE,
        collected_info=CollectedInfo(name="Иван"),
    )
    
    # Invalid phone
    mock_message.text = "123"
    await handle_message(mock_message)
    
    # Should show error and remain in same state
    context = await storage.load(user_id)
    assert context.current_state == ConversationState.WAITING_PHONE


@pytest.mark.asyncio
async def test_past_date_validation(mock_message):
    """Test date validation rejects past dates."""
    user_id = mock_message.from_user.id
    storage = get_storage()
    
    await storage.update(
        user_id,
        state=ConversationState.WAITING_DATE,
        collected_info=CollectedInfo(
            name="Иван",
            phone="+77771234567",
            doctor_id=1,
            doctor_name="Доктор Иванов",
        ),
    )
    
    # Past date
    past_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    mock_message.text = past_date
    await handle_message(mock_message)
    
    # Should show error
    assert mock_message.answer.called
    error_msg = mock_message.answer.call_args[0][0]
    assert "прошедшую" in error_msg.lower() or "past" in error_msg.lower()


# ============================================================================
# TEST FALLBACK MODES
# ============================================================================


@pytest.mark.asyncio
async def test_gemini_failure_fallback(mock_message, mock_gemini_analyzer, mock_notifier):
    """Test fallback when Gemini service fails."""
    # Mock Gemini failure
    mock_gemini_analyzer.classify_request.side_effect = Exception("API Error")
    
    user_id = mock_message.from_user.id
    storage = get_storage()
    await storage.update(user_id, state=ConversationState.START)
    
    mock_message.text = "Хочу записаться"
    await handle_message(mock_message)
    
    # Should handle gracefully and start booking flow
    assert mock_message.answer.called
    
    # Context should progress (fallback to booking flow)
    context = await storage.load(user_id)
    assert context is not None


@pytest.mark.asyncio
async def test_sheets_failure_fallback(mock_message, mock_sheets_manager, mock_notifier):
    """Test fallback when Sheets service fails."""
    # Mock Sheets failure
    mock_sheets_manager.read_specialists.side_effect = Exception("Sheets API Error")
    
    user_id = mock_message.from_user.id
    storage = get_storage()
    
    await storage.update(
        user_id,
        state=ConversationState.WAITING_DOCTOR_CHOICE,
        collected_info=CollectedInfo(name="Иван", phone="+77771234567"),
    )
    
    mock_message.text = "Любой врач"
    await handle_message(mock_message)
    
    # Should inform user and notify admins
    assert mock_message.answer.called
    assert mock_notifier.send_immediate_alert.called


@pytest.mark.asyncio
async def test_booking_creation_failure_notifies_admins(mock_message, mock_sheets_manager, mock_notifier):
    """Test that booking creation failure notifies admins."""
    # Mock booking creation failure
    mock_sheets_manager.add_booking.side_effect = Exception("Database error")
    
    user_id = mock_message.from_user.id
    storage = get_storage()
    
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    context = await storage.update(
        user_id,
        state=ConversationState.CONFIRM_BOOKING,
        collected_info=CollectedInfo(
            name="Иван Иванов",
            phone="+77771234567",
            doctor_id=1,
            doctor_name="Доктор Иванов",
            booking_date=tomorrow.strftime("%Y-%m-%d"),
            booking_time="14:30",
        ),
    )
    
    success = await create_booking(mock_message, context)
    
    # Should fail gracefully
    assert not success
    
    # Should notify admins
    assert mock_notifier.send_immediate_alert.called


# ============================================================================
# TEST HELPER FUNCTIONS
# ============================================================================


@pytest.mark.asyncio
async def test_check_booking_conflict(mock_sheets_manager):
    """Test booking conflict detection."""
    # Set up existing booking
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    existing_booking = BookingDTO(
        id=1,
        specialist_id=1,
        client_name="Existing",
        booking_datetime=tomorrow.replace(hour=14, minute=30, second=0, microsecond=0),
        duration_minutes=60,
        status="confirmed",
    )
    mock_sheets_manager.read_bookings.return_value = [existing_booking]
    
    # Check conflict
    conflict = await check_booking_conflict(
        doctor_id=1,
        date_str=tomorrow.strftime("%Y-%m-%d"),
        time_str="14:30",
        sheets_manager=mock_sheets_manager,
    )
    
    assert conflict is True
    
    # Check non-conflict
    no_conflict = await check_booking_conflict(
        doctor_id=1,
        date_str=tomorrow.strftime("%Y-%m-%d"),
        time_str="10:00",
        sheets_manager=mock_sheets_manager,
    )
    
    assert no_conflict is False


@pytest.mark.asyncio
async def test_suggest_alternative_times(mock_sheets_manager):
    """Test alternative time suggestion."""
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    existing_booking = BookingDTO(
        id=1,
        specialist_id=1,
        client_name="Existing",
        booking_datetime=tomorrow.replace(hour=14, minute=0, second=0, microsecond=0),
        duration_minutes=60,
        status="confirmed",
    )
    mock_sheets_manager.read_bookings.return_value = [existing_booking]
    
    alternatives = await suggest_alternative_times(
        doctor_id=1,
        date_str=tomorrow.strftime("%Y-%m-%d"),
        sheets_manager=mock_sheets_manager,
    )
    
    # Should suggest times
    assert len(alternatives) > 0
    
    # Should not include 14:00 (booked)
    assert "14:00" not in alternatives


# ============================================================================
# TEST CANCELLATION FLOW
# ============================================================================


@pytest.mark.asyncio
async def test_booking_cancellation_via_callback(mock_callback_query):
    """Test booking cancellation via 'No' button."""
    user_id = mock_callback_query.from_user.id
    storage = get_storage()
    
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    await storage.update(
        user_id,
        state=ConversationState.CONFIRM_BOOKING,
        collected_info=CollectedInfo(
            name="Иван",
            phone="+77771234567",
            doctor_id=1,
            doctor_name="Доктор Иванов",
            booking_date=tomorrow.strftime("%Y-%m-%d"),
            booking_time="14:30",
        ),
    )
    
    mock_callback_query.data = "confirm_booking_no"
    await handle_booking_no(mock_callback_query)
    
    # Should go back to date selection
    context = await storage.load(user_id)
    assert context.current_state == ConversationState.WAITING_DATE
