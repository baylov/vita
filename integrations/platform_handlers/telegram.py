"""Telegram platform adapter using aiogram."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.types import Update, Message as AiogramMessage, CallbackQuery
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from integrations.platform_handlers.base import (
    PlatformAdapter,
    Message,
    MessageType,
    WebhookValidationError,
)
from services.notifications.notifier import Notifier, NotificationEvent

logger = logging.getLogger(__name__)


class TelegramAdapter(PlatformAdapter):
    """Telegram platform adapter using aiogram Bot."""
    
    def __init__(
        self,
        bot: Optional[Bot] = None,
        notifier: Optional[Notifier] = None,
    ):
        """Initialize Telegram adapter.
        
        Args:
            bot: Aiogram Bot instance
            notifier: Notifier instance for admin alerts
        """
        super().__init__("telegram")
        self.bot = bot
        self.notifier = notifier
    
    def set_bot(self, bot: Bot) -> None:
        """Set aiogram Bot instance.
        
        Args:
            bot: Aiogram Bot instance
        """
        self.bot = bot
        logger.info("Telegram bot instance configured")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((OSError, ConnectionError)),
    )
    async def send_message(
        self,
        recipient_id: str,
        text: str,
        **kwargs
    ) -> bool:
        """Send text message via Telegram.
        
        Args:
            recipient_id: Telegram user ID
            text: Message text
            **kwargs: Additional arguments (reply_markup, parse_mode, etc.)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.bot:
            logger.error("Telegram bot not configured")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=int(recipient_id),
                text=text,
                **kwargs
            )
            logger.debug(f"Sent Telegram message to {recipient_id}")
            return True
            
        except ValueError as e:
            logger.error(f"Invalid recipient ID format: {recipient_id}: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to send Telegram message to {recipient_id}: {e}")
            await self._notify_admin_error(recipient_id, str(e))
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((OSError, ConnectionError)),
    )
    async def send_media(
        self,
        recipient_id: str,
        media_url: str,
        media_type: str,
        caption: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send media message via Telegram.
        
        Args:
            recipient_id: Telegram user ID
            media_url: URL or file_id of media
            media_type: Type of media (image, video, document, audio)
            caption: Optional caption
            **kwargs: Additional arguments
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.bot:
            logger.error("Telegram bot not configured")
            return False
        
        try:
            chat_id = int(recipient_id)
            
            if media_type == "image":
                await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=media_url,
                    caption=caption,
                    **kwargs
                )
            elif media_type == "video":
                await self.bot.send_video(
                    chat_id=chat_id,
                    video=media_url,
                    caption=caption,
                    **kwargs
                )
            elif media_type == "document":
                await self.bot.send_document(
                    chat_id=chat_id,
                    document=media_url,
                    caption=caption,
                    **kwargs
                )
            elif media_type == "audio":
                await self.bot.send_audio(
                    chat_id=chat_id,
                    audio=media_url,
                    caption=caption,
                    **kwargs
                )
            else:
                logger.warning(f"Unsupported media type: {media_type}")
                return False
            
            logger.debug(f"Sent Telegram {media_type} to {recipient_id}")
            return True
            
        except ValueError as e:
            logger.error(f"Invalid recipient ID format: {recipient_id}: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to send Telegram media to {recipient_id}: {e}")
            await self._notify_admin_error(recipient_id, str(e))
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((OSError, ConnectionError)),
    )
    async def send_typing(
        self,
        recipient_id: str,
        **kwargs
    ) -> bool:
        """Send typing indicator via Telegram.
        
        Args:
            recipient_id: Telegram user ID
            **kwargs: Additional arguments
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.bot:
            logger.error("Telegram bot not configured")
            return False
        
        try:
            await self.bot.send_chat_action(
                chat_id=int(recipient_id),
                action="typing"
            )
            return True
            
        except ValueError as e:
            logger.error(f"Invalid recipient ID format: {recipient_id}: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to send typing indicator to {recipient_id}: {e}")
            return False
    
    async def notify_error(
        self,
        recipient_id: str,
        error_message: str,
        **kwargs
    ) -> bool:
        """Send error notification via Telegram.
        
        Args:
            recipient_id: Telegram user ID
            error_message: Error message to send
            **kwargs: Additional arguments
            
        Returns:
            True if sent successfully, False otherwise
        """
        formatted_message = f"⚠️ Ошибка: {error_message}"
        return await self.send_message(recipient_id, formatted_message, **kwargs)
    
    def parse_webhook(
        self,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[Message]:
        """Parse Telegram webhook (Update) payload.
        
        Args:
            payload: Telegram Update dict, Update object, Message object, or CallbackQuery object
            headers: HTTP headers (not used for Telegram)
            
        Returns:
            Parsed Message object or None if parsing failed
        """
        try:
            # Handle direct Message objects (from tests or direct dispatch)
            if isinstance(payload, AiogramMessage):
                return self._parse_message(payload)
            
            # Handle direct CallbackQuery objects
            if isinstance(payload, CallbackQuery):
                return self._parse_callback_query(payload)
            
            # Handle Update objects or dicts
            if isinstance(payload, Update):
                update = payload
            elif isinstance(payload, dict):
                update = Update(**payload)
            else:
                logger.error(f"Unsupported payload type: {type(payload)}")
                return None
            
            # Parse message
            if update.message:
                return self._parse_message(update.message)
            
            # Parse callback query
            elif update.callback_query:
                return self._parse_callback_query(update.callback_query)
            
            # Unsupported update type
            else:
                logger.debug(f"Unsupported update type: {update}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to parse Telegram webhook: {e}")
            return None
    
    def _parse_message(self, message: AiogramMessage) -> Message:
        """Parse Telegram message.
        
        Args:
            message: Aiogram Message object
            
        Returns:
            Parsed Message object
        """
        # Determine message type
        message_type = MessageType.TEXT
        text = message.text
        media_url = None
        media_type = None
        
        if message.voice:
            message_type = MessageType.VOICE
            media_url = message.voice.file_id
            media_type = "voice"
            text = None
        elif message.photo:
            message_type = MessageType.IMAGE
            media_url = message.photo[-1].file_id  # Get largest photo
            media_type = "image"
            text = message.caption
        elif message.video:
            message_type = MessageType.VIDEO
            media_url = message.video.file_id
            media_type = "video"
            text = message.caption
        elif message.document:
            message_type = MessageType.DOCUMENT
            media_url = message.document.file_id
            media_type = "document"
            text = message.caption
        elif message.location:
            message_type = MessageType.LOCATION
            text = f"Location: {message.location.latitude}, {message.location.longitude}"
        
        return Message(
            message_id=str(message.message_id),
            platform="telegram",
            platform_user_id=str(message.from_user.id),
            message_type=message_type,
            text=text,
            media_url=media_url,
            media_type=media_type,
            language_code=message.from_user.language_code,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            timestamp=datetime.fromtimestamp(message.date.timestamp(), tz=timezone.utc) if message.date else datetime.now(timezone.utc),
            raw_payload=message.model_dump() if hasattr(message, 'model_dump') else {},
        )
    
    def _parse_callback_query(self, callback_query: CallbackQuery) -> Message:
        """Parse Telegram callback query.
        
        Args:
            callback_query: Aiogram CallbackQuery object
            
        Returns:
            Parsed Message object
        """
        return Message(
            message_id=str(callback_query.id),
            platform="telegram",
            platform_user_id=str(callback_query.from_user.id),
            message_type=MessageType.CALLBACK,
            callback_data=callback_query.data,
            language_code=callback_query.from_user.language_code,
            username=callback_query.from_user.username,
            first_name=callback_query.from_user.first_name,
            last_name=callback_query.from_user.last_name,
            timestamp=datetime.now(timezone.utc),
            raw_payload=callback_query.model_dump() if hasattr(callback_query, 'model_dump') else {},
        )
    
    def validate_webhook(
        self,
        payload: Dict[str, Any],
        signature: str,
        **kwargs
    ) -> bool:
        """Validate Telegram webhook.
        
        Note: Telegram webhooks are validated via secret token in URL path,
        not via signature. This method is a no-op for Telegram.
        
        Args:
            payload: Webhook payload
            signature: Not used for Telegram
            **kwargs: Additional arguments
            
        Returns:
            Always True for Telegram (validation handled by bot token in URL)
        """
        return True
    
    async def _notify_admin_error(self, recipient_id: str, error: str) -> None:
        """Notify admin of adapter error.
        
        Args:
            recipient_id: Recipient that failed
            error: Error message
        """
        if not self.notifier:
            return
        
        try:
            event = NotificationEvent(
                event_type="adapter_error",
                recipient_id=1,  # Default admin
                recipient_type="admin",
                language="ru",
                data={
                    "platform": "telegram",
                    "recipient_id": recipient_id,
                    "error": error,
                },
                priority="urgent",
                channels=["telegram"],
            )
            
            await self.notifier.send_urgent_escalation(event)
            
        except Exception as e:
            logger.error(f"Failed to notify admin of error: {e}")
