"""Client dialog handlers for text and voice interactions."""

import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from core.conversation import (
    get_storage,
    ConversationState,
    ConversationContext,
    CollectedInfo,
)
from core.i18n import get_text, detect_language
from models import BookingDTO, SpecialistDTO, ScheduleDTO
from services.gemini.analyzer import GeminiAnalyzer, RequestType
from services.audio.pipeline import AudioPipeline
from services.repositories import (
    SpecialistRepository,
    ScheduleRepository,
    BookingRepository,
)
from services.validators import validate_phone, validate_name, validate_date_format, validate_time_format
from integrations.google.sheets_manager import GoogleSheetsManager
from services.notifications.notifier import Notifier, NotificationEvent
from settings import settings

logger = logging.getLogger(__name__)

# Create router for client interactions
client_router = Router()

# Global instances (to be initialized in main application)
_gemini_analyzer: Optional[GeminiAnalyzer] = None
_audio_pipeline: Optional[AudioPipeline] = None
_sheets_manager: Optional[GoogleSheetsManager] = None
_notifier: Optional[Notifier] = None


def initialize_services(
    gemini_analyzer: Optional[GeminiAnalyzer] = None,
    audio_pipeline: Optional[AudioPipeline] = None,
    sheets_manager: Optional[GoogleSheetsManager] = None,
    notifier: Optional[Notifier] = None,
) -> None:
    """Initialize service dependencies for handlers."""
    global _gemini_analyzer, _audio_pipeline, _sheets_manager, _notifier
    _gemini_analyzer = gemini_analyzer
    _audio_pipeline = audio_pipeline
    _sheets_manager = sheets_manager
    _notifier = notifier


def get_gemini_analyzer() -> Optional[GeminiAnalyzer]:
    """Get Gemini analyzer instance."""
    return _gemini_analyzer


def get_audio_pipeline() -> Optional[AudioPipeline]:
    """Get audio pipeline instance."""
    return _audio_pipeline


def get_sheets_manager() -> Optional[GoogleSheetsManager]:
    """Get sheets manager instance."""
    return _sheets_manager


def get_notifier() -> Optional[Notifier]:
    """Get notifier instance."""
    return _notifier


# ============================================================================
# COMMAND HANDLERS
# ============================================================================


@client_router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Handle /start command - greet user and start booking flow."""
    user_id = message.from_user.id
    language = detect_language(message.from_user.language_code)
    
    # Initialize conversation context
    storage = get_storage()
    await storage.update(
        user_id,
        state=ConversationState.START,
        collected_info=CollectedInfo(),
    )
    
    # Send greeting
    greeting = get_text("greetings.welcome", language)
    await message.answer(greeting)
    
    # Ask for name to start booking
    await start_booking_flow(message, language)


async def start_booking_flow(message: Message, language: str) -> None:
    """Start the booking flow by asking for name."""
    user_id = message.from_user.id
    storage = get_storage()
    
    # Transition to waiting for name
    await storage.update(user_id, state=ConversationState.WAITING_NAME)
    
    prompt = get_text("prompts.enter_name", language)
    await message.answer(prompt)


# ============================================================================
# TEXT MESSAGE HANDLER
# ============================================================================


@client_router.message(F.text)
async def handle_message(message: Message) -> None:
    """Handle text messages with FSM-driven conversation flow."""
    user_id = message.from_user.id
    text = message.text
    language = detect_language(message.from_user.language_code)
    
    # Get or create conversation context
    storage = get_storage()
    context = await storage.load(user_id)
    if not context:
        context = await storage.update(user_id, state=ConversationState.START)
    
    # Update language
    context.language = language
    await storage.save(context)
    
    logger.info(f"Handling message from user {user_id} in state {context.current_state}")
    
    # Route based on current state
    state = context.current_state
    
    if state == ConversationState.START:
        await handle_start_state(message, context)
    elif state == ConversationState.WAITING_NAME:
        await handle_name_input(message, context)
    elif state == ConversationState.WAITING_PHONE:
        await handle_phone_input(message, context)
    elif state == ConversationState.WAITING_DOCTOR_CHOICE:
        await handle_doctor_choice(message, context)
    elif state == ConversationState.WAITING_DATE:
        await handle_date_input(message, context)
    elif state == ConversationState.WAITING_TIME:
        await handle_time_input(message, context)
    elif state == ConversationState.CONFIRM_BOOKING:
        await handle_booking_confirmation(message, context)
    elif state == ConversationState.DONE:
        # Start new conversation
        await cmd_start(message)
    else:
        # Unknown state, restart
        logger.warning(f"Unknown state {state} for user {user_id}, restarting")
        await cmd_start(message)


async def handle_start_state(message: Message, context: ConversationContext) -> None:
    """Handle messages in START state - classify intent."""
    text = message.text
    language = context.language
    user_id = message.from_user.id
    
    # Try to classify the request using Gemini
    analyzer = get_gemini_analyzer()
    if analyzer:
        try:
            classification = analyzer.classify_request(text, language)
            logger.info(f"Classified request as {classification.request_type}")
            
            # Route based on classification
            if classification.request_type == RequestType.APPOINTMENT_BOOKING:
                await start_booking_flow(message, language)
            elif classification.request_type == RequestType.SCHEDULE_INQUIRY:
                await handle_schedule_inquiry(message, context)
            elif classification.request_type == RequestType.SPECIALIST_INQUIRY:
                await handle_specialist_inquiry(message, context)
            elif classification.request_type == RequestType.COMPLAINT:
                await handle_complaint(message, context, text)
            else:
                # Generate response using Gemini
                response = analyzer.generate_response(text, language=language)
                await message.answer(response.text)
                if response.is_fallback:
                    await notify_admins_for_manual_followup(user_id, text, language)
        except Exception as e:
            logger.error(f"Error classifying request: {e}")
            await handle_gemini_failure(message, context, text)
    else:
        # Gemini not available, assume booking intent
        logger.warning("Gemini analyzer not available, assuming booking intent")
        await start_booking_flow(message, language)


async def handle_name_input(message: Message, context: ConversationContext) -> None:
    """Handle name input during booking flow."""
    text = message.text
    language = context.language
    user_id = message.from_user.id
    storage = get_storage()
    
    # Validate name
    is_valid, error_msg = validate_name(text)
    if not is_valid:
        error_text = get_text("errors.invalid_input", language)
        await message.answer(f"{error_text} {error_msg}")
        return
    
    # Save name and move to phone
    context.collected_info.name = text.strip()
    await storage.update(
        user_id,
        state=ConversationState.WAITING_PHONE,
        collected_info=context.collected_info,
    )
    
    prompt = get_text("prompts.enter_phone", language)
    await message.answer(prompt)


async def handle_phone_input(message: Message, context: ConversationContext) -> None:
    """Handle phone input during booking flow."""
    text = message.text
    language = context.language
    user_id = message.from_user.id
    storage = get_storage()
    
    # Validate phone
    is_valid, error_msg = validate_phone(text)
    if not is_valid:
        error_text = get_text("errors.invalid_input", language)
        await message.answer(f"{error_text} {error_msg}")
        return
    
    # Save phone and move to doctor choice
    context.collected_info.phone = text.strip()
    await storage.update(
        user_id,
        state=ConversationState.WAITING_DOCTOR_CHOICE,
        collected_info=context.collected_info,
    )
    
    # Show available specialists
    await show_specialists(message, context)


async def show_specialists(message: Message, context: ConversationContext) -> None:
    """Display available specialists with inline keyboard."""
    language = context.language
    
    # Get specialists from Sheets
    sheets_manager = get_sheets_manager()
    if not sheets_manager:
        await handle_sheets_failure(message, context)
        return
    
    try:
        specialists = sheets_manager.read_specialists()
        active_specialists = [s for s in specialists if s.is_active]
        
        if not active_specialists:
            error_msg = get_text("errors.specialist_not_found", language)
            await message.answer(error_msg)
            await notify_admins_for_manual_followup(
                message.from_user.id,
                "No specialists available",
                language
            )
            return
        
        # Build keyboard with specialist options
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{s.name} - {s.specialization}",
                    callback_data=f"doctor_{s.id}"
                )]
                for s in active_specialists
            ]
        )
        
        prompt = get_text("prompts.select_specialist", language)
        await message.answer(prompt, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error fetching specialists: {e}")
        await handle_sheets_failure(message, context)


async def handle_doctor_choice(message: Message, context: ConversationContext) -> None:
    """Handle doctor choice input (text or callback will be handled separately)."""
    # For text input, try to match by name
    text = message.text
    language = context.language
    user_id = message.from_user.id
    storage = get_storage()
    
    sheets_manager = get_sheets_manager()
    if not sheets_manager:
        await handle_sheets_failure(message, context)
        return
    
    try:
        specialists = sheets_manager.read_specialists()
        
        # Try to find specialist by name (case-insensitive)
        matching_specialist = None
        for s in specialists:
            if s.is_active and text.lower() in s.name.lower():
                matching_specialist = s
                break
        
        if not matching_specialist:
            error_msg = get_text("errors.specialist_not_found", language)
            await message.answer(error_msg)
            # Show specialists again
            await show_specialists(message, context)
            return
        
        # Save doctor choice and move to date
        context.collected_info.doctor_id = matching_specialist.id
        context.collected_info.doctor_name = matching_specialist.name
        await storage.update(
            user_id,
            state=ConversationState.WAITING_DATE,
            collected_info=context.collected_info,
        )
        
        prompt = get_text("prompts.select_date", language)
        await message.answer(f"{prompt}\nФормат: YYYY-MM-DD (например, 2024-12-25)")
        
    except Exception as e:
        logger.error(f"Error processing doctor choice: {e}")
        await handle_sheets_failure(message, context)


@client_router.callback_query(F.data.startswith("doctor_"))
async def handle_doctor_callback(callback: types.CallbackQuery) -> None:
    """Handle doctor selection via inline keyboard callback."""
    user_id = callback.from_user.id
    language = detect_language(callback.from_user.language_code)
    storage = get_storage()
    
    context = await storage.load(user_id)
    if not context:
        await callback.answer(get_text("fallback.session_expired", language))
        return
    
    # Extract doctor ID from callback data
    doctor_id = int(callback.data.split("_")[1])
    
    # Get doctor details
    sheets_manager = get_sheets_manager()
    if not sheets_manager:
        await callback.answer(get_text("errors.sheets_error", language))
        return
    
    try:
        specialists = sheets_manager.read_specialists()
        doctor = next((s for s in specialists if s.id == doctor_id), None)
        
        if not doctor:
            await callback.answer(get_text("errors.specialist_not_found", language))
            return
        
        # Save doctor choice
        context.collected_info.doctor_id = doctor.id
        context.collected_info.doctor_name = doctor.name
        await storage.update(
            user_id,
            state=ConversationState.WAITING_DATE,
            collected_info=context.collected_info,
        )
        
        await callback.answer()
        prompt = get_text("prompts.select_date", language)
        await callback.message.answer(f"{prompt}\nФормат: YYYY-MM-DD (например, 2024-12-25)")
        
    except Exception as e:
        logger.error(f"Error in doctor callback: {e}")
        await callback.answer(get_text("errors.general", language))


async def handle_date_input(message: Message, context: ConversationContext) -> None:
    """Handle date input during booking flow."""
    text = message.text
    language = context.language
    user_id = message.from_user.id
    storage = get_storage()
    
    # Validate date format
    is_valid, error_msg = validate_date_format(text)
    if not is_valid:
        error_text = get_text("errors.invalid_input", language)
        await message.answer(f"{error_text} {error_msg}")
        return
    
    # Check if date is in the past
    try:
        date_obj = datetime.strptime(text, "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        
        if date_obj < today:
            error_msg = get_text("errors.past_date", language)
            await message.answer(error_msg)
            return
        
        # Check if date is too far in the future (e.g., 90 days)
        max_days = 90
        if (date_obj - today).days > max_days:
            error_msg = get_text("errors.booking_too_far", language).format(days=max_days)
            await message.answer(error_msg)
            return
        
        # Save date and move to time
        context.collected_info.booking_date = text
        await storage.update(
            user_id,
            state=ConversationState.WAITING_TIME,
            collected_info=context.collected_info,
        )
        
        prompt = get_text("prompts.select_time", language)
        await message.answer(f"{prompt}\nФормат: HH:MM (например, 14:30)")
        
    except ValueError:
        error_text = get_text("errors.invalid_input", language)
        await message.answer(error_text)


async def handle_time_input(message: Message, context: ConversationContext) -> None:
    """Handle time input during booking flow."""
    text = message.text
    language = context.language
    user_id = message.from_user.id
    storage = get_storage()
    
    # Validate time format
    is_valid, error_msg = validate_time_format(text)
    if not is_valid:
        error_text = get_text("errors.invalid_input", language)
        await message.answer(f"{error_text} {error_msg}")
        return
    
    # Check for scheduling conflicts
    sheets_manager = get_sheets_manager()
    if not sheets_manager:
        await handle_sheets_failure(message, context)
        return
    
    try:
        # Check if slot is available
        conflict = await check_booking_conflict(
            context.collected_info.doctor_id,
            context.collected_info.booking_date,
            text,
            sheets_manager
        )
        
        if conflict:
            error_msg = get_text("errors.time_slot_unavailable", language)
            await message.answer(error_msg)
            
            # Suggest alternative times
            alternatives = await suggest_alternative_times(
                context.collected_info.doctor_id,
                context.collected_info.booking_date,
                sheets_manager
            )
            
            if alternatives:
                alt_text = "Доступные варианты:\n" + "\n".join([f"- {t}" for t in alternatives[:5]])
                await message.answer(alt_text)
            return
        
        # Save time and move to confirmation
        context.collected_info.booking_time = text
        await storage.update(
            user_id,
            state=ConversationState.CONFIRM_BOOKING,
            collected_info=context.collected_info,
        )
        
        # Show confirmation
        await show_booking_confirmation(message, context)
        
    except Exception as e:
        logger.error(f"Error checking time slot: {e}")
        await handle_sheets_failure(message, context)


async def show_booking_confirmation(message: Message, context: ConversationContext) -> None:
    """Show booking confirmation with Yes/No buttons."""
    language = context.language
    info = context.collected_info
    
    confirmation_text = get_text("prompts.confirm_booking", language)
    details = f"""
{confirmation_text}

{get_text("booking.client_name", language).format(name=info.name)}
{get_text("booking.specialist", language).format(name=info.doctor_name)}
{get_text("booking.date", language).format(date=info.booking_date)}
{get_text("booking.time", language).format(time=info.booking_time)}
{get_text("booking.duration", language).format(duration=info.booking_duration)}
"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("common.yes", language),
                    callback_data="confirm_booking_yes"
                ),
                InlineKeyboardButton(
                    text=get_text("common.no", language),
                    callback_data="confirm_booking_no"
                )
            ]
        ]
    )
    
    await message.answer(details, reply_markup=keyboard)


@client_router.callback_query(F.data == "confirm_booking_yes")
async def handle_booking_yes(callback: types.CallbackQuery) -> None:
    """Handle booking confirmation YES."""
    user_id = callback.from_user.id
    language = detect_language(callback.from_user.language_code)
    storage = get_storage()
    
    context = await storage.load(user_id)
    if not context or context.current_state != ConversationState.CONFIRM_BOOKING:
        await callback.answer(get_text("fallback.session_expired", language))
        return
    
    await callback.answer()
    
    # Create the booking
    success = await create_booking(callback.message, context)
    
    if success:
        # Reset conversation
        await storage.update(user_id, state=ConversationState.DONE)
    else:
        # Stay in confirmation state for retry
        pass


@client_router.callback_query(F.data == "confirm_booking_no")
async def handle_booking_no(callback: types.CallbackQuery) -> None:
    """Handle booking confirmation NO."""
    user_id = callback.from_user.id
    language = detect_language(callback.from_user.language_code)
    storage = get_storage()
    
    await callback.answer()
    
    # Go back to date selection
    await storage.update(user_id, state=ConversationState.WAITING_DATE)
    
    prompt = get_text("prompts.select_date", language)
    await callback.message.answer(f"{prompt}\nФормат: YYYY-MM-DD")


async def handle_booking_confirmation(message: Message, context: ConversationContext) -> None:
    """Handle text responses during booking confirmation."""
    text = message.text.lower()
    language = context.language
    
    # Simple yes/no detection
    if text in ["да", "yes", "иә", "ок", "ok"]:
        await create_booking(message, context)
    elif text in ["нет", "no", "жоқ"]:
        # Go back to date selection
        storage = get_storage()
        await storage.update(message.from_user.id, state=ConversationState.WAITING_DATE)
        
        prompt = get_text("prompts.select_date", language)
        await message.answer(f"{prompt}\nФормат: YYYY-MM-DD")
    else:
        # Ask again
        await show_booking_confirmation(message, context)


async def create_booking(message: Message, context: ConversationContext) -> bool:
    """Create booking in Sheets and trigger notifications."""
    language = context.language
    info = context.collected_info
    user_id = message.from_user.id
    storage = get_storage()
    
    sheets_manager = get_sheets_manager()
    if not sheets_manager:
        await handle_sheets_failure(message, context)
        return False
    
    try:
        # Combine date and time into datetime
        booking_datetime = datetime.strptime(
            f"{info.booking_date} {info.booking_time}",
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc)
        
        # Create booking DTO
        booking = BookingDTO(
            specialist_id=info.doctor_id,
            client_name=info.name,
            booking_datetime=booking_datetime,
            duration_minutes=info.booking_duration,
            notes=info.notes,
            status="confirmed"
        )
        
        # Save to Sheets
        created_booking = sheets_manager.add_booking(booking)
        logger.info(f"Booking created: {created_booking.id}")
        
        # Send confirmation to client
        confirmation_msg = get_text("confirmations.booking_created", language).format(
            specialist=info.doctor_name,
            date=info.booking_date,
            time=info.booking_time,
            duration=info.booking_duration
        )
        await message.answer(confirmation_msg)
        
        # Notify admins via notifier
        notifier = get_notifier()
        if notifier:
            try:
                # Get admin IDs from settings
                for admin_id in settings.admin_ids:
                    event = NotificationEvent(
                        event_type="booking_created",
                        recipient_id=admin_id,
                        recipient_type="admin",
                        language=language,
                        data={
                            "client_name": info.name,
                            "specialist_name": info.doctor_name,
                            "booking_date": info.booking_date,
                            "booking_time": info.booking_time,
                        },
                        priority="urgent",
                        related_booking_id=created_booking.id,
                    )
                    await notifier.send_immediate_alert(event)
            except Exception as e:
                logger.error(f"Error sending admin notifications: {e}")
                # Don't fail the booking if notifications fail
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        await handle_sheets_failure(message, context)
        return False


async def check_booking_conflict(
    doctor_id: int,
    date_str: str,
    time_str: str,
    sheets_manager: GoogleSheetsManager
) -> bool:
    """Check if the requested time slot conflicts with existing bookings."""
    try:
        bookings = sheets_manager.read_bookings()
        
        # Parse requested datetime
        requested_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        
        # Check for conflicts
        for booking in bookings:
            if booking.specialist_id != doctor_id:
                continue
            
            if booking.status == "cancelled":
                continue
            
            # Check if bookings overlap
            booking_start = booking.booking_datetime.replace(tzinfo=None)
            booking_end = booking_start + timedelta(minutes=booking.duration_minutes)
            requested_end = requested_dt + timedelta(minutes=60)  # Default duration
            
            # Check overlap
            if (requested_dt < booking_end and requested_end > booking_start):
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking booking conflict: {e}")
        return False


async def suggest_alternative_times(
    doctor_id: int,
    date_str: str,
    sheets_manager: GoogleSheetsManager
) -> List[str]:
    """Suggest alternative available time slots."""
    try:
        bookings = sheets_manager.read_bookings()
        
        # Get bookings for this doctor on this date
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        busy_times = []
        
        for booking in bookings:
            if booking.specialist_id != doctor_id:
                continue
            
            if booking.status == "cancelled":
                continue
            
            booking_date = booking.booking_datetime.date()
            if booking_date == date_obj:
                start_time = booking.booking_datetime.time()
                busy_times.append(start_time)
        
        # Generate available times (9:00 to 18:00, hourly)
        available_times = []
        for hour in range(9, 18):
            time_obj = datetime.strptime(f"{hour:02d}:00", "%H:%M").time()
            if time_obj not in busy_times:
                available_times.append(f"{hour:02d}:00")
        
        return available_times
        
    except Exception as e:
        logger.error(f"Error suggesting alternative times: {e}")
        return []


# ============================================================================
# VOICE MESSAGE HANDLER
# ============================================================================


@client_router.message(F.voice)
async def handle_voice(message: Message) -> None:
    """Handle voice messages - download, transcribe, and process as text."""
    user_id = message.from_user.id
    language = detect_language(message.from_user.language_code)
    
    # Get or create conversation context
    storage = get_storage()
    context = await storage.load(user_id)
    if not context:
        context = await storage.update(user_id, state=ConversationState.START)
    
    context.language = language
    await storage.save(context)
    
    # Check if audio pipeline is available
    audio_pipeline = get_audio_pipeline()
    if not audio_pipeline or not audio_pipeline.is_available():
        error_msg = get_text("audio.transcription_error", language)
        await message.answer(error_msg)
        # Ask user to send text instead
        return
    
    processing_msg = get_text("audio.processing", language)
    status_message = await message.answer(processing_msg)
    
    try:
        # Download voice message
        voice = message.voice
        
        # Create temp file for download
        with tempfile.NamedTemporaryFile(delete=False, suffix=".oga") as tmp_file:
            audio_path = tmp_file.name
        
        # Download file
        file = await message.bot.get_file(voice.file_id)
        await message.bot.download_file(file.file_path, audio_path)
        
        logger.info(f"Downloaded voice message: {audio_path}")
        
        # Transcribe audio
        transcript = audio_pipeline.process_voice_message(
            audio_path,
            language=language,
            cleanup=True
        )
        
        # Clean up downloaded file
        try:
            os.unlink(audio_path)
        except Exception:
            pass
        
        if not transcript:
            error_msg = get_text("audio.transcription_error", language)
            await status_message.edit_text(error_msg)
            
            # Notify admins for manual follow-up
            await notify_admins_for_manual_followup(
                user_id,
                "Voice transcription failed",
                language
            )
            return
        
        logger.info(f"Transcribed voice: {transcript[:100]}...")
        
        # Delete processing message
        await status_message.delete()
        
        # Create a fake text message and process it
        fake_message = message
        fake_message.text = transcript
        await handle_message(fake_message)
        
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        error_msg = get_text("audio.transcription_error", language)
        await status_message.edit_text(error_msg)
        
        # Notify admins for manual follow-up
        await notify_admins_for_manual_followup(
            user_id,
            f"Voice processing error: {str(e)}",
            language
        )


# ============================================================================
# HELPER HANDLERS
# ============================================================================


async def handle_schedule_inquiry(message: Message, context: ConversationContext) -> None:
    """Handle schedule inquiry requests."""
    language = context.language
    
    sheets_manager = get_sheets_manager()
    if not sheets_manager:
        await handle_sheets_failure(message, context)
        return
    
    try:
        specialists = sheets_manager.read_specialists()
        schedules = sheets_manager.read_schedule()
        
        if not specialists:
            await message.answer(get_text("fallback.no_data", language))
            return
        
        # Build schedule response
        response_lines = ["📅 Расписание специалистов:\n"]
        
        for specialist in specialists:
            if not specialist.is_active:
                continue
            
            specialist_schedules = [s for s in schedules if s.specialist_id == specialist.id]
            
            response_lines.append(f"\n👨‍⚕️ {specialist.name} ({specialist.specialization})")
            
            if specialist_schedules:
                for sched in specialist_schedules:
                    day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][sched.day_of_week]
                    response_lines.append(f"  {day_name}: {sched.start_time} - {sched.end_time}")
            else:
                response_lines.append("  Расписание не указано")
        
        await message.answer("\n".join(response_lines))
        
    except Exception as e:
        logger.error(f"Error handling schedule inquiry: {e}")
        await handle_sheets_failure(message, context)


async def handle_specialist_inquiry(message: Message, context: ConversationContext) -> None:
    """Handle specialist inquiry requests."""
    language = context.language
    
    sheets_manager = get_sheets_manager()
    if not sheets_manager:
        await handle_sheets_failure(message, context)
        return
    
    try:
        specialists = sheets_manager.read_specialists()
        
        if not specialists:
            await message.answer(get_text("fallback.no_data", language))
            return
        
        # Build specialists list
        response_lines = ["👨‍⚕️ Наши специалисты:\n"]
        
        for specialist in specialists:
            if not specialist.is_active:
                continue
            
            response_lines.append(f"\n• {specialist.name}")
            response_lines.append(f"  Специализация: {specialist.specialization}")
            if specialist.phone:
                response_lines.append(f"  Телефон: {specialist.phone}")
        
        await message.answer("\n".join(response_lines))
        
    except Exception as e:
        logger.error(f"Error handling specialist inquiry: {e}")
        await handle_sheets_failure(message, context)


async def handle_complaint(message: Message, context: ConversationContext, complaint_text: str) -> None:
    """Handle complaint - summarize with Gemini and notify admins."""
    language = context.language
    user_id = message.from_user.id
    
    analyzer = get_gemini_analyzer()
    if analyzer:
        try:
            # Summarize complaint
            summary = analyzer.summarize_complaint(complaint_text, language)
            summary_text = summary.text
        except Exception as e:
            logger.error(f"Error summarizing complaint: {e}")
            summary_text = complaint_text[:200]  # Fallback to truncated text
    else:
        summary_text = complaint_text[:200]
    
    # Acknowledge complaint
    acknowledgment = "Спасибо за ваше сообщение. Мы передали его администратору для рассмотрения."
    await message.answer(acknowledgment)
    
    # Notify admins
    notifier = get_notifier()
    if notifier:
        try:
            for admin_id in settings.admin_ids:
                event = NotificationEvent(
                    event_type="complaint_received",
                    recipient_id=admin_id,
                    recipient_type="admin",
                    language=language,
                    data={
                        "client_name": context.collected_info.name or "Неизвестный",
                        "complaint_subject": summary_text,
                        "severity": "high",
                    },
                    priority="immediate",
                )
                await notifier.send_immediate_alert(event)
        except Exception as e:
            logger.error(f"Error notifying admins of complaint: {e}")


async def handle_gemini_failure(message: Message, context: ConversationContext, text: str) -> None:
    """Handle Gemini service failure - fallback to manual mode."""
    language = context.language
    
    # Inform client
    fallback_msg = get_text("gemini.fallback_response", language)
    await message.answer(fallback_msg)
    
    # Notify admins
    await notify_admins_for_manual_followup(message.from_user.id, text, language)


async def handle_sheets_failure(message: Message, context: ConversationContext) -> None:
    """Handle Sheets service failure - fallback to manual mode."""
    language = context.language
    
    # Inform client
    fallback_msg = get_text("gemini.fallback_response", language)
    error_msg = get_text("errors.sheets_error", language)
    await message.answer(f"{error_msg}\n\n{fallback_msg}")
    
    # Notify admins
    user_id = message.from_user.id
    info = context.collected_info
    
    details = f"""
Пользователь: {user_id}
Имя: {info.name or 'N/A'}
Телефон: {info.phone or 'N/A'}
Врач: {info.doctor_name or 'N/A'}
Дата: {info.booking_date or 'N/A'}
Время: {info.booking_time or 'N/A'}
"""
    
    await notify_admins_for_manual_followup(
        user_id,
        f"Ошибка Sheets - требуется ручная обработка:\n{details}",
        language
    )


async def notify_admins_for_manual_followup(
    user_id: int,
    message: str,
    language: str
) -> None:
    """Notify admins for manual follow-up when automated systems fail."""
    notifier = get_notifier()
    if not notifier:
        logger.warning("Notifier not available, cannot notify admins")
        return
    
    try:
        for admin_id in settings.admin_ids:
            event = NotificationEvent(
                event_type="manual_followup_required",
                recipient_id=admin_id,
                recipient_type="admin",
                language=language,
                data={
                    "user_id": user_id,
                    "message": message,
                },
                priority="immediate",
            )
            await notifier.send_immediate_alert(event)
            logger.info(f"Notified admin {admin_id} for manual follow-up")
    except Exception as e:
        logger.error(f"Error notifying admins: {e}")
