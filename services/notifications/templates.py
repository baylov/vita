"""Notification templates and formatting."""

from datetime import datetime
from typing import Optional
from core.i18n import get_text


class NotificationTemplate:
    """Base class for notification templates."""

    def __init__(self, language: str = "ru"):
        """Initialize template with language.

        Args:
            language: Language code (ru or kz)
        """
        self.language = language

    def format_message(self, key: str, **kwargs) -> str:
        """Format a localized notification message.

        Args:
            key: Translation key
            **kwargs: Placeholder values

        Returns:
            Formatted message
        """
        return get_text(f"notification.{key}", self.language, **kwargs)


class BookingNotificationTemplate(NotificationTemplate):
    """Template for booking-related notifications."""

    def booking_created(
        self,
        client_name: str,
        booking_date: str,
        booking_time: str,
        specialist_name: str
    ) -> str:
        """Format booking created notification.

        Args:
            client_name: Name of client
            booking_date: Booking date
            booking_time: Booking time
            specialist_name: Name of specialist

        Returns:
            Formatted message
        """
        return self.format_message(
            "booking_created",
            client_name=client_name,
            booking_date=booking_date,
            booking_time=booking_time,
            specialist_name=specialist_name,
        )

    def booking_cancelled(
        self,
        client_name: str,
        booking_date: str,
        booking_time: str,
        specialist_name: str
    ) -> str:
        """Format booking cancelled notification.

        Args:
            client_name: Name of client
            booking_date: Booking date
            booking_time: Booking time
            specialist_name: Name of specialist

        Returns:
            Formatted message
        """
        return self.format_message(
            "booking_cancelled",
            client_name=client_name,
            booking_date=booking_date,
            booking_time=booking_time,
            specialist_name=specialist_name,
        )

    def booking_rescheduled(
        self,
        client_name: str,
        new_date: str,
        new_time: str,
        specialist_name: str
    ) -> str:
        """Format booking rescheduled notification.

        Args:
            client_name: Name of client
            new_date: New booking date
            new_time: New booking time
            specialist_name: Name of specialist

        Returns:
            Formatted message
        """
        return self.format_message(
            "booking_rescheduled",
            client_name=client_name,
            new_date=new_date,
            new_time=new_time,
            specialist_name=specialist_name,
        )


class ComplaintNotificationTemplate(NotificationTemplate):
    """Template for complaint-related notifications."""

    def complaint_received(
        self,
        client_name: str,
        complaint_subject: str,
        severity: str
    ) -> str:
        """Format complaint received notification.

        Args:
            client_name: Name of client filing complaint
            complaint_subject: Subject of complaint
            severity: Severity level

        Returns:
            Formatted message
        """
        return self.format_message(
            "complaint_received",
            client_name=client_name,
            complaint_subject=complaint_subject,
            severity=severity,
        )


class DigestNotificationTemplate(NotificationTemplate):
    """Template for daily digest notifications."""

    def daily_digest(
        self,
        date: str,
        new_bookings: int,
        cancelled_bookings: int,
        complaints: int,
        urgent_events: int
    ) -> str:
        """Format daily digest notification.

        Args:
            date: Date of digest
            new_bookings: Number of new bookings
            cancelled_bookings: Number of cancelled bookings
            complaints: Number of complaints
            urgent_events: Number of urgent events

        Returns:
            Formatted message
        """
        return self.format_message(
            "digest_summary",
            date=date,
            new_bookings=new_bookings,
            cancelled_bookings=cancelled_bookings,
            complaints=complaints,
            urgent_events=urgent_events,
        )


class AdminAlertTemplate(NotificationTemplate):
    """Template for admin alerts."""

    def manual_alert(
        self,
        attempts: int,
        message: str,
        recipient: str
    ) -> str:
        """Format manual intervention alert.

        Args:
            attempts: Number of failed attempts
            message: Original message that failed
            recipient: Recipient identifier

        Returns:
            Formatted message
        """
        return self.format_message(
            "manual_alert",
            attempts=attempts,
            message=message,
            recipient=recipient,
        )

    def health_check(self) -> str:
        """Format health check message.

        Returns:
            Formatted message
        """
        return self.format_message("health_check")

    def health_check_failed(self, error: str) -> str:
        """Format health check failure message.

        Args:
            error: Error description

        Returns:
            Formatted message
        """
        return self.format_message("health_check_failed", error=error)


def add_urgent_tag(message: str, language: str = "ru") -> str:
    """Add urgent tag to message.

    Args:
        message: Original message
        language: Language code

    Returns:
        Message with urgent tag prepended
    """
    urgent_tag = get_text("notification.urgent_tag", language)
    return f"{urgent_tag} {message}"


def should_escalate_to_urgent(
    event_type: str,
    booking_datetime: Optional[datetime] = None,
    complaint_severity: Optional[str] = None,
    current_time: Optional[datetime] = None
) -> bool:
    """Determine if notification should be escalated to urgent.

    Rules for escalation:
    - Same-day booking after 08:00
    - High severity complaints

    Args:
        event_type: Type of event (booking, complaint)
        booking_datetime: Datetime of booking (for booking events)
        complaint_severity: Severity of complaint (for complaint events)
        current_time: Current time (defaults to now)

    Returns:
        True if should escalate to urgent, False otherwise
    """
    if current_time is None:
        from datetime import timezone
        current_time = datetime.now(timezone.utc)

    if event_type == "booking" and booking_datetime:
        booking_date = booking_datetime.date()
        current_date = current_time.date()

        if booking_date == current_date and current_time.hour >= 8:
            return True

    if event_type == "complaint" and complaint_severity:
        if complaint_severity.lower() in ["high", "critical", "urgent"]:
            return True

    return False
