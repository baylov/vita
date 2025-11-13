"""Multi-channel notification service with urgency tiers and scheduling."""

from services.notifications.notifier import Notifier, NotificationEvent
from services.notifications.adapters import (
    NotificationAdapter,
    TelegramAdapter,
    WhatsAppAdapter,
    InstagramAdapter,
)
from services.notifications.templates import (
    NotificationTemplate,
    BookingNotificationTemplate,
    ComplaintNotificationTemplate,
    DigestNotificationTemplate,
    AdminAlertTemplate,
    add_urgent_tag,
    should_escalate_to_urgent,
)

__all__ = [
    "Notifier",
    "NotificationEvent",
    "NotificationAdapter",
    "TelegramAdapter",
    "WhatsAppAdapter",
    "InstagramAdapter",
    "NotificationTemplate",
    "BookingNotificationTemplate",
    "ComplaintNotificationTemplate",
    "DigestNotificationTemplate",
    "AdminAlertTemplate",
    "add_urgent_tag",
    "should_escalate_to_urgent",
]
