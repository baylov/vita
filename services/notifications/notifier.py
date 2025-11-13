"""Main notification service with multi-channel support and urgency tiers."""

import asyncio
import logging
from datetime import datetime, timezone, time
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from settings import settings
from core.i18n import get_text, detect_language
from models import NotificationLogDTO
from services.notifications.adapters import (
    NotificationAdapter,
    TelegramAdapter,
    WhatsAppAdapter,
    InstagramAdapter,
)
from services.notifications.templates import (
    BookingNotificationTemplate,
    ComplaintNotificationTemplate,
    DigestNotificationTemplate,
    AdminAlertTemplate,
    add_urgent_tag,
    should_escalate_to_urgent,
)


logger = logging.getLogger(__name__)


@dataclass
class NotificationEvent:
    """Represents a notification event."""

    event_type: str  # booking_created, booking_cancelled, complaint_received
    recipient_id: int
    recipient_type: str  # specialist, admin, client
    language: str = "ru"
    data: Dict = field(default_factory=dict)
    priority: str = "normal"  # immediate, urgent, scheduled
    channels: List[str] = field(default_factory=lambda: ["telegram"])
    related_booking_id: Optional[int] = None
    related_complaint_id: Optional[int] = None


class Notifier:
    """Multi-channel notification service with urgency tiers and retry logic."""

    def __init__(
        self,
        adapters: Optional[Dict[str, NotificationAdapter]] = None,
        log_callback: Optional[Callable] = None,
    ):
        """Initialize notifier with platform adapters.

        Args:
            adapters: Dictionary of channel name to adapter instances
            log_callback: Callback function to log notifications to database/sheets
        """
        self.adapters = adapters or {
            "telegram": TelegramAdapter(),
            "whatsapp": WhatsAppAdapter(),
            "instagram": InstagramAdapter(),
        }
        self.log_callback = log_callback
        self.retry_attempts = settings.notification_retry_attempts
        self.retry_delay_min = settings.notification_retry_delay_min
        self.retry_delay_max = settings.notification_retry_delay_max
        self.digest_schedule = {
            "hour": settings.digest_schedule_hour,
            "minute": settings.digest_schedule_minute,
        }
        self.pending_notifications: List[NotificationEvent] = []
        self.failed_notifications: List[Dict] = []

    async def send_immediate_alert(
        self,
        event: NotificationEvent,
    ) -> bool:
        """Send immediate per-event alert notification.

        Args:
            event: Notification event

        Returns:
            True if sent successfully, False otherwise
        """
        logger.info(f"Sending immediate alert for event: {event.event_type}")

        try:
            message = self._format_notification_message(event)

            success = await self._send_to_channels(
                event.recipient_id,
                event.channels,
                message,
                subject=event.event_type,
            )

            await self._log_notification(
                event,
                "immediate",
                "sent" if success else "failed",
                message,
            )

            if not success:
                await self._handle_failed_notification(event, message)

            return success

        except Exception as e:
            logger.error(f"Error sending immediate alert: {e}")
            await self._log_notification(
                event,
                "immediate",
                "failed",
                None,
                error_details=str(e),
            )
            return False

    async def send_urgent_escalation(
        self,
        event: NotificationEvent,
    ) -> bool:
        """Send urgent escalation with [❗️ СРОЧНО] tag.

        Args:
            event: Notification event

        Returns:
            True if sent successfully, False otherwise
        """
        logger.info(f"Sending urgent escalation for event: {event.event_type}")

        try:
            message = self._format_notification_message(event)
            message = add_urgent_tag(message, event.language)

            success = await self._send_to_channels(
                event.recipient_id,
                event.channels,
                message,
                subject=event.event_type,
            )

            await self._log_notification(
                event,
                "urgent",
                "sent" if success else "failed",
                message,
            )

            if not success:
                await self._handle_failed_notification(event, message)

            return success

        except Exception as e:
            logger.error(f"Error sending urgent escalation: {e}")
            await self._log_notification(
                event,
                "urgent",
                "failed",
                None,
                error_details=str(e),
            )
            return False

    async def schedule_daily_digest(
        self,
        recipient_id: int,
        recipient_type: str,
        language: str = "ru",
        digest_data: Optional[Dict] = None,
    ) -> None:
        """Schedule daily digest notification at 08:00.

        Args:
            recipient_id: ID of recipient
            recipient_type: Type of recipient (specialist, admin, client)
            language: Language code
            digest_data: Dictionary with digest summary data
        """
        logger.info(f"Scheduling daily digest for {recipient_id}")

        event = NotificationEvent(
            event_type="daily_digest",
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            language=language,
            data=digest_data or {},
            priority="scheduled",
        )

        self.pending_notifications.append(event)

    async def send_scheduled_digest(
        self,
        recipient_id: int,
        recipient_type: str,
        language: str = "ru",
        digest_data: Optional[Dict] = None,
        channels: Optional[List[str]] = None,
    ) -> bool:
        """Send scheduled daily digest at configured time.

        Args:
            recipient_id: ID of recipient
            recipient_type: Type of recipient
            language: Language code
            digest_data: Digest summary data
            channels: List of channels to send to

        Returns:
            True if sent successfully, False otherwise
        """
        logger.info(f"Sending scheduled digest to {recipient_id}")

        try:
            if channels is None:
                channels = ["telegram"]

            event = NotificationEvent(
                event_type="daily_digest",
                recipient_id=recipient_id,
                recipient_type=recipient_type,
                language=language,
                data=digest_data or {},
                priority="scheduled",
                channels=channels,
            )

            message = self._format_digest_message(event)

            success = await self._send_to_channels(
                recipient_id,
                channels,
                message,
                subject="daily_digest",
            )

            await self._log_notification(
                event,
                "digest",
                "sent" if success else "failed",
                message,
            )

            if not success:
                await self._handle_failed_notification(event, message)

            return success

        except Exception as e:
            logger.error(f"Error sending scheduled digest: {e}")
            return False

    async def send_health_check(
        self,
        admin_id: int,
        language: str = "ru",
    ) -> bool:
        """Send health check/heartbeat notification.

        Args:
            admin_id: ID of admin to notify
            language: Language code

        Returns:
            True if sent successfully, False otherwise
        """
        logger.info(f"Sending health check to admin {admin_id}")

        try:
            template = AdminAlertTemplate(language)
            message = template.health_check()

            event = NotificationEvent(
                event_type="health_check",
                recipient_id=admin_id,
                recipient_type="admin",
                language=language,
                data={"timestamp": datetime.now(timezone.utc).isoformat()},
                channels=["telegram"],
            )

            success = await self._send_to_channels(
                admin_id,
                ["telegram"],
                message,
                subject="health_check",
            )

            logger.info(f"Health check sent: {success}")
            return success

        except Exception as e:
            logger.error(f"Error sending health check: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(
            multiplier=settings.notification_retry_delay_min,
            min=settings.notification_retry_delay_min,
            max=settings.notification_retry_delay_max,
        ),
        retry=retry_if_exception_type(OSError),
    )
    async def _send_to_channels(
        self,
        recipient_id: int,
        channels: List[str],
        message: str,
        subject: Optional[str] = None,
    ) -> bool:
        """Send message to multiple channels with retry logic.

        Args:
            recipient_id: ID of recipient
            channels: List of channel names
            message: Message to send
            subject: Optional subject

        Returns:
            True if sent to at least one channel, False if all failed
        """
        results = []

        for channel_name in channels:
            if channel_name not in self.adapters:
                logger.warning(f"Channel {channel_name} not available")
                continue

            adapter = self.adapters[channel_name]

            if not adapter.is_available:
                logger.warning(f"Adapter {channel_name} is unavailable")
                continue

            try:
                success = await adapter.send(
                    recipient_id,
                    message,
                    subject=subject,
                )
                results.append(success)
            except Exception as e:
                logger.error(
                    f"Error sending to {channel_name} for {recipient_id}: {e}"
                )
                results.append(False)

        return any(results) if results else False

    async def _handle_failed_notification(
        self,
        event: NotificationEvent,
        message: str,
    ) -> None:
        """Handle failed notification with escalation to manual alert.

        Args:
            event: Original notification event
            message: Message that failed to send
        """
        self.failed_notifications.append({
            "event": event,
            "message": message,
            "timestamp": datetime.now(timezone.utc),
        })

        if len(self.failed_notifications) >= self.retry_attempts:
            await self._send_manual_alert(event, message)

    async def _send_manual_alert(
        self,
        event: NotificationEvent,
        message: str,
    ) -> None:
        """Send manual alert to admins when automated delivery fails.

        Args:
            event: Original notification event
            message: Message that failed to send
        """
        logger.warning(
            f"Manual alert needed for failed notification: {event.event_type}"
        )

        template = AdminAlertTemplate(event.language)
        alert_message = template.manual_alert(
            attempts=self.retry_attempts,
            message=message[:100],
            recipient=str(event.recipient_id),
        )

        event_alert = NotificationEvent(
            event_type="manual_alert",
            recipient_id=1,
            recipient_type="admin",
            language=event.language,
            data={"original_event": event.event_type},
            channels=["telegram"],
        )

        await self._send_to_channels(
            1,
            ["telegram"],
            alert_message,
            subject="manual_alert",
        )

    def _format_notification_message(self, event: NotificationEvent) -> str:
        """Format notification message based on event type.

        Args:
            event: Notification event

        Returns:
            Formatted message string
        """
        template_map = {
            "booking_created": self._format_booking_created,
            "booking_cancelled": self._format_booking_cancelled,
            "booking_rescheduled": self._format_booking_rescheduled,
            "complaint_received": self._format_complaint_received,
        }

        formatter = template_map.get(event.event_type)
        if formatter:
            return formatter(event)

        logger.warning(f"Unknown event type: {event.event_type}")
        return get_text("fallback.no_data", event.language)

    def _format_booking_created(self, event: NotificationEvent) -> str:
        """Format booking created message."""
        template = BookingNotificationTemplate(event.language)
        return template.booking_created(
            client_name=event.data.get("client_name", "Unknown"),
            booking_date=event.data.get("booking_date", "N/A"),
            booking_time=event.data.get("booking_time", "N/A"),
            specialist_name=event.data.get("specialist_name", "Unknown"),
        )

    def _format_booking_cancelled(self, event: NotificationEvent) -> str:
        """Format booking cancelled message."""
        template = BookingNotificationTemplate(event.language)
        return template.booking_cancelled(
            client_name=event.data.get("client_name", "Unknown"),
            booking_date=event.data.get("booking_date", "N/A"),
            booking_time=event.data.get("booking_time", "N/A"),
            specialist_name=event.data.get("specialist_name", "Unknown"),
        )

    def _format_booking_rescheduled(self, event: NotificationEvent) -> str:
        """Format booking rescheduled message."""
        template = BookingNotificationTemplate(event.language)
        return template.booking_rescheduled(
            client_name=event.data.get("client_name", "Unknown"),
            new_date=event.data.get("new_date", "N/A"),
            new_time=event.data.get("new_time", "N/A"),
            specialist_name=event.data.get("specialist_name", "Unknown"),
        )

    def _format_complaint_received(self, event: NotificationEvent) -> str:
        """Format complaint received message."""
        template = ComplaintNotificationTemplate(event.language)
        return template.complaint_received(
            client_name=event.data.get("client_name", "Unknown"),
            complaint_subject=event.data.get("complaint_subject", "General"),
            severity=event.data.get("severity", "normal"),
        )

    def _format_digest_message(self, event: NotificationEvent) -> str:
        """Format daily digest message."""
        template = DigestNotificationTemplate(event.language)
        return template.daily_digest(
            date=event.data.get("date", "N/A"),
            new_bookings=event.data.get("new_bookings", 0),
            cancelled_bookings=event.data.get("cancelled_bookings", 0),
            complaints=event.data.get("complaints", 0),
            urgent_events=event.data.get("urgent_events", 0),
        )

    async def _log_notification(
        self,
        event: NotificationEvent,
        message_type: str,
        status: str,
        message: Optional[str] = None,
        error_details: Optional[str] = None,
    ) -> None:
        """Log notification to database/sheets via callback.

        Args:
            event: Notification event
            message_type: Type of message (immediate, urgent, digest)
            status: Delivery status (pending, sent, failed, retrying)
            message: Message content
            error_details: Error details if failed
        """
        if not self.log_callback:
            return

        log_entry = NotificationLogDTO(
            recipient_id=event.recipient_id,
            recipient_type=event.recipient_type,
            channel=",".join(event.channels),
            message_type=message_type,
            urgency_level="urgent" if message_type == "urgent" else "normal",
            subject=event.event_type,
            message_preview=message[:100] if message else "",
            delivery_status=status,
            related_booking_id=event.related_booking_id,
            related_complaint_id=event.related_complaint_id,
            error_details=error_details,
            sent_at=datetime.now(timezone.utc) if status == "sent" else None,
            created_at=datetime.now(timezone.utc),
        )

        try:
            await self.log_callback(log_entry)
        except Exception as e:
            logger.error(f"Error logging notification: {e}")

    def get_pending_notifications(self) -> List[NotificationEvent]:
        """Get list of pending scheduled notifications.

        Returns:
            List of pending notification events
        """
        return self.pending_notifications.copy()

    def clear_pending_notifications(self) -> None:
        """Clear pending notifications list."""
        self.pending_notifications.clear()

    def get_failed_notifications(self) -> List[Dict]:
        """Get list of failed notifications.

        Returns:
            List of failed notification records
        """
        return self.failed_notifications.copy()

    def clear_failed_notifications(self) -> None:
        """Clear failed notifications list."""
        self.failed_notifications.clear()

    def set_adapter_availability(self, channel: str, available: bool) -> None:
        """Set adapter availability status.

        Args:
            channel: Channel name
            available: Availability status
        """
        if channel in self.adapters:
            self.adapters[channel].is_available = available
            logger.info(f"Adapter {channel} availability set to {available}")
