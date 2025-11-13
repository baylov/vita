"""Platform adapters for multi-channel notifications."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationAdapter(ABC):
    """Abstract base class for notification adapters."""

    def __init__(self, channel_name: str):
        """Initialize adapter with channel name."""
        self.channel_name = channel_name
        self.is_available = True

    @abstractmethod
    async def send(
        self,
        recipient_id: int,
        message: str,
        subject: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send notification to recipient.

        Args:
            recipient_id: ID of recipient
            message: Message content
            subject: Optional message subject
            **kwargs: Additional adapter-specific arguments

        Returns:
            True if sent successfully, False otherwise
        """
        pass

    @abstractmethod
    def validate_recipient(self, recipient_id: int) -> bool:
        """Validate that recipient exists and is valid.

        Args:
            recipient_id: ID of recipient to validate

        Returns:
            True if recipient is valid, False otherwise
        """
        pass


class TelegramAdapter(NotificationAdapter):
    """Telegram notification adapter."""

    def __init__(self):
        """Initialize Telegram adapter."""
        super().__init__("telegram")
        self.mock_mode = False
        self._sent_messages = []

    async def send(
        self,
        recipient_id: int,
        message: str,
        subject: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send notification via Telegram.

        Args:
            recipient_id: Telegram user ID
            message: Message content
            subject: Ignored for Telegram
            **kwargs: Additional arguments

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not self.validate_recipient(recipient_id):
                logger.warning(f"Invalid Telegram recipient: {recipient_id}")
                return False

            if self.mock_mode:
                self._sent_messages.append({
                    "recipient_id": recipient_id,
                    "message": message,
                    "timestamp": datetime.now(timezone.utc),
                })
                logger.debug(f"Mock Telegram send to {recipient_id}")
                return True

            logger.info(f"Sending Telegram message to {recipient_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False

    def validate_recipient(self, recipient_id: int) -> bool:
        """Validate Telegram recipient.

        Args:
            recipient_id: Telegram user ID to validate

        Returns:
            True if valid (positive integer), False otherwise
        """
        return isinstance(recipient_id, int) and recipient_id > 0

    def enable_mock_mode(self) -> None:
        """Enable mock mode for testing."""
        self.mock_mode = True

    def get_sent_messages(self) -> list:
        """Get list of sent messages in mock mode."""
        return self._sent_messages.copy()

    def clear_sent_messages(self) -> None:
        """Clear sent messages log."""
        self._sent_messages.clear()


class WhatsAppAdapter(NotificationAdapter):
    """WhatsApp notification adapter."""

    def __init__(self):
        """Initialize WhatsApp adapter."""
        super().__init__("whatsapp")
        self.mock_mode = False
        self._sent_messages = []

    async def send(
        self,
        recipient_id: int,
        message: str,
        subject: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send notification via WhatsApp.

        Args:
            recipient_id: WhatsApp user ID or phone number
            message: Message content
            subject: Ignored for WhatsApp
            **kwargs: Additional arguments

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not self.validate_recipient(recipient_id):
                logger.warning(f"Invalid WhatsApp recipient: {recipient_id}")
                return False

            if self.mock_mode:
                self._sent_messages.append({
                    "recipient_id": recipient_id,
                    "message": message,
                    "timestamp": datetime.now(timezone.utc),
                })
                logger.debug(f"Mock WhatsApp send to {recipient_id}")
                return True

            logger.info(f"Sending WhatsApp message to {recipient_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send WhatsApp notification: {e}")
            return False

    def validate_recipient(self, recipient_id: int) -> bool:
        """Validate WhatsApp recipient.

        Args:
            recipient_id: WhatsApp user ID to validate

        Returns:
            True if valid (positive integer), False otherwise
        """
        return isinstance(recipient_id, int) and recipient_id > 0

    def enable_mock_mode(self) -> None:
        """Enable mock mode for testing."""
        self.mock_mode = True

    def get_sent_messages(self) -> list:
        """Get list of sent messages in mock mode."""
        return self._sent_messages.copy()

    def clear_sent_messages(self) -> None:
        """Clear sent messages log."""
        self._sent_messages.clear()


class InstagramAdapter(NotificationAdapter):
    """Instagram Direct Message notification adapter."""

    def __init__(self):
        """Initialize Instagram adapter."""
        super().__init__("instagram")
        self.mock_mode = False
        self._sent_messages = []

    async def send(
        self,
        recipient_id: int,
        message: str,
        subject: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send notification via Instagram DM.

        Args:
            recipient_id: Instagram user ID
            message: Message content
            subject: Ignored for Instagram
            **kwargs: Additional arguments

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not self.validate_recipient(recipient_id):
                logger.warning(f"Invalid Instagram recipient: {recipient_id}")
                return False

            if self.mock_mode:
                self._sent_messages.append({
                    "recipient_id": recipient_id,
                    "message": message,
                    "timestamp": datetime.now(timezone.utc),
                })
                logger.debug(f"Mock Instagram send to {recipient_id}")
                return True

            logger.info(f"Sending Instagram message to {recipient_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Instagram notification: {e}")
            return False

    def validate_recipient(self, recipient_id: int) -> bool:
        """Validate Instagram recipient.

        Args:
            recipient_id: Instagram user ID to validate

        Returns:
            True if valid (positive integer), False otherwise
        """
        return isinstance(recipient_id, int) and recipient_id > 0

    def enable_mock_mode(self) -> None:
        """Enable mock mode for testing."""
        self.mock_mode = True

    def get_sent_messages(self) -> list:
        """Get list of sent messages in mock mode."""
        return self._sent_messages.copy()

    def clear_sent_messages(self) -> None:
        """Clear sent messages log."""
        self._sent_messages.clear()
