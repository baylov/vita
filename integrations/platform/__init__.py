"""Platform integrations for unified messaging."""

from integrations.platform.base import Message, PlatformAdapter, WebhookValidationError
from integrations.platform.telegram import TelegramAdapter
from integrations.platform.whatsapp import WhatsAppAdapter
from integrations.platform.instagram import InstagramAdapter
from integrations.platform.router import MessageRouter

__all__ = [
    "Message",
    "PlatformAdapter",
    "WebhookValidationError",
    "TelegramAdapter",
    "WhatsAppAdapter",
    "InstagramAdapter",
    "MessageRouter",
]
