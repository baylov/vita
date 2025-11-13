"""Aiogram middlewares for error handling, logging, and monitoring."""

import asyncio
import json
import logging
import traceback
from typing import Callable, Any, Optional, Dict

from aiogram import BaseMiddleware, types
from aiogram.types import TelegramObject, Update, Message, CallbackQuery, User

from core.errors import ExternalServiceError, ManualInterventionRequired
from core.conversation import ConversationContext
from models import ErrorLogDTO

logger = logging.getLogger(__name__)


class ContextLoggingMiddleware(BaseMiddleware):
    """Middleware to add contextual metadata to all log records."""

    def __init__(
        self,
        sheets_manager: Optional[Any] = None,
        conversation_storage: Optional[Any] = None,
    ):
        """
        Initialize the logging middleware.

        Args:
            sheets_manager: Google Sheets manager for error logging
            conversation_storage: Conversation context storage for state tracking
        """
        self.sheets_manager = sheets_manager
        self.conversation_storage = conversation_storage
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Any],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Process middleware - add context to log records."""
        # Extract user_id and message info from the event
        user_id: Optional[int] = None
        message_type: Optional[str] = None
        message_text: Optional[str] = None
        platform: str = "telegram"

        if isinstance(event, Update):
            if event.message:
                user_id = event.message.from_user.id if event.message.from_user else None
                message_type = "text" if event.message.text else "media"
                message_text = event.message.text[:100] if event.message.text else None
            elif event.callback_query:
                user_id = (
                    event.callback_query.from_user.id
                    if event.callback_query.from_user
                    else None
                )
                message_type = "callback"
                message_text = event.callback_query.data[:100]

        # Get conversation context if available
        context: Optional[ConversationContext] = None
        state: Optional[str] = None
        if user_id and self.conversation_storage:
            try:
                context_data = await self.conversation_storage.get_data(
                    key=str(user_id)
                )
                if context_data and isinstance(context_data, dict):
                    context = ConversationContext(**context_data)
                    state = context.current_state
            except Exception as e:
                logger.debug(f"Failed to load context for user {user_id}: {e}")

        # Add context to logger
        old_factory = logging.getLoggerClass()

        class ContextualLogger(logging.Logger):
            def makeRecord(
                self,
                name: str,
                level: int,
                fn: str,
                lno: int,
                msg: str,
                args: tuple,
                exc_info: Any,
                func: Optional[str] = None,
                extra: Optional[dict] = None,
                sinfo: Optional[str] = None,
            ) -> logging.LogRecord:
                if extra is None:
                    extra = {}
                extra.update(
                    {
                        "user_id": user_id,
                        "platform": platform,
                        "message_type": message_type,
                        "state": state,
                    }
                )
                return super().makeRecord(
                    name, level, fn, lno, msg, args, exc_info, func, extra, sinfo
                )

        logging.setLoggerClass(ContextualLogger)

        try:
            return await handler(event, data)
        finally:
            logging.setLoggerClass(old_factory)


class ErrorHandlingMiddleware(BaseMiddleware):
    """Middleware to catch exceptions, log them, and provide fallback responses."""

    def __init__(
        self,
        sheets_manager: Optional[Any] = None,
        notifier: Optional[Any] = None,
        admin_ids: Optional[list[int]] = None,
    ):
        """
        Initialize the error handling middleware.

        Args:
            sheets_manager: Google Sheets manager for error logging
            notifier: Notifier instance for admin alerts
            admin_ids: List of admin user IDs to notify
        """
        self.sheets_manager = sheets_manager
        self.notifier = notifier
        self.admin_ids = admin_ids or []
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Any],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Process middleware - catch and handle exceptions."""
        user_id: Optional[int] = None
        bot: Optional[Any] = None

        try:
            # Extract user_id and bot from event and data
            if isinstance(event, Update):
                if event.message and event.message.from_user:
                    user_id = event.message.from_user.id
                elif event.callback_query and event.callback_query.from_user:
                    user_id = event.callback_query.from_user.id

            if "bot" in data:
                bot = data["bot"]

            # Execute the handler
            try:
                return await handler(event, data)
            except ManualInterventionRequired as e:
                logger.error(
                    f"Manual intervention required for user {user_id}: {e.message}",
                    exc_info=True,
                )

                # Log error to sheets
                if self.sheets_manager:
                    try:
                        self._log_error_to_sheets(
                            error_type="ManualInterventionRequired",
                            message=e.message,
                            user_id=user_id,
                            context=json.dumps(e.context),
                        )
                    except Exception as logging_error:
                        logger.warning(
                            f"Failed to log error to sheets: {logging_error}"
                        )

                # Notify admins
                if e.requires_admin_notification and bot and user_id:
                    await self._notify_admin_error(
                        bot, user_id, e.message, e.context
                    )

                # Send user-friendly response
                if bot and user_id:
                    try:
                        await bot.send_message(
                            user_id,
                            "⚠️ Произошла ошибка. Мы уведомили администратора. "
                            "Пожалуйста, попробуйте позже.",
                        )
                    except Exception as msg_error:
                        logger.warning(
                            f"Failed to send error message to user {user_id}: {msg_error}"
                        )

                return None

            except ExternalServiceError as e:
                logger.error(
                    f"External service error for user {user_id}: {e.service_name} - {e.message}",
                    exc_info=True,
                )

                # Log error to sheets
                if self.sheets_manager:
                    try:
                        self._log_error_to_sheets(
                            error_type=f"ExternalServiceError ({e.service_name})",
                            message=e.message,
                            user_id=user_id,
                        )
                    except Exception as logging_error:
                        logger.warning(
                            f"Failed to log error to sheets: {logging_error}"
                        )

                # Notify admins
                if bot and user_id:
                    await self._notify_admin_error(
                        bot, user_id, f"External service error: {e.service_name}"
                    )

                # Send user-friendly response
                if bot and user_id:
                    try:
                        await bot.send_message(
                            user_id,
                            "⚠️ Сервис временно недоступен. Пожалуйста, попробуйте позже.",
                        )
                    except Exception as msg_error:
                        logger.warning(
                            f"Failed to send error message to user {user_id}: {msg_error}"
                        )

                return None

            except Exception as e:
                logger.error(
                    f"Unhandled exception for user {user_id}: {str(e)}",
                    exc_info=True,
                )

                # Log error to sheets
                if self.sheets_manager:
                    try:
                        error_traceback = traceback.format_exc()
                        self._log_error_to_sheets(
                            error_type=type(e).__name__,
                            message=str(e),
                            user_id=user_id,
                            traceback_str=error_traceback,
                        )
                    except Exception as logging_error:
                        logger.warning(
                            f"Failed to log error to sheets: {logging_error}"
                        )

                # Notify admins
                if bot and user_id:
                    await self._notify_admin_error(
                        bot, user_id, f"Unexpected error: {type(e).__name__}"
                    )

                # Send user-friendly response
                if bot and user_id:
                    try:
                        await bot.send_message(
                            user_id,
                            "❌ Произошла непредвиденная ошибка. "
                            "Администратор был уведомлен.",
                        )
                    except Exception as msg_error:
                        logger.warning(
                            f"Failed to send error message to user {user_id}: {msg_error}"
                        )

                return None

        except Exception as e:
            logger.critical(
                f"Critical error in ErrorHandlingMiddleware: {str(e)}",
                exc_info=True,
            )
            raise

    def _log_error_to_sheets(
        self,
        error_type: str,
        message: str,
        user_id: Optional[int] = None,
        context: Optional[str] = None,
        traceback_str: Optional[str] = None,
    ) -> None:
        """Log error to Google Sheets."""
        if not self.sheets_manager:
            return

        try:
            full_context = context or ""
            if user_id:
                full_context = f"User: {user_id}, {full_context}" if full_context else f"User: {user_id}"

            self.sheets_manager._log_error(
                error_type=error_type,
                message=message,
                context=full_context,
                traceback=traceback_str,
            )
        except Exception as e:
            logger.warning(f"Failed to log error to sheets: {e}")

    async def _notify_admin_error(
        self,
        bot: Any,
        user_id: int,
        error_message: str,
        context: Optional[dict] = None,
    ) -> None:
        """Notify admins about the error."""
        if not self.admin_ids or not bot:
            return

        try:
            # Format admin notification
            admin_message = (
                f"🚨 *Error Alert*\n\n"
                f"User ID: `{user_id}`\n"
                f"Error: {error_message}"
            )

            if context:
                admin_message += f"\n\nContext: `{json.dumps(context)}`"

            # Send to all admins
            for admin_id in self.admin_ids:
                try:
                    await bot.send_message(
                        admin_id,
                        admin_message,
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    logger.warning(f"Failed to notify admin {admin_id}: {e}")

        except Exception as e:
            logger.warning(f"Failed to notify admins: {e}")


class StructuredLoggingFormatter(logging.Formatter):
    """Custom formatter to add structured logging with context metadata."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with contextual metadata."""
        # Add extra fields to the record
        user_id = getattr(record, "user_id", None)
        platform = getattr(record, "platform", None)
        state = getattr(record, "state", None)
        message_type = getattr(record, "message_type", None)

        # Build context string
        context_parts = []
        if user_id:
            context_parts.append(f"user_id={user_id}")
        if platform:
            context_parts.append(f"platform={platform}")
        if state:
            context_parts.append(f"state={state}")
        if message_type:
            context_parts.append(f"msg_type={message_type}")

        context_str = f" [{', '.join(context_parts)}]" if context_parts else ""

        # Format the log message
        base_format = f"%(asctime)s - %(name)s - %(levelname)s{context_str} - %(message)s"
        formatter = logging.Formatter(base_format, datefmt="%Y-%m-%d %H:%M:%S")

        return formatter.format(record)


def setup_logging(
    log_level: int = logging.INFO,
    log_file: Optional[str] = "app.log",
) -> None:
    """
    Configure application logging with structured output.

    Args:
        log_level: Logging level (default: INFO)
        log_file: Path to log file (optional)
    """
    # Create logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Create formatter
    formatter = StructuredLoggingFormatter()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            logger.warning(f"Failed to setup file logging: {e}")

    logger.info(f"Logging configured with level: {logging.getLevelName(log_level)}")
