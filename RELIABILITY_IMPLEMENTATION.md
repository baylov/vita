# Reliability and Error Handling Implementation

This document describes the error handling, monitoring, and health management infrastructure added to the VITA system.

## Overview

The reliability improvements include:

1. **Custom Exception Hierarchy** (`core/errors.py`)
2. **Aiogram Middleware for Error Handling** (`core/middleware.py`)
3. **Health Monitoring System** (`core/health.py`)
4. **Comprehensive Logging** with contextual metadata

## Core Error Classes

### ExternalServiceError
Raised when an external service call fails after retries are exhausted.

```python
from core.errors import ExternalServiceError

try:
    # External API call
    pass
except ExternalServiceError as e:
    print(f"Service {e.service_name} failed: {e.message}")
```

### ValidationError
Raised when input validation fails.

```python
from core.errors import ValidationError

raise ValidationError(
    message="Invalid phone number format",
    field="phone"
)
```

### ManualInterventionRequired
Raised when automatic processing fails and requires manual admin intervention.

```python
from core.errors import ManualInterventionRequired

raise ManualInterventionRequired(
    message="Booking conflict - no available slots",
    context={"specialist_id": 123, "date": "2024-01-15"},
    requires_admin_notification=True
)
```

## Retry Decorators

### retry_with_logging (Sync)
Decorator for retrying synchronous functions with exponential backoff and logging.

```python
from core.errors import retry_with_logging

@retry_with_logging(
    max_attempts=3,
    min_delay=2.0,
    max_delay=10.0,
    exception_types=(OSError, TimeoutError)
)
def fetch_data():
    # Will retry up to 3 times with exponential backoff
    pass
```

### async_retry_with_logging (Async)
Decorator for retrying asynchronous functions with exponential backoff and logging.

```python
from core.errors import async_retry_with_logging

@async_retry_with_logging(
    max_attempts=3,
    min_delay=2.0,
    max_delay=10.0,
    exception_types=(OSError, TimeoutError)
)
async def fetch_data_async():
    # Will retry up to 3 times with exponential backoff
    pass
```

## Aiogram Middleware

### ContextLoggingMiddleware
Adds contextual metadata (user_id, platform, state, message_type) to all log records.

```python
from core.middleware import ContextLoggingMiddleware
from aiogram import Dispatcher

middleware = ContextLoggingMiddleware(
    sheets_manager=sheets_manager,
    conversation_storage=storage
)

dp = Dispatcher()
dp.message.middleware(middleware)
```

### ErrorHandlingMiddleware
Catches exceptions, logs them, provides user-friendly fallback responses, and notifies admins.

```python
from core.middleware import ErrorHandlingMiddleware
from aiogram import Dispatcher

error_middleware = ErrorHandlingMiddleware(
    sheets_manager=sheets_manager,
    notifier=notifier,
    admin_ids=[123, 456]
)

dp = Dispatcher()
dp.message.middleware(error_middleware)
```

**Features:**
- Catches `ExternalServiceError`, `ManualInterventionRequired`, and generic exceptions
- Logs errors to both console/file and Google Sheets ("Ошибки" worksheet)
- Sends user-friendly responses in Russian
- Notifies admins about critical failures

### StructuredLoggingFormatter
Custom logging formatter that includes contextual metadata in log output.

```python
from core.middleware import setup_logging

setup_logging(
    log_level=logging.INFO,
    log_file="app.log"
)
```

**Output Format:**
```
2024-01-15 10:30:45 - my_module - INFO [user_id=123, platform=telegram, state=WAITING_NAME, msg_type=text] - Processing message
```

## Health Monitoring

### HealthChecker
Performs health checks on critical services (Google Sheets, Gemini AI).

```python
from core.health import HealthChecker
import asyncio

checker = HealthChecker(
    sheets_manager=sheets_manager,
    gemini_client=gemini_client
)

status = asyncio.run(checker.perform_all_checks())

if status.healthy:
    print("System is healthy")
else:
    for service, result in status.checks.items():
        if not result.healthy:
            print(f"{service} failed: {result.error}")
```

### HealthMonitor
Runs periodic health checks (default: every 30 minutes) and notifies admins on degradation.

```python
from core.health import HealthMonitor, HealthChecker
import asyncio

checker = HealthChecker(sheets_manager, gemini_client)
monitor = HealthMonitor(
    checker=checker,
    sheets_manager=sheets_manager,
    notifier=notifier,
    admin_ids=[123, 456],
    check_interval_minutes=30
)

# Start monitoring
asyncio.run(monitor.start())

# Stop monitoring
asyncio.run(monitor.stop())
```

**Features:**
- Runs health checks every 30 minutes (configurable)
- Checks Google Sheets connectivity and response time
- Checks Gemini AI connectivity with test prompt
- Logs results to AdminLog worksheet
- Notifies admins when system degrades

## Error Logging to Sheets

All errors are automatically logged to the "Ошибки" (Errors) worksheet with:
- Error type (exception class name)
- Error message
- Context (user_id, function name, etc.)
- Full traceback
- Timestamp

## Integration Example

```python
import logging
from aiogram import Bot, Dispatcher, Router, types
from core.middleware import (
    setup_logging,
    ContextLoggingMiddleware,
    ErrorHandlingMiddleware
)
from core.health import HealthChecker, HealthMonitor
from integrations.google.sheets_manager import GoogleSheetsManager
from services.notifications.notifier import Notifier
from services.gemini.client import GeminiClient

# Setup logging
setup_logging(log_level=logging.INFO, log_file="app.log")

# Initialize services
sheets_manager = GoogleSheetsManager(settings.google_sheets_id)
notifier = Notifier()
gemini_client = GeminiClient(settings.gemini_api_key)

# Setup health monitoring
checker = HealthChecker(sheets_manager, gemini_client)
health_monitor = HealthMonitor(
    checker=checker,
    sheets_manager=sheets_manager,
    notifier=notifier,
    admin_ids=settings.admin_ids,
    check_interval_minutes=30
)

# Setup bot
bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()

# Add middlewares
dp.message.middleware(ContextLoggingMiddleware(sheets_manager))
dp.message.middleware(ErrorHandlingMiddleware(
    sheets_manager=sheets_manager,
    notifier=notifier,
    admin_ids=settings.admin_ids
))

# Start health monitoring
async def startup():
    await health_monitor.start()

async def shutdown():
    await health_monitor.stop()

# Use in handler - exceptions are now automatically caught and handled
@router.message()
async def message_handler(message: types.Message):
    # Any exception raised here will be caught by ErrorHandlingMiddleware
    # and a safe response will be sent to the user
    pass
```

## Testing

Comprehensive tests are provided in `tests/test_error_handling.py`:

- **TestErrorHierarchy**: Tests custom exception classes
- **TestRetryDecorator**: Tests sync retry decorator behavior
- **TestAsyncRetryDecorator**: Tests async retry decorator behavior
- **TestContextLoggingMiddleware**: Tests context metadata addition
- **TestErrorHandlingMiddleware**: Tests error catching and fallback responses
- **TestHealthChecker**: Tests health check operations
- **TestHealthMonitor**: Tests health monitoring scheduler
- **TestHealthStatus**: Tests serialization

Run tests:
```bash
python -m pytest tests/test_error_handling.py -v
```

## Logging Configuration

The system uses Python's standard logging library with structured logging support.

### Log Levels
- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for recoverable errors
- **ERROR**: Error messages for non-recoverable errors
- **CRITICAL**: Critical errors that may cause system failure

### Log Destinations
1. **Console**: All log levels are output to console
2. **File**: All log levels are output to `app.log` (configured in setup_logging)
3. **Sheets**: Errors are logged to "Ошибки" worksheet via ErrorHandlingMiddleware

### Contextual Metadata in Logs
Each log record includes:
- `user_id`: Telegram user ID
- `platform`: Platform source (telegram, whatsapp, instagram)
- `state`: Current conversation state
- `message_type`: Type of message (text, media, callback, etc.)

Example structured log:
```
2024-01-15 10:30:45 - my_module - ERROR [user_id=123, platform=telegram, state=WAITING_NAME, msg_type=text] - ExternalServiceError: Google Sheets: API error
```

## Best Practices

1. **Use decorators for external calls**: Apply `@retry_with_logging` or `@async_retry_with_logging` to functions that call external APIs.

2. **Validate early**: Use `ValidationError` for input validation failures in handlers.

3. **Request manual intervention gracefully**: Use `ManualInterventionRequired` when automatic processing fails and admins need to handle the issue.

4. **Monitor health regularly**: Run health checks at least every 30 minutes to catch service degradation early.

5. **Log contextual information**: Use the logging middleware to automatically track user context in logs.

6. **Handle errors gracefully**: Let the ErrorHandlingMiddleware catch exceptions and send user-friendly responses.

## Migration Guide

To integrate error handling and health monitoring into existing code:

1. Add middlewares to your Dispatcher:
```python
dp.message.middleware(ContextLoggingMiddleware(sheets_manager))
dp.message.middleware(ErrorHandlingMiddleware(
    sheets_manager=sheets_manager,
    notifier=notifier,
    admin_ids=settings.admin_ids
))
```

2. Add decorators to external API calls:
```python
@async_retry_with_logging(exception_types=(OSError, TimeoutError))
async def call_external_api():
    pass
```

3. Start health monitoring:
```python
health_monitor = HealthMonitor(
    checker=checker,
    sheets_manager=sheets_manager,
    notifier=notifier,
    admin_ids=settings.admin_ids
)
await health_monitor.start()
```

4. Setup logging:
```python
setup_logging(log_level=logging.INFO, log_file="app.log")
```

## Troubleshooting

### Middleware not catching exceptions
- Ensure middlewares are added before handlers
- Check that the bot and sheets_manager are properly initialized
- Verify admin_ids is not empty if you want admin notifications

### Health checks failing
- Verify Google Sheets API credentials are valid
- Verify Gemini API key is valid
- Check network connectivity

### Logs not appearing in Sheets
- Verify sheets_manager._log_error() is working
- Check that "Ошибки" worksheet exists in the spreadsheet
- Check service account has write permissions

### Async decorator not retrying
- Ensure function is defined as `async def`
- Check exception_types include the actual exception being raised
- Verify max_attempts is greater than 1
