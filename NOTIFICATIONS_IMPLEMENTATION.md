# Multi-Channel Notification Service Implementation

## Overview

This document describes the multi-channel notification service with urgency tiers, scheduled digests, and comprehensive retry/logging capabilities.

## Architecture

The notification system is composed of three main layers:

### 1. Platform Adapters (`services/notifications/adapters.py`)

Adapters handle platform-specific communication:

- **TelegramAdapter**: Sends notifications via Telegram to users
- **WhatsAppAdapter**: Sends notifications via WhatsApp to recipients
- **InstagramAdapter**: Sends notifications via Instagram Direct Messages

Each adapter:
- Validates recipient IDs before sending
- Tracks sent messages (especially in mock mode for testing)
- Reports availability status
- Supports mock mode for testing without actual delivery
- Includes timestamps for all messages

### 2. Notification Templates (`services/notifications/templates.py`)

Templates generate localized messages:

- **BookingNotificationTemplate**: Creates booking-related messages
  - `booking_created()`
  - `booking_cancelled()`
  - `booking_rescheduled()`

- **ComplaintNotificationTemplate**: Creates complaint messages
  - `complaint_received()`

- **DigestNotificationTemplate**: Creates daily digest messages
  - `daily_digest()`

- **AdminAlertTemplate**: Creates admin-specific messages
  - `manual_alert()` - Escalation for failed notifications
  - `health_check()` - System health notification
  - `health_check_failed()` - Health check failure alert

- **Utility Functions**:
  - `add_urgent_tag(message, language)` - Prepends urgent marker
  - `should_escalate_to_urgent()` - Decision logic based on event type and rules

### 3. Notification Service (`services/notifications/notifier.py`)

The main `Notifier` class orchestrates multi-channel delivery:

```python
class Notifier:
    async def send_immediate_alert(event: NotificationEvent) -> bool
    async def send_urgent_escalation(event: NotificationEvent) -> bool
    async def send_scheduled_digest(recipient_id, digest_data, channels) -> bool
    async def send_health_check(admin_id, language) -> bool
```

## Three-Tier Notification System

### Tier 1: Immediate Alerts

Sent immediately upon event occurrence:

```python
event = NotificationEvent(
    event_type="booking_created",
    recipient_id=123,
    recipient_type="specialist",
    language="ru",
    data={"client_name": "Ivan", ...},
    channels=["telegram"]
)
await notifier.send_immediate_alert(event)
```

**Features:**
- Direct send to specified channels
- Async delivery with retry logic
- Logged to admin logs
- Falls back to failed notifications on error

### Tier 2: Urgent Escalation

Escalates based on urgency rules with [❗️ СРОЧНО] / [❗️ ШҰРАЙЛЫ] tag:

```python
await notifier.send_urgent_escalation(event)
```

**Escalation Rules:**
- **Same-day bookings after 08:00**: Escalates to urgent
- **High/critical/urgent severity complaints**: Escalates to urgent

**Features:**
- Prepends urgent marker to message
- Same retry logic as immediate alerts
- Logged with urgency_level="urgent"

### Tier 3: Scheduled Daily Digests

Scheduled delivery at configured time (default 08:00):

```python
await notifier.send_scheduled_digest(
    recipient_id=1,
    recipient_type="admin",
    language="ru",
    digest_data={
        "date": "2024-01-15",
        "new_bookings": 5,
        "cancelled_bookings": 1,
        "complaints": 0,
        "urgent_events": 1,
    },
    channels=["telegram"]
)
```

**Features:**
- Batch summary of daily activity
- Configurable schedule via settings
- Multi-channel delivery support
- Logged as "digest" message type

## Urgency Determination

### Rules

```python
from services.notifications.templates import should_escalate_to_urgent

# Booking: same-day after 08:00
is_urgent = should_escalate_to_urgent(
    "booking",
    booking_datetime=datetime(2024, 1, 15, 9, 30),
    current_time=datetime(2024, 1, 15, 10, 0)  # True
)

# Complaint: severity-based
is_urgent = should_escalate_to_urgent(
    "complaint",
    complaint_severity="high"  # True (high, critical, urgent)
)
```

## Multi-Channel Support

Send to multiple channels simultaneously:

```python
event = NotificationEvent(
    ...
    channels=["telegram", "whatsapp", "instagram"]
)
await notifier.send_immediate_alert(event)
```

**Delivery Logic:**
- Sends to all available channels
- Returns True if sent to at least one channel
- Logs failures per channel
- Continues on individual adapter failures

## Retry Logic with Exponential Backoff

Configuration (in `settings.py`):
```python
notification_retry_attempts = 3          # Max attempts
notification_retry_delay_min = 2         # Min delay (seconds)
notification_retry_delay_max = 10        # Max delay (seconds)
```

**Behavior:**
- Automatically retries failed sends
- Exponential backoff: delay grows between attempts
- Converts individual failures to notification event
- Escalates to manual alert after all retries exhausted

## Logging and Admin Alerts

### Notification Logging

Each notification is logged via callback:

```python
async def log_notification(log_entry: NotificationLogDTO):
    # Log to Sheets "Логи Админа" worksheet
    await sheets_manager.log_notification(log_entry)

notifier = Notifier(log_callback=log_notification)
```

**Logged Data:**
- Recipient and recipient type
- Channel(s) used
- Message type (immediate, urgent, digest)
- Urgency level
- Subject and message preview
- Delivery status (pending, sent, failed, retrying)
- Retry count
- Related booking/complaint IDs
- Error details (if failed)
- Timestamps

### Manual Alerts

After retry attempts exhausted:

```
🚨 Требуется ручное вмешательство

Не удалось доставить уведомление после 3 попыток.

Сообщение: Failed notification text preview
Получатель: 123456789
```

## Health Checks

Monitor notification system health:

```python
result = await notifier.send_health_check(admin_id=1, language="ru")
# Message: "💚 Система уведомлений работает нормально"
```

## Adapter Management

Control adapter availability at runtime:

```python
notifier.set_adapter_availability("telegram", False)  # Disable
notifier.set_adapter_availability("telegram", True)   # Enable

# Check status
is_available = notifier.adapters["telegram"].is_available
```

## Testing

### Mock Adapters

Enable mock mode for testing:

```python
from services.notifications import TelegramAdapter

adapter = TelegramAdapter()
adapter.enable_mock_mode()

# Send without actual delivery
result = await adapter.send(123, "Test message")

# Inspect sent messages
messages = adapter.get_sent_messages()
# [{"recipient_id": 123, "message": "Test message", "timestamp": ...}]

# Clear for next test
adapter.clear_sent_messages()
```

### Test Suites

**Total: 87 tests across 3 modules**

- **test_notifications_adapters.py** (28 tests)
  - Adapter creation and configuration
  - Mock mode functionality
  - Recipient validation
  - Message tracking
  - Timestamp handling

- **test_notifications_notifier.py** (29 tests)
  - Event creation
  - Immediate alerts
  - Urgent escalation
  - Scheduled digests
  - Health checks
  - Multi-channel sending
  - Retry logic
  - Message formatting
  - Failed notification handling
  - Adapter availability management

- **test_notifications_templates.py** (30 tests)
  - Template rendering
  - Urgent tag application
  - Escalation decision logic
  - Language support (RU/KZ)
  - Edge cases and error handling

## Configuration

### Settings

Add to `.env`:

```bash
# Notification retry settings
NOTIFICATION_RETRY_ATTEMPTS=3
NOTIFICATION_RETRY_DELAY_MIN=2
NOTIFICATION_RETRY_DELAY_MAX=10

# Digest schedule (24-hour format)
DIGEST_SCHEDULE_HOUR=8
DIGEST_SCHEDULE_MINUTE=0
```

### Localization

Russian locales (`locales/ru.json`):
```json
{
  "notification": {
    "booking_created": "🔔 Новая запись создана\n\n...",
    "booking_cancelled": "🔔 Запись отменена\n\n...",
    "booking_rescheduled": "🔔 Запись перенесена\n\n...",
    "complaint_received": "🔔 Получена жалоба\n\n...",
    "urgent_tag": "❗️ СРОЧНО",
    "immediate_alert": "⚠️ Срочное уведомление",
    "daily_digest": "📋 Ежедневный отчёт",
    "digest_summary": "Сводка за день {date}\n\n...",
    "delivery_failed": "❌ Не удалось доставить уведомление",
    "retry_attempt": "↻ Повторная попытка отправки ({attempt}/{max_attempts})",
    "manual_alert": "🚨 Требуется ручное вмешательство\n\n...",
    "health_check": "💚 Система уведомлений работает нормально",
    "health_check_failed": "❌ Проблема с системой уведомлений: {error}",
    "adapter_unavailable": "⚠️ Адаптер {adapter_name} недоступен"
  }
}
```

Kazakh locales (`locales/kz.json`) - Similar structure with Kazakh translations.

## Usage Examples

### Example 1: Send Immediate Booking Notification

```python
from services.notifications import Notifier, NotificationEvent

notifier = Notifier()

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
```

### Example 2: Send Urgent Complaint Alert

```python
from services.notifications import Notifier, NotificationEvent

notifier = Notifier()

event = NotificationEvent(
    event_type="complaint_received",
    recipient_id=1,
    recipient_type="admin",
    language="ru",
    data={
        "client_name": "Maria Smirnova",
        "complaint_subject": "Poor service",
        "severity": "high",
    },
    channels=["telegram"],
)

await notifier.send_urgent_escalation(event)
```

### Example 3: Send Daily Digest

```python
await notifier.send_scheduled_digest(
    recipient_id=1,
    recipient_type="admin",
    language="ru",
    digest_data={
        "date": "2024-01-15",
        "new_bookings": 5,
        "cancelled_bookings": 1,
        "complaints": 0,
        "urgent_events": 1,
    },
    channels=["telegram"],
)
```

### Example 4: Multi-Channel Delivery with Logging

```python
async def log_to_sheets(log_entry):
    # Your logging logic
    pass

notifier = Notifier(log_callback=log_to_sheets)

event = NotificationEvent(
    event_type="booking_created",
    recipient_id=123,
    recipient_type="specialist",
    language="ru",
    data={...},
    channels=["telegram", "whatsapp"],
)

await notifier.send_immediate_alert(event)
# Sends to both channels, logs results
```

## Integration Points

### With Google Sheets

Log notifications to "Логи Админа" worksheet:

```python
from integrations.google.sheets_manager import GoogleSheetsManager

sheets_manager = GoogleSheetsManager(settings.google_sheets_id)

async def log_callback(log_entry):
    await sheets_manager.log_notification(log_entry)

notifier = Notifier(log_callback=log_callback)
```

### With Conversation System

Trigger notifications from conversation states:

```python
from core.conversation import ConversationFSM
from services.notifications import Notifier, NotificationEvent

# In conversation handler
if state_transition == "booking_confirmed":
    event = NotificationEvent(...)
    await notifier.send_immediate_alert(event)
```

### With Monitoring (Future)

Health checks for monitoring system:

```python
# Periodically run health check
await notifier.send_health_check(admin_id=1, language="ru")
```

## Error Handling

**Adapter Failures:**
- Individual adapter failures don't block other channels
- Failed notifications tracked in `notifier.failed_notifications`
- Auto-escalation to manual alert after retry exhaustion

**Graceful Degradation:**
- Invalid recipients logged but don't raise exceptions
- Unavailable adapters skipped
- Retry logic transparent to caller

**Logging:**
- All errors logged via Python logging module
- Optional callback for external logging
- Detailed error context in notification logs

## Performance Considerations

- **Async delivery**: Non-blocking sends via `asyncio`
- **Batch digests**: Consolidate multiple notifications into one
- **Adapter pooling**: Reuse adapter instances
- **Caching**: Template rendering cached locally
- **Retry backoff**: Exponential backoff prevents API throttling

## Security Notes

- Recipient IDs validated before sending
- No sensitive data in message previews (capped at 100 chars)
- Credentials managed via environment variables
- Platform-specific auth handled by adapters (not in core)
- Audit trail via admin logs
