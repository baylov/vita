"""Examples of using the multi-channel notification service."""

import asyncio
from datetime import datetime, timezone, timedelta

from services.notifications.notifier import Notifier, NotificationEvent
from services.notifications.adapters import TelegramAdapter, WhatsAppAdapter
from services.notifications.templates import should_escalate_to_urgent


async def example_immediate_alert():
    """Example: Send immediate booking notification."""
    print("=" * 60)
    print("Example 1: Immediate Alert")
    print("=" * 60)

    notifier = Notifier()

    event = NotificationEvent(
        event_type="booking_created",
        recipient_id=123456789,
        recipient_type="specialist",
        language="ru",
        data={
            "client_name": "Ivan Petrov",
            "booking_date": "2024-01-15",
            "booking_time": "10:30",
            "specialist_name": "Dr. Alexandra Sidorova",
        },
        channels=["telegram"],
    )

    result = await notifier.send_immediate_alert(event)
    print(f"✓ Immediate alert sent: {result}\n")


async def example_urgent_escalation():
    """Example: Send urgent escalation for high-severity complaint."""
    print("=" * 60)
    print("Example 2: Urgent Escalation")
    print("=" * 60)

    notifier = Notifier()

    current_time = datetime.now(timezone.utc)
    booking_time = current_time.replace(hour=9, minute=30)

    is_urgent = should_escalate_to_urgent(
        event_type="booking",
        booking_datetime=booking_time,
        current_time=current_time,
    )

    print(f"Is urgent (same-day after 08:00): {is_urgent}")

    if is_urgent:
        event = NotificationEvent(
            event_type="booking_created",
            recipient_id=123456789,
            recipient_type="specialist",
            language="ru",
            data={
                "client_name": "Ivan Petrov",
                "booking_date": "2024-01-15",
                "booking_time": "09:30",
                "specialist_name": "Dr. Alexandra Sidorova",
            },
            channels=["telegram"],
        )

        result = await notifier.send_urgent_escalation(event)
        print(f"✓ Urgent escalation sent: {result}\n")


async def example_scheduled_digest():
    """Example: Schedule and send daily digest."""
    print("=" * 60)
    print("Example 3: Scheduled Daily Digest")
    print("=" * 60)

    notifier = Notifier()

    digest_data = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "new_bookings": 5,
        "cancelled_bookings": 1,
        "complaints": 2,
        "urgent_events": 1,
    }

    await notifier.schedule_daily_digest(
        recipient_id=1,
        recipient_type="admin",
        language="ru",
        digest_data=digest_data,
    )

    pending = notifier.get_pending_notifications()
    print(f"✓ Scheduled digest for {len(pending)} recipient(s)")

    result = await notifier.send_scheduled_digest(
        recipient_id=1,
        recipient_type="admin",
        language="ru",
        digest_data=digest_data,
        channels=["telegram"],
    )
    print(f"✓ Digest sent: {result}\n")


async def example_multi_channel():
    """Example: Send to multiple channels."""
    print("=" * 60)
    print("Example 4: Multi-Channel Sending")
    print("=" * 60)

    telegram = TelegramAdapter()
    telegram.enable_mock_mode()

    whatsapp = WhatsAppAdapter()
    whatsapp.enable_mock_mode()

    notifier = Notifier(adapters={"telegram": telegram, "whatsapp": whatsapp})

    event = NotificationEvent(
        event_type="booking_created",
        recipient_id=123456789,
        recipient_type="specialist",
        language="ru",
        data={
            "client_name": "Ivan Petrov",
            "booking_date": "2024-01-15",
            "booking_time": "10:30",
            "specialist_name": "Dr. Alexandra Sidorova",
        },
        channels=["telegram", "whatsapp"],
    )

    result = await notifier.send_immediate_alert(event)
    print(f"✓ Multi-channel send result: {result}")
    print(f"  - Telegram messages: {len(telegram.get_sent_messages())}")
    print(f"  - WhatsApp messages: {len(whatsapp.get_sent_messages())}\n")


async def example_complaint_urgency():
    """Example: Complaint severity escalation."""
    print("=" * 60)
    print("Example 5: Complaint Severity Escalation")
    print("=" * 60)

    severities = ["low", "normal", "high", "critical"]

    for severity in severities:
        is_urgent = should_escalate_to_urgent(
            event_type="complaint",
            complaint_severity=severity,
        )
        print(f"Severity '{severity}' escalates to urgent: {is_urgent}")

    print()


async def example_health_check():
    """Example: Send health check notification."""
    print("=" * 60)
    print("Example 6: Health Check Notification")
    print("=" * 60)

    telegram = TelegramAdapter()
    telegram.enable_mock_mode()

    notifier = Notifier(adapters={"telegram": telegram})

    result = await notifier.send_health_check(admin_id=1, language="ru")
    print(f"✓ Health check sent: {result}\n")


async def example_with_logging():
    """Example: Send notification with logging callback."""
    print("=" * 60)
    print("Example 7: Notification with Logging")
    print("=" * 60)

    async def log_notification(log_entry):
        """Callback to log notifications."""
        print(f"Logged notification:")
        print(f"  - Recipient: {log_entry.recipient_id}")
        print(f"  - Type: {log_entry.message_type}")
        print(f"  - Status: {log_entry.delivery_status}")
        print(f"  - Subject: {log_entry.subject}")

    telegram = TelegramAdapter()
    telegram.enable_mock_mode()

    notifier = Notifier(adapters={"telegram": telegram}, log_callback=log_notification)

    event = NotificationEvent(
        event_type="booking_created",
        recipient_id=123,
        recipient_type="specialist",
        language="ru",
        data={
            "client_name": "Ivan Petrov",
            "booking_date": "2024-01-15",
            "booking_time": "10:30",
            "specialist_name": "Dr. Sidorova",
        },
        channels=["telegram"],
    )

    await notifier.send_immediate_alert(event)
    print()


async def example_failed_notification_handling():
    """Example: Handle failed notifications."""
    print("=" * 60)
    print("Example 8: Failed Notification Handling")
    print("=" * 60)

    telegram = TelegramAdapter()
    telegram.is_available = False

    notifier = Notifier(adapters={"telegram": telegram})

    event = NotificationEvent(
        event_type="booking_created",
        recipient_id=123,
        recipient_type="specialist",
        language="ru",
        channels=["telegram"],
    )

    result = await notifier.send_immediate_alert(event)
    print(f"✓ Send result (expected failure): {result}")

    failed = notifier.get_failed_notifications()
    print(f"✓ Failed notifications count: {len(failed)}")
    print(f"✓ Failed event type: {failed[0]['event'].event_type}\n")


async def example_adapter_management():
    """Example: Manage adapter availability."""
    print("=" * 60)
    print("Example 9: Adapter Availability Management")
    print("=" * 60)

    notifier = Notifier()

    print(f"Telegram available: {notifier.adapters['telegram'].is_available}")

    notifier.set_adapter_availability("telegram", False)
    print(f"After disabling: {notifier.adapters['telegram'].is_available}")

    notifier.set_adapter_availability("telegram", True)
    print(f"After enabling: {notifier.adapters['telegram'].is_available}\n")


async def example_complaint_notification():
    """Example: Send complaint notification."""
    print("=" * 60)
    print("Example 10: Complaint Notification")
    print("=" * 60)

    notifier = Notifier()

    event = NotificationEvent(
        event_type="complaint_received",
        recipient_id=1,
        recipient_type="admin",
        language="ru",
        data={
            "client_name": "Maria Smirnova",
            "complaint_subject": "Poor appointment schedule clarity",
            "severity": "high",
        },
        channels=["telegram"],
    )

    is_urgent = should_escalate_to_urgent(
        event_type="complaint",
        complaint_severity=event.data.get("severity"),
    )

    print(f"Is urgent: {is_urgent}")

    if is_urgent:
        result = await notifier.send_urgent_escalation(event)
        print(f"✓ Urgent complaint notification sent: {result}\n")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("NOTIFICATION SERVICE EXAMPLES")
    print("=" * 60 + "\n")

    await example_immediate_alert()
    await example_urgent_escalation()
    await example_scheduled_digest()
    await example_multi_channel()
    await example_complaint_urgency()
    await example_health_check()
    await example_with_logging()
    await example_failed_notification_handling()
    await example_adapter_management()
    await example_complaint_notification()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
