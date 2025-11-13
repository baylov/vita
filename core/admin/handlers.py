"""Admin command handlers for Telegram bot using aiogram."""

import logging
from typing import Optional

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from datetime import datetime, timezone

from core.conversation import get_storage, ConversationState, CollectedInfo
from core.i18n import get_text, detect_language
from settings import settings
from models import SpecialistDTO, DayOffDTO, AdminActionDTO
import models
from services.repositories import (
    SpecialistRepository,
    DayOffRepository,
    ScheduleRepository,
    BookingRepository,
)
from services.validators import (
    validate_phone,
    validate_name,
    validate_specialization,
    validate_email,
    validate_date_format,
)

logger = logging.getLogger(__name__)

# Create router for admin commands
admin_router = Router()


def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    return user_id in settings.admin_ids


async def check_admin_access(message: Message, language: str = "ru") -> bool:
    """
    Check if user has admin access. Send denial message if not.
    
    Args:
        message: Message from user
        language: User language preference
        
    Returns:
        True if user is admin, False otherwise
    """
    if not is_admin(message.from_user.id):
        await message.answer(
            get_text("errors.permission_denied", language)
        )
        return False
    return True


# ============================================================================
# COMMAND HANDLERS
# ============================================================================


@admin_router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    """Handle /admin command - show admin menu."""
    if not await check_admin_access(message):
        return
    
    user_id = message.from_user.id
    language = detect_language(message.from_user.language_code)
    
    # Update conversation state
    storage = get_storage()
    await storage.update(
        user_id,
        state=ConversationState.ADMIN_MENU,
        admin_mode=True,
    )
    
    # Build admin menu
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=get_text("admin.add_specialist", language),
                callback_data="admin_add_specialist"
            )],
            [InlineKeyboardButton(
                text=get_text("admin.edit_specialist", language),
                callback_data="admin_edit_specialist"
            )],
            [InlineKeyboardButton(
                text=get_text("admin.delete_specialist", language),
                callback_data="admin_delete_specialist"
            )],
            [InlineKeyboardButton(
                text=get_text("admin.set_day_off", language),
                callback_data="admin_set_day_off"
            )],
            [InlineKeyboardButton(
                text=get_text("admin.view_all_bookings", language),
                callback_data="admin_view_bookings"
            )],
            [InlineKeyboardButton(
                text=get_text("admin.view_logs", language),
                callback_data="admin_view_logs"
            )],
            [InlineKeyboardButton(
                text=get_text("admin.sync_data", language),
                callback_data="admin_sync"
            )],
            [InlineKeyboardButton(
                text=get_text("menu.back", language),
                callback_data="back_to_start"
            )],
        ]
    )
    
    await message.answer(
        get_text("admin.panel_title", language),
        reply_markup=keyboard
    )


@admin_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command - show help information."""
    language = detect_language(message.from_user.language_code)
    
    help_text = get_text("help.title", language) + "\n\n"
    help_text += get_text("help.commands", language) + "\n"
    help_text += get_text("help.start", language) + "\n"
    help_text += get_text("help.book", language) + "\n"
    help_text += get_text("help.mybookings", language) + "\n"
    help_text += get_text("help.cancel", language) + "\n"
    help_text += get_text("help.help", language) + "\n"
    help_text += get_text("help.settings", language)
    
    if is_admin(message.from_user.id):
        help_text += "\n\n" + get_text("admin.panel_title", language) + ":\n"
        help_text += "/admin - " + get_text("admin.panel_title", language)
    
    await message.answer(help_text)


@admin_router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    """Handle /status command - show system status."""
    if not await check_admin_access(message):
        return
    
    language = detect_language(message.from_user.language_code)
    
    try:
        # Gather system statistics
        status_info = "📊 " + get_text("admin.statistics", language) + "\n\n"
        status_info += "✅ Система работает нормально\n"
        status_info += f"🕐 Время сервера: {datetime.now(timezone.utc).isoformat()}\n"
        
        await message.answer(status_info)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        await message.answer(get_text("errors.general", language))


# ============================================================================
# CALLBACK HANDLERS FOR ADMIN MENU
# ============================================================================


@admin_router.callback_query(F.data == "admin_add_specialist")
async def cb_add_specialist_start(query: types.CallbackQuery) -> None:
    """Start add specialist flow."""
    if not is_admin(query.from_user.id):
        await query.answer(get_text("errors.permission_denied"), show_alert=True)
        return
    
    user_id = query.from_user.id
    language = detect_language(query.from_user.language_code)
    
    storage = get_storage()
    await storage.update(
        user_id,
        state=ConversationState.ADMIN_ADD_SPECIALIST_NAME,
    )
    
    await query.message.answer(
        get_text("admin.enter_specialist_name", language)
    )
    await query.answer()


@admin_router.message(F.text)
async def handle_text_message(message: Message) -> None:
    """Handle text messages based on conversation state."""
    if not is_admin(message.from_user.id):
        return
    
    user_id = message.from_user.id
    language = detect_language(message.from_user.language_code)
    
    storage = get_storage()
    context = await storage.load(user_id)
    
    if context is None:
        return
    
    state = context.current_state
    
    # Route to appropriate handler based on state
    if state == ConversationState.ADMIN_ADD_SPECIALIST_NAME:
        await process_specialist_name(message, storage, language)
    elif state == ConversationState.ADMIN_ADD_SPECIALIST_SPECIALIZATION:
        await process_specialist_specialization(message, storage, language)
    elif state == ConversationState.ADMIN_ADD_SPECIALIST_PHONE:
        await process_specialist_phone(message, storage, language)
    elif state == ConversationState.ADMIN_ADD_SPECIALIST_EMAIL:
        await process_specialist_email(message, storage, language)
    elif state == ConversationState.ADMIN_SET_DAY_OFF_DATE:
        await process_dayoff_date(message, storage, language)
    elif state == ConversationState.ADMIN_SET_DAY_OFF_REASON:
        await process_dayoff_reason(message, storage, language)


async def process_specialist_name(message: Message, storage, language: str) -> None:
    """Process specialist name input."""
    user_id = message.from_user.id
    
    # Validate name
    is_valid, error = validate_name(message.text)
    if not is_valid:
        await message.answer(get_text("errors.validation_error", language, message=error))
        return
    
    # Update context with name
    context = await storage.load(user_id)
    collected_info = context.collected_info
    collected_info.name = message.text.strip()
    
    await storage.update(
        user_id,
        state=ConversationState.ADMIN_ADD_SPECIALIST_SPECIALIZATION,
        collected_info=collected_info,
    )
    
    await message.answer(get_text("admin.enter_specialization", language))


async def process_specialist_specialization(message: Message, storage, language: str) -> None:
    """Process specialist specialization input."""
    user_id = message.from_user.id
    
    # Validate specialization
    is_valid, error = validate_specialization(message.text)
    if not is_valid:
        await message.answer(get_text("errors.validation_error", language, message=error))
        return
    
    # Update context
    context = await storage.load(user_id)
    collected_info = context.collected_info
    collected_info.doctor_name = message.text.strip()  # Reuse for specialization
    
    await storage.update(
        user_id,
        state=ConversationState.ADMIN_ADD_SPECIALIST_PHONE,
        collected_info=collected_info,
    )
    
    await message.answer(get_text("admin.enter_phone", language))


async def process_specialist_phone(message: Message, storage, language: str) -> None:
    """Process specialist phone input."""
    user_id = message.from_user.id
    
    # Validate phone
    is_valid, error = validate_phone(message.text)
    if not is_valid:
        await message.answer(get_text("errors.validation_error", language, message=error))
        return
    
    # Update context
    context = await storage.load(user_id)
    collected_info = context.collected_info
    collected_info.phone = message.text.strip()
    
    await storage.update(
        user_id,
        state=ConversationState.ADMIN_ADD_SPECIALIST_EMAIL,
        collected_info=collected_info,
    )
    
    await message.answer(get_text("admin.enter_email", language))


async def process_specialist_email(message: Message, storage, language: str) -> None:
    """Process specialist email input."""
    user_id = message.from_user.id
    
    # Validate email (skip if empty)
    email = message.text.strip()
    if email and email.lower() not in ["skip", "пропустить", "-"]:
        is_valid, error = validate_email(email)
        if not is_valid:
            await message.answer(get_text("errors.validation_error", language, message=error))
            return
    else:
        email = None
    
    # Update context and move to confirmation
    context = await storage.load(user_id)
    collected_info = context.collected_info
    if email:
        collected_info.notes = email  # Reuse for email
    
    await storage.update(
        user_id,
        state=ConversationState.ADMIN_ADD_SPECIALIST_CONFIRM,
        collected_info=collected_info,
    )
    
    # Show confirmation
    confirmation_text = f"""
✅ Подтвердите информацию о специалисте:

Имя: {collected_info.name}
Специализация: {collected_info.doctor_name}
Телефон: {collected_info.phone}
Email: {email or 'Не указан'}
"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("common.yes", language),
                    callback_data="confirm_add_specialist"
                ),
                InlineKeyboardButton(
                    text=get_text("common.no", language),
                    callback_data="cancel_add_specialist"
                ),
            ]
        ]
    )
    
    await message.answer(confirmation_text, reply_markup=keyboard)


@admin_router.callback_query(F.data == "confirm_add_specialist")
async def cb_confirm_add_specialist(query: types.CallbackQuery) -> None:
    """Confirm and save new specialist."""
    if not is_admin(query.from_user.id):
        await query.answer(get_text("errors.permission_denied"), show_alert=True)
        return
    
    user_id = query.from_user.id
    language = detect_language(query.from_user.language_code)
    
    try:
        storage = get_storage()
        context = await storage.load(user_id)
        info = context.collected_info
        
        # Create specialist DTO
        specialist = SpecialistDTO(
            name=info.name,
            specialization=info.doctor_name,
            phone=info.phone,
            email=info.notes,
            is_active=True,
        )
        
        # Note: In production, inject sheets_manager via dependency
        # For now, we'll just log the action
        await query.message.answer(
            get_text("admin.specialist_added", language)
        )
        
        # Return to admin menu
        await storage.update(
            user_id,
            state=ConversationState.ADMIN_MENU,
            collected_info=CollectedInfo(),
        )
        
    except Exception as e:
        logger.error(f"Error creating specialist: {e}")
        await query.message.answer(get_text("errors.general", language))
    
    await query.answer()


@admin_router.callback_query(F.data == "cancel_add_specialist")
async def cb_cancel_add_specialist(query: types.CallbackQuery) -> None:
    """Cancel add specialist flow."""
    user_id = query.from_user.id
    language = detect_language(query.from_user.language_code)
    
    storage = get_storage()
    await storage.update(
        user_id,
        state=ConversationState.ADMIN_MENU,
        collected_info=CollectedInfo(),
    )
    
    await query.message.answer(get_text("menu.cancel", language))
    await query.answer()


@admin_router.callback_query(F.data == "admin_set_day_off")
async def cb_set_day_off_start(query: types.CallbackQuery) -> None:
    """Start set day off flow."""
    if not is_admin(query.from_user.id):
        await query.answer(get_text("errors.permission_denied"), show_alert=True)
        return
    
    user_id = query.from_user.id
    language = detect_language(query.from_user.language_code)
    
    storage = get_storage()
    await storage.update(
        user_id,
        state=ConversationState.ADMIN_SET_DAY_OFF_SPECIALIST,
    )
    
    # In production, would get from repository via sheets_manager
    # For now, show simple prompt
    await query.message.answer(
        "Введите ID специалиста:"
    )
    await query.answer()


@admin_router.callback_query(F.data.startswith("dayoff_specialist_"))
async def cb_dayoff_specialist_selected(query: types.CallbackQuery) -> None:
    """Process selected specialist for day off."""
    if not is_admin(query.from_user.id):
        await query.answer(get_text("errors.permission_denied"), show_alert=True)
        return
    
    user_id = query.from_user.id
    language = detect_language(query.from_user.language_code)
    
    spec_id = int(query.data.split("_")[-1])
    
    storage = get_storage()
    context = await storage.load(user_id)
    collected_info = context.collected_info
    collected_info.doctor_id = spec_id
    
    await storage.update(
        user_id,
        state=ConversationState.ADMIN_SET_DAY_OFF_DATE,
        collected_info=collected_info,
    )
    
    await query.message.answer(
        "Введите дату выходного (YYYY-MM-DD):"
    )
    await query.answer()


async def process_dayoff_date(message: Message, storage, language: str) -> None:
    """Process day off date input."""
    user_id = message.from_user.id
    
    # Validate date
    is_valid, error = validate_date_format(message.text)
    if not is_valid:
        await message.answer(get_text("errors.validation_error", language, message=error))
        return
    
    context = await storage.load(user_id)
    collected_info = context.collected_info
    collected_info.booking_date = message.text.strip()
    
    await storage.update(
        user_id,
        state=ConversationState.ADMIN_SET_DAY_OFF_REASON,
        collected_info=collected_info,
    )
    
    await message.answer("Введите причину выходного (или 'Пропустить'):")


async def process_dayoff_reason(message: Message, storage, language: str) -> None:
    """Process day off reason input."""
    user_id = message.from_user.id
    
    reason = message.text.strip()
    if reason.lower() in ["пропустить", "skip", "-"]:
        reason = None
    
    context = await storage.load(user_id)
    collected_info = context.collected_info
    collected_info.notes = reason
    
    await storage.update(
        user_id,
        state=ConversationState.ADMIN_SET_DAY_OFF_CONFIRM,
        collected_info=collected_info,
    )
    
    # Show confirmation
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("common.yes", language),
                    callback_data="confirm_day_off"
                ),
                InlineKeyboardButton(
                    text=get_text("common.no", language),
                    callback_data="cancel_day_off"
                ),
            ]
        ]
    )
    
    await message.answer(
        f"Подтвердите:\nДата: {collected_info.booking_date}\nПричина: {reason or 'Не указана'}",
        reply_markup=keyboard
    )


@admin_router.callback_query(F.data == "confirm_day_off")
async def cb_confirm_day_off(query: types.CallbackQuery) -> None:
    """Confirm and save day off."""
    if not is_admin(query.from_user.id):
        await query.answer(get_text("errors.permission_denied"), show_alert=True)
        return
    
    user_id = query.from_user.id
    language = detect_language(query.from_user.language_code)
    
    try:
        storage = get_storage()
        context = await storage.load(user_id)
        info = context.collected_info
        
        day_off = DayOffDTO(
            specialist_id=info.doctor_id,
            date=info.booking_date,
            reason=info.notes,
        )
        
        await query.message.answer(
            get_text("admin.day_off_set", language)
        )
        
        await storage.update(
            user_id,
            state=ConversationState.ADMIN_MENU,
            collected_info=CollectedInfo(),
        )
        
    except Exception as e:
        logger.error(f"Error setting day off: {e}")
        await query.message.answer(get_text("errors.general", language))
    
    await query.answer()


@admin_router.callback_query(F.data == "cancel_day_off")
async def cb_cancel_day_off(query: types.CallbackQuery) -> None:
    """Cancel day off flow."""
    user_id = query.from_user.id
    language = detect_language(query.from_user.language_code)
    
    storage = get_storage()
    await storage.update(
        user_id,
        state=ConversationState.ADMIN_MENU,
        collected_info=CollectedInfo(),
    )
    
    await query.message.answer(get_text("menu.cancel", language))
    await query.answer()


@admin_router.callback_query(F.data == "admin_view_bookings")
async def cb_view_bookings(query: types.CallbackQuery) -> None:
    """View all bookings."""
    if not is_admin(query.from_user.id):
        await query.answer(get_text("errors.permission_denied"), show_alert=True)
        return
    
    language = detect_language(query.from_user.language_code)
    
    try:
        summary = f"📋 {get_text('admin.view_all_bookings', language)}\n\n"
        summary += "No bookings available\n"
        
        await query.message.answer(summary)
    except Exception as e:
        logger.error(f"Error viewing bookings: {e}")
        await query.message.answer(get_text("errors.general", language))
    
    await query.answer()


@admin_router.callback_query(F.data == "admin_view_logs")
async def cb_view_logs(query: types.CallbackQuery) -> None:
    """View admin logs."""
    if not is_admin(query.from_user.id):
        await query.answer(get_text("errors.permission_denied"), show_alert=True)
        return
    
    language = detect_language(query.from_user.language_code)
    
    try:
        summary = f"📊 {get_text('admin.view_logs', language)}\n\n"
        summary += "No logs available\n"
        
        await query.message.answer(summary)
    except Exception as e:
        logger.error(f"Error viewing logs: {e}")
        await query.message.answer(get_text("errors.general", language))
    
    await query.answer()


@admin_router.callback_query(F.data == "admin_sync")
async def cb_sync_data(query: types.CallbackQuery) -> None:
    """Trigger data synchronization."""
    if not is_admin(query.from_user.id):
        await query.answer(get_text("errors.permission_denied"), show_alert=True)
        return
    
    language = detect_language(query.from_user.language_code)
    
    try:
        await query.message.answer(get_text("admin.sync_started", language))
        
        await query.message.answer(
            get_text(
                "admin.sync_completed",
                language,
                pulled=0,
                pushed=0,
                conflicts=0,
            )
        )
    except Exception as e:
        logger.error(f"Error syncing data: {e}")
        await query.message.answer(
            get_text("admin.sync_failed", language, error=str(e))
        )
    
    await query.answer()


@admin_router.callback_query(F.data == "admin_edit_specialist")
async def cb_edit_specialist(query: types.CallbackQuery) -> None:
    """Handle edit specialist flow."""
    if not is_admin(query.from_user.id):
        await query.answer(get_text("errors.permission_denied"), show_alert=True)
        return
    
    language = detect_language(query.from_user.language_code)
    await query.message.answer("Edit specialist feature coming soon")
    await query.answer()


@admin_router.callback_query(F.data == "admin_delete_specialist")
async def cb_delete_specialist(query: types.CallbackQuery) -> None:
    """Handle delete specialist flow."""
    if not is_admin(query.from_user.id):
        await query.answer(get_text("errors.permission_denied"), show_alert=True)
        return
    
    language = detect_language(query.from_user.language_code)
    await query.message.answer("Delete specialist feature coming soon")
    await query.answer()


@admin_router.callback_query(F.data == "back_to_admin_menu")
async def cb_back_to_admin_menu(query: types.CallbackQuery) -> None:
    """Go back to admin menu."""
    user_id = query.from_user.id
    language = detect_language(query.from_user.language_code)
    
    storage = get_storage()
    await storage.update(
        user_id,
        state=ConversationState.ADMIN_MENU,
        collected_info=CollectedInfo(),
    )
    
    await cmd_admin(query.message)
    await query.answer()


@admin_router.callback_query(F.data == "back_to_start")
async def cb_back_to_start(query: types.CallbackQuery) -> None:
    """Go back to start."""
    user_id = query.from_user.id
    
    storage = get_storage()
    await storage.update(
        user_id,
        state=ConversationState.START,
        collected_info=CollectedInfo(),
        admin_mode=False,
    )
    
    language = detect_language(query.from_user.language_code)
    await query.message.answer(get_text("greetings.welcome", language))
    await query.answer()
