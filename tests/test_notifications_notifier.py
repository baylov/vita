"""Tests for the notification service notifier."""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from services.notifications.notifier import Notifier, NotificationEvent
from services.notifications.adapters import (
    TelegramAdapter,
    WhatsAppAdapter,
    InstagramAdapter,
)
from models import NotificationLogDTO


class TestNotificationEvent:
    """Tests for NotificationEvent dataclass."""

    def test_notification_event_creation(self):
        """Test creating a notification event."""
        event = NotificationEvent(
            event_type="booking_created",
            recipient_id=123,
            recipient_type="specialist",
            language="ru",
        )

        assert event.event_type == "booking_created"
        assert event.recipient_id == 123
        assert event.recipient_type == "specialist"
        assert event.language == "ru"
        assert event.priority == "normal"
        assert event.channels == ["telegram"]

    def test_notification_event_with_data(self):
        """Test creating event with custom data."""
        data = {"client_name": "Ivan", "booking_date": "2024-01-01"}
        event = NotificationEvent(
            event_type="booking_created",
            recipient_id=123,
            recipient_type="admin",
            data=data,
        )

        assert event.data == data


class TestNotifierInitialization:
    """Tests for Notifier initialization."""

    def test_notifier_creation_with_defaults(self):
        """Test creating notifier with default adapters."""
        notifier = Notifier()

        assert "telegram" in notifier.adapters
        assert "whatsapp" in notifier.adapters
        assert "instagram" in notifier.adapters
        assert notifier.retry_attempts == 3
        assert notifier.pending_notifications == []
        assert notifier.failed_notifications == []

    def test_notifier_creation_with_custom_adapters(self):
        """Test creating notifier with custom adapters."""
        custom_adapters = {"telegram": TelegramAdapter()}
        notifier = Notifier(adapters=custom_adapters)

        assert "telegram" in notifier.adapters
        assert "whatsapp" not in notifier.adapters

    def test_notifier_creation_with_log_callback(self):
        """Test creating notifier with logging callback."""
        callback = Mock()
        notifier = Notifier(log_callback=callback)

        assert notifier.log_callback == callback


class TestImmediateAlerts:
    """Tests for immediate per-event alerts."""

    @pytest.mark.asyncio
    async def test_send_immediate_alert_success(self):
        """Test successful immediate alert sending."""
        adapter = TelegramAdapter()
        adapter.enable_mock_mode()

        notifier = Notifier(adapters={"telegram": adapter})

        event = NotificationEvent(
            event_type="booking_created",
            recipient_id=123,
            recipient_type="specialist",
            language="ru",
            data={
                "client_name": "Ivan",
                "booking_date": "2024-01-01",
                "booking_time": "10:00",
                "specialist_name": "Dr. Smith",
            },
            channels=["telegram"],
        )

        result = await notifier.send_immediate_alert(event)

        assert result is True
        assert len(adapter.get_sent_messages()) == 1

    @pytest.mark.asyncio
    async def test_send_immediate_alert_invalid_recipient(self):
        """Test immediate alert with invalid recipient."""
        adapter = TelegramAdapter()
        notifier = Notifier(adapters={"telegram": adapter})

        event = NotificationEvent(
            event_type="booking_created",
            recipient_id=-1,
            recipient_type="specialist",
            channels=["telegram"],
        )

        result = await notifier.send_immediate_alert(event)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_immediate_alert_with_logging(self):
        """Test immediate alert with notification logging."""
        adapter = TelegramAdapter()
        adapter.enable_mock_mode()

        log_callback = AsyncMock()
        notifier = Notifier(adapters={"telegram": adapter}, log_callback=log_callback)

        event = NotificationEvent(
            event_type="booking_created",
            recipient_id=123,
            recipient_type="specialist",
            language="ru",
            data={
                "client_name": "Ivan",
                "booking_date": "2024-01-01",
                "booking_time": "10:00",
                "specialist_name": "Dr. Smith",
            },
            channels=["telegram"],
        )

        await notifier.send_immediate_alert(event)

        assert log_callback.call_count == 1
        call_args = log_callback.call_args[0][0]
        assert isinstance(call_args, NotificationLogDTO)
        assert call_args.message_type == "immediate"
        assert call_args.delivery_status == "sent"


class TestUrgentEscalation:
    """Tests for urgent escalation notifications."""

    @pytest.mark.asyncio
    async def test_send_urgent_escalation_success(self):
        """Test successful urgent escalation sending."""
        adapter = TelegramAdapter()
        adapter.enable_mock_mode()

        notifier = Notifier(adapters={"telegram": adapter})

        event = NotificationEvent(
            event_type="complaint_received",
            recipient_id=123,
            recipient_type="admin",
            language="ru",
            data={
                "client_name": "Ivan",
                "complaint_subject": "Poor service",
                "severity": "high",
            },
            channels=["telegram"],
        )

        result = await notifier.send_urgent_escalation(event)

        assert result is True
        messages = adapter.get_sent_messages()
        assert len(messages) == 1
        assert "СРОЧНО" in messages[0]["message"]

    @pytest.mark.asyncio
    async def test_send_urgent_escalation_with_logging(self):
        """Test urgent escalation with logging."""
        adapter = TelegramAdapter()
        adapter.enable_mock_mode()

        log_callback = AsyncMock()
        notifier = Notifier(adapters={"telegram": adapter}, log_callback=log_callback)

        event = NotificationEvent(
            event_type="complaint_received",
            recipient_id=123,
            recipient_type="admin",
            language="ru",
            data={
                "client_name": "Ivan",
                "complaint_subject": "Poor service",
                "severity": "high",
            },
            channels=["telegram"],
        )

        await notifier.send_urgent_escalation(event)

        assert log_callback.call_count == 1
        call_args = log_callback.call_args[0][0]
        assert call_args.message_type == "urgent"
        assert call_args.urgency_level == "urgent"


class TestScheduledDigests:
    """Tests for scheduled daily digest notifications."""

    @pytest.mark.asyncio
    async def test_schedule_daily_digest(self):
        """Test scheduling a daily digest."""
        notifier = Notifier()

        await notifier.schedule_daily_digest(
            recipient_id=123,
            recipient_type="admin",
            language="ru",
            digest_data={
                "date": "2024-01-01",
                "new_bookings": 5,
                "cancelled_bookings": 1,
                "complaints": 0,
                "urgent_events": 1,
            },
        )

        pending = notifier.get_pending_notifications()
        assert len(pending) == 1
        assert pending[0].event_type == "daily_digest"
        assert pending[0].recipient_id == 123

    @pytest.mark.asyncio
    async def test_send_scheduled_digest(self):
        """Test sending a scheduled digest."""
        adapter = TelegramAdapter()
        adapter.enable_mock_mode()

        notifier = Notifier(adapters={"telegram": adapter})

        result = await notifier.send_scheduled_digest(
            recipient_id=123,
            recipient_type="admin",
            language="ru",
            digest_data={
                "date": "2024-01-01",
                "new_bookings": 5,
                "cancelled_bookings": 1,
                "complaints": 0,
                "urgent_events": 1,
            },
            channels=["telegram"],
        )

        assert result is True
        messages = adapter.get_sent_messages()
        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_send_scheduled_digest_with_logging(self):
        """Test scheduled digest with logging."""
        adapter = TelegramAdapter()
        adapter.enable_mock_mode()

        log_callback = AsyncMock()
        notifier = Notifier(adapters={"telegram": adapter}, log_callback=log_callback)

        await notifier.send_scheduled_digest(
            recipient_id=123,
            recipient_type="admin",
            language="ru",
            digest_data={
                "date": "2024-01-01",
                "new_bookings": 5,
                "cancelled_bookings": 1,
                "complaints": 0,
                "urgent_events": 1,
            },
            channels=["telegram"],
        )

        assert log_callback.call_count == 1
        call_args = log_callback.call_args[0][0]
        assert call_args.message_type == "digest"


class TestHealthCheckNotifications:
    """Tests for health check notifications."""

    @pytest.mark.asyncio
    async def test_send_health_check(self):
        """Test sending health check notification."""
        adapter = TelegramAdapter()
        adapter.enable_mock_mode()

        notifier = Notifier(adapters={"telegram": adapter})

        result = await notifier.send_health_check(admin_id=1, language="ru")

        assert result is True
        messages = adapter.get_sent_messages()
        assert len(messages) == 1
        assert "нормально" in messages[0]["message"].lower()

    @pytest.mark.asyncio
    async def test_send_health_check_failure(self):
        """Test health check failure."""
        adapter = TelegramAdapter()
        adapter.is_available = False

        notifier = Notifier(adapters={"telegram": adapter})

        result = await notifier.send_health_check(admin_id=1, language="ru")

        assert result is False


class TestMultiChannelSending:
    """Tests for multi-channel message sending."""

    @pytest.mark.asyncio
    async def test_send_to_multiple_channels_success(self):
        """Test sending to multiple channels."""
        telegram = TelegramAdapter()
        telegram.enable_mock_mode()
        whatsapp = WhatsAppAdapter()
        whatsapp.enable_mock_mode()

        notifier = Notifier(adapters={"telegram": telegram, "whatsapp": whatsapp})

        event = NotificationEvent(
            event_type="booking_created",
            recipient_id=123,
            recipient_type="specialist",
            language="ru",
            data={
                "client_name": "Ivan",
                "booking_date": "2024-01-01",
                "booking_time": "10:00",
                "specialist_name": "Dr. Smith",
            },
            channels=["telegram", "whatsapp"],
        )

        result = await notifier.send_immediate_alert(event)

        assert result is True
        assert len(telegram.get_sent_messages()) == 1
        assert len(whatsapp.get_sent_messages()) == 1

    @pytest.mark.asyncio
    async def test_send_to_unavailable_channel(self):
        """Test sending to unavailable channel."""
        telegram = TelegramAdapter()
        telegram.enable_mock_mode()
        whatsapp = WhatsAppAdapter()
        whatsapp.is_available = False

        notifier = Notifier(adapters={"telegram": telegram, "whatsapp": whatsapp})

        event = NotificationEvent(
            event_type="booking_created",
            recipient_id=123,
            recipient_type="specialist",
            language="ru",
            channels=["telegram", "whatsapp"],
        )

        result = await notifier.send_immediate_alert(event)

        assert result is True
        assert len(telegram.get_sent_messages()) == 1

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_channel(self):
        """Test sending to nonexistent channel."""
        telegram = TelegramAdapter()
        telegram.enable_mock_mode()

        notifier = Notifier(adapters={"telegram": telegram})

        event = NotificationEvent(
            event_type="booking_created",
            recipient_id=123,
            recipient_type="specialist",
            language="ru",
            channels=["nonexistent"],
        )

        result = await notifier.send_immediate_alert(event)

        assert result is False


class TestRetryLogic:
    """Tests for retry logic and failure handling."""

    @pytest.mark.asyncio
    async def test_failed_notification_escalation(self):
        """Test escalation to manual alert after retries."""
        adapter = TelegramAdapter()
        adapter.is_available = False

        log_callback = AsyncMock()
        notifier = Notifier(adapters={"telegram": adapter}, log_callback=log_callback)

        event = NotificationEvent(
            event_type="booking_created",
            recipient_id=123,
            recipient_type="specialist",
            language="ru",
            channels=["telegram"],
        )

        result = await notifier.send_immediate_alert(event)

        assert result is False
        assert len(notifier.get_failed_notifications()) == 1

    @pytest.mark.asyncio
    async def test_manual_alert_on_repeated_failures(self):
        """Test manual alert sent on repeated failures."""
        adapter = TelegramAdapter()
        adapter.enable_mock_mode()
        adapter.is_available = False

        notifier = Notifier(adapters={"telegram": adapter})

        event = NotificationEvent(
            event_type="booking_created",
            recipient_id=123,
            recipient_type="specialist",
            language="ru",
            channels=["telegram"],
        )

        await notifier.send_immediate_alert(event)

        assert len(notifier.get_failed_notifications()) == 1


class TestNotificationFormatting:
    """Tests for notification message formatting."""

    def test_format_booking_created_message(self):
        """Test formatting booking created message."""
        notifier = Notifier()

        event = NotificationEvent(
            event_type="booking_created",
            recipient_id=123,
            recipient_type="specialist",
            language="ru",
            data={
                "client_name": "Ivan",
                "booking_date": "2024-01-01",
                "booking_time": "10:00",
                "specialist_name": "Dr. Smith",
            },
        )

        message = notifier._format_notification_message(event)

        assert "Ivan" in message
        assert "2024-01-01" in message

    def test_format_booking_cancelled_message(self):
        """Test formatting booking cancelled message."""
        notifier = Notifier()

        event = NotificationEvent(
            event_type="booking_cancelled",
            recipient_id=123,
            recipient_type="specialist",
            language="ru",
            data={
                "client_name": "Ivan",
                "booking_date": "2024-01-01",
                "booking_time": "10:00",
                "specialist_name": "Dr. Smith",
            },
        )

        message = notifier._format_notification_message(event)

        assert "Ivan" in message

    def test_format_complaint_received_message(self):
        """Test formatting complaint received message."""
        notifier = Notifier()

        event = NotificationEvent(
            event_type="complaint_received",
            recipient_id=123,
            recipient_type="admin",
            language="ru",
            data={
                "client_name": "Ivan",
                "complaint_subject": "Poor service",
                "severity": "high",
            },
        )

        message = notifier._format_notification_message(event)

        assert "Ivan" in message


class TestPendingNotifications:
    """Tests for pending notifications management."""

    @pytest.mark.asyncio
    async def test_get_pending_notifications(self):
        """Test getting pending notifications."""
        notifier = Notifier()

        await notifier.schedule_daily_digest(
            recipient_id=123,
            recipient_type="admin",
            language="ru",
        )

        pending = notifier.get_pending_notifications()
        assert len(pending) == 1

    @pytest.mark.asyncio
    async def test_clear_pending_notifications(self):
        """Test clearing pending notifications."""
        notifier = Notifier()

        await notifier.schedule_daily_digest(
            recipient_id=123,
            recipient_type="admin",
            language="ru",
        )

        notifier.clear_pending_notifications()
        pending = notifier.get_pending_notifications()
        assert len(pending) == 0


class TestFailedNotifications:
    """Tests for failed notifications management."""

    @pytest.mark.asyncio
    async def test_get_failed_notifications(self):
        """Test getting failed notifications."""
        adapter = TelegramAdapter()
        adapter.is_available = False

        notifier = Notifier(adapters={"telegram": adapter})

        event = NotificationEvent(
            event_type="booking_created",
            recipient_id=123,
            recipient_type="specialist",
            language="ru",
            channels=["telegram"],
        )

        await notifier.send_immediate_alert(event)

        failed = notifier.get_failed_notifications()
        assert len(failed) == 1

    @pytest.mark.asyncio
    async def test_clear_failed_notifications(self):
        """Test clearing failed notifications."""
        adapter = TelegramAdapter()
        adapter.is_available = False

        notifier = Notifier(adapters={"telegram": adapter})

        event = NotificationEvent(
            event_type="booking_created",
            recipient_id=123,
            recipient_type="specialist",
            language="ru",
            channels=["telegram"],
        )

        await notifier.send_immediate_alert(event)
        notifier.clear_failed_notifications()

        failed = notifier.get_failed_notifications()
        assert len(failed) == 0


class TestAdapterAvailability:
    """Tests for adapter availability control."""

    def test_set_adapter_availability(self):
        """Test setting adapter availability."""
        notifier = Notifier()

        notifier.set_adapter_availability("telegram", False)

        assert notifier.adapters["telegram"].is_available is False

        notifier.set_adapter_availability("telegram", True)

        assert notifier.adapters["telegram"].is_available is True

    def test_set_unavailable_adapter_status(self):
        """Test that unavailable adapters are skipped."""
        telegram = TelegramAdapter()
        telegram.enable_mock_mode()

        notifier = Notifier(adapters={"telegram": telegram})
        notifier.set_adapter_availability("telegram", False)

        event = NotificationEvent(
            event_type="booking_created",
            recipient_id=123,
            recipient_type="specialist",
            language="ru",
            channels=["telegram"],
        )

        # Need to use asyncio.run since we can't use await here
        import asyncio

        result = asyncio.run(notifier.send_immediate_alert(event))

        assert result is False
