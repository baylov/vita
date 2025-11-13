"""Platform integrations for unified messaging."""

from integrations.platform_handlers.base import Message, PlatformAdapter, WebhookValidationError
from integrations.platform_handlers.telegram import TelegramAdapter
from integrations.platform_handlers.whatsapp import WhatsAppAdapter
from integrations.platform_handlers.instagram import InstagramAdapter
from integrations.platform_handlers.router import MessageRouter

__all__ = [
    "Message",
    "PlatformAdapter",
    "WebhookValidationError",
    "TelegramAdapter",
    "WhatsAppAdapter",
    "InstagramAdapter",
    "MessageRouter",
]
