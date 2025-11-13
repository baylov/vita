"""Tests for notification templates."""

import pytest
from datetime import datetime, timezone, time

from services.notifications.templates import (
    NotificationTemplate,
    BookingNotificationTemplate,
    ComplaintNotificationTemplate,
    DigestNotificationTemplate,
    AdminAlertTemplate,
    add_urgent_tag,
    should_escalate_to_urgent,
)


class TestNotificationTemplate:
    """Tests for base NotificationTemplate."""

    def test_template_creation_default_language(self):
        """Test creating template with default language."""
        template = NotificationTemplate()

        assert template.language == "ru"

    def test_template_creation_custom_language(self):
        """Test creating template with custom language."""
        template = NotificationTemplate("kz")

        assert template.language == "kz"

    def test_template_format_message(self):
        """Test formatting message with template."""
        template = NotificationTemplate("ru")

        message = template.format_message(
            "booking_created",
            client_name="Ivan",
            booking_date="2024-01-01",
            booking_time="10:00",
            specialist_name="Dr. Smith",
        )

        assert "Ivan" in message
        assert "2024-01-01" in message


class TestBookingNotificationTemplate:
    """Tests for BookingNotificationTemplate."""

    def test_booking_template_creation(self):
        """Test creating booking notification template."""
        template = BookingNotificationTemplate()

        assert template.language == "ru"

    def test_booking_created_message(self):
        """Test formatting booking created message."""
        template = BookingNotificationTemplate("ru")

        message = template.booking_created(
            client_name="Ivan",
            booking_date="2024-01-01",
            booking_time="10:00",
            specialist_name="Dr. Smith",
        )

        assert "Ivan" in message
        assert "2024-01-01" in message
        assert "10:00" in message

    def test_booking_cancelled_message(self):
        """Test formatting booking cancelled message."""
        template = BookingNotificationTemplate("ru")

        message = template.booking_cancelled(
            client_name="Ivan",
            booking_date="2024-01-01",
            booking_time="10:00",
            specialist_name="Dr. Smith",
        )

        assert "Ivan" in message

    def test_booking_rescheduled_message(self):
        """Test formatting booking rescheduled message."""
        template = BookingNotificationTemplate("ru")

        message = template.booking_rescheduled(
            client_name="Ivan",
            new_date="2024-01-02",
            new_time="11:00",
            specialist_name="Dr. Smith",
        )

        assert "Ivan" in message
        assert "2024-01-02" in message

    def test_booking_template_kazakh_language(self):
        """Test booking template with Kazakh language."""
        template = BookingNotificationTemplate("kz")

        message = template.booking_created(
            client_name="Ivan",
            booking_date="2024-01-01",
            booking_time="10:00",
            specialist_name="Dr. Smith",
        )

        assert len(message) > 0


class TestComplaintNotificationTemplate:
    """Tests for ComplaintNotificationTemplate."""

    def test_complaint_template_creation(self):
        """Test creating complaint notification template."""
        template = ComplaintNotificationTemplate()

        assert template.language == "ru"

    def test_complaint_received_message(self):
        """Test formatting complaint received message."""
        template = ComplaintNotificationTemplate("ru")

        message = template.complaint_received(
            client_name="Ivan",
            complaint_subject="Poor service",
            severity="high",
        )

        assert "Ivan" in message
        assert "Poor service" in message


class TestDigestNotificationTemplate:
    """Tests for DigestNotificationTemplate."""

    def test_digest_template_creation(self):
        """Test creating digest notification template."""
        template = DigestNotificationTemplate()

        assert template.language == "ru"

    def test_daily_digest_message(self):
        """Test formatting daily digest message."""
        template = DigestNotificationTemplate("ru")

        message = template.daily_digest(
            date="2024-01-01",
            new_bookings=5,
            cancelled_bookings=1,
            complaints=0,
            urgent_events=1,
        )

        assert "2024-01-01" in message
        assert "5" in message
        assert "1" in message


class TestAdminAlertTemplate:
    """Tests for AdminAlertTemplate."""

    def test_admin_template_creation(self):
        """Test creating admin alert template."""
        template = AdminAlertTemplate()

        assert template.language == "ru"

    def test_manual_alert_message(self):
        """Test formatting manual alert message."""
        template = AdminAlertTemplate("ru")

        message = template.manual_alert(
            attempts=3,
            message="Failed notification",
            recipient="123",
        )

        assert "3" in message
        assert "Failed notification" in message

    def test_health_check_message(self):
        """Test formatting health check message."""
        template = AdminAlertTemplate("ru")

        message = template.health_check()

        assert len(message) > 0

    def test_health_check_failed_message(self):
        """Test formatting health check failed message."""
        template = AdminAlertTemplate("ru")

        message = template.health_check_failed("Connection timeout")

        assert "Connection timeout" in message


class TestAddUrgentTag:
    """Tests for add_urgent_tag function."""

    def test_add_urgent_tag_ru(self):
        """Test adding urgent tag in Russian."""
        message = "Test message"
        result = add_urgent_tag(message, "ru")

        assert "СРОЧНО" in result
        assert "Test message" in result

    def test_add_urgent_tag_kz(self):
        """Test adding urgent tag in Kazakh."""
        message = "Test message"
        result = add_urgent_tag(message, "kz")

        assert "ШҰРАЙЛЫ" in result
        assert "Test message" in result

    def test_add_urgent_tag_preserves_message(self):
        """Test that urgent tag doesn't modify original message."""
        message = "Test message"
        result = add_urgent_tag(message)

        assert message in result


class TestShouldEscalateToUrgent:
    """Tests for should_escalate_to_urgent function."""

    def test_escalate_same_day_booking_after_8am(self):
        """Test escalation for same-day booking after 08:00."""
        today = datetime.now(timezone.utc)
        booking_time = today.replace(hour=9, minute=0, second=0, microsecond=0)
        current_time = today.replace(hour=10, minute=0, second=0, microsecond=0)

        result = should_escalate_to_urgent(
            "booking",
            booking_datetime=booking_time,
            current_time=current_time,
        )

        assert result is True

    def test_no_escalate_same_day_booking_before_8am(self):
        """Test no escalation for same-day booking before 08:00."""
        today = datetime.now(timezone.utc)
        booking_time = today.replace(hour=14, minute=0, second=0, microsecond=0)
        current_time = today.replace(hour=7, minute=0, second=0, microsecond=0)

        result = should_escalate_to_urgent(
            "booking",
            booking_datetime=booking_time,
            current_time=current_time,
        )

        assert result is False

    def test_no_escalate_future_booking(self):
        """Test no escalation for future booking."""
        from datetime import timedelta
        today = datetime.now(timezone.utc)
        booking_time = today + timedelta(days=1)
        booking_time = booking_time.replace(hour=14, minute=0, second=0, microsecond=0)

        result = should_escalate_to_urgent(
            "booking",
            booking_datetime=booking_time,
        )

        assert result is False

    def test_escalate_high_severity_complaint(self):
        """Test escalation for high severity complaint."""
        result = should_escalate_to_urgent(
            "complaint",
            complaint_severity="high",
        )

        assert result is True

    def test_escalate_critical_complaint(self):
        """Test escalation for critical complaint."""
        result = should_escalate_to_urgent(
            "complaint",
            complaint_severity="critical",
        )

        assert result is True

    def test_escalate_urgent_complaint(self):
        """Test escalation for urgent complaint."""
        result = should_escalate_to_urgent(
            "complaint",
            complaint_severity="urgent",
        )

        assert result is True

    def test_no_escalate_normal_complaint(self):
        """Test no escalation for normal complaint."""
        result = should_escalate_to_urgent(
            "complaint",
            complaint_severity="normal",
        )

        assert result is False

    def test_no_escalate_low_complaint(self):
        """Test no escalation for low severity complaint."""
        result = should_escalate_to_urgent(
            "complaint",
            complaint_severity="low",
        )

        assert result is False

    def test_no_escalate_unknown_event_type(self):
        """Test no escalation for unknown event type."""
        result = should_escalate_to_urgent(
            "unknown_type",
        )

        assert result is False

    def test_escalate_uses_current_time_default(self):
        """Test that function uses current time by default."""
        today = datetime.now(timezone.utc)
        booking_time = today.replace(hour=9, minute=0, second=0, microsecond=0)

        result = should_escalate_to_urgent(
            "booking",
            booking_datetime=booking_time,
        )

        if today.hour >= 8:
            assert result is True
        else:
            assert result is False

    def test_escalate_case_insensitive_severity(self):
        """Test that severity check is case insensitive."""
        result_high = should_escalate_to_urgent(
            "complaint",
            complaint_severity="HIGH",
        )

        result_high_lower = should_escalate_to_urgent(
            "complaint",
            complaint_severity="high",
        )

        assert result_high == result_high_lower
