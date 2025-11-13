"""Tests for error handling, middleware, and health monitoring."""

import pytest
import asyncio
import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from aiogram import types
from aiogram.types import Update, Message, User, Chat, CallbackQuery

from core.errors import (
    ExternalServiceError,
    ValidationError,
    ManualInterventionRequired,
    retry_with_logging,
    async_retry_with_logging,
)
from core.middleware import (
    ContextLoggingMiddleware,
    ErrorHandlingMiddleware,
    StructuredLoggingFormatter,
    setup_logging,
)
from core.health import (
    HealthChecker,
    HealthCheckResult,
    HealthStatus,
    HealthMonitor,
)
from core.conversation import ConversationContext


# ============================================================================
# ERROR HIERARCHY TESTS
# ============================================================================


class TestErrorHierarchy:
    """Test custom exception classes."""

    def test_external_service_error(self):
        """Test ExternalServiceError creation."""
        original_error = ValueError("API error")
        error = ExternalServiceError(
            message="API call failed",
            service_name="TestAPI",
            original_error=original_error,
        )

        assert error.message == "API call failed"
        assert error.service_name == "TestAPI"
        assert error.original_error is original_error
        assert "TestAPI" in str(error)

    def test_validation_error(self):
        """Test ValidationError creation."""
        error = ValidationError(
            message="Invalid format",
            field="email",
        )

        assert error.message == "Invalid format"
        assert error.field == "email"
        assert "email" in str(error)

    def test_manual_intervention_required(self):
        """Test ManualInterventionRequired creation."""
        context = {"user_id": 123, "action": "booking"}
        error = ManualInterventionRequired(
            message="Booking failed",
            context=context,
            requires_admin_notification=True,
        )

        assert error.message == "Booking failed"
        assert error.context == context
        assert error.requires_admin_notification is True


# ============================================================================
# RETRY DECORATOR TESTS
# ============================================================================


class TestRetryDecorator:
    """Test retry_with_logging decorator."""

    def test_retry_decorator_success_first_attempt(self):
        """Test retry decorator with immediate success."""
        mock_func = MagicMock(return_value="success")

        @retry_with_logging(max_attempts=3)
        def test_function():
            return mock_func()

        result = test_function()
        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_decorator_success_after_retries(self):
        """Test retry decorator with success after retries."""
        mock_func = MagicMock(side_effect=[OSError("Error 1"), OSError("Error 2"), "success"])

        @retry_with_logging(max_attempts=3, min_delay=0.01, max_delay=0.05)
        def test_function():
            return mock_func()

        result = test_function()
        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_decorator_failure_all_attempts(self):
        """Test retry decorator with failure on all attempts."""
        mock_func = MagicMock(side_effect=OSError("API Error"))

        @retry_with_logging(max_attempts=3, min_delay=0.01, max_delay=0.05)
        def test_function():
            return mock_func()

        with pytest.raises(ExternalServiceError) as exc_info:
            test_function()

        assert "test_function" in str(exc_info.value)
        assert mock_func.call_count == 3

    def test_retry_decorator_with_logging_callback(self):
        """Test retry decorator with logging callback."""
        log_callback = MagicMock()
        call_count = 0

        @retry_with_logging(
            max_attempts=3,
            min_delay=0.01,
            max_delay=0.05,
            log_callback=log_callback,
        )
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OSError("Error")
            return "success"

        result = test_function()
        assert result == "success"
        # log_callback is called when retry is exhausted


class TestAsyncRetryDecorator:
    """Test async_retry_with_logging decorator."""

    @pytest.mark.asyncio
    async def test_async_retry_decorator_success_first_attempt(self):
        """Test async retry decorator with immediate success."""
        mock_func = AsyncMock(return_value="success")

        @async_retry_with_logging(max_attempts=3)
        async def test_function():
            return await mock_func()

        result = await test_function()
        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_decorator_success_after_retries(self):
        """Test async retry decorator with success after retries."""
        mock_func = AsyncMock(side_effect=[OSError("Error 1"), OSError("Error 2"), "success"])

        @async_retry_with_logging(max_attempts=3, min_delay=0.01, max_delay=0.05)
        async def test_function():
            return await mock_func()

        result = await test_function()
        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_async_retry_decorator_failure_all_attempts(self):
        """Test async retry decorator with failure on all attempts."""
        mock_func = AsyncMock(side_effect=OSError("API Error"))

        @async_retry_with_logging(max_attempts=3, min_delay=0.01, max_delay=0.05)
        async def test_function():
            return await mock_func()

        with pytest.raises(ExternalServiceError) as exc_info:
            await test_function()

        assert "test_function" in str(exc_info.value)
        assert mock_func.call_count == 3


# ============================================================================
# MIDDLEWARE TESTS
# ============================================================================


class TestContextLoggingMiddleware:
    """Test ContextLoggingMiddleware."""

    @pytest.mark.asyncio
    async def test_context_logging_middleware_with_text_message(self):
        """Test middleware adds context for text messages."""
        # Create a mock update with text message
        user = User(id=123, is_bot=False, first_name="Test")
        chat = Chat(id=123, type="private")
        message = Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=chat,
            from_user=user,
            text="Hello",
        )
        update = Update(update_id=1, message=message)

        # Create middleware
        middleware = ContextLoggingMiddleware()

        # Create mock handler
        handler_called = False

        async def mock_handler(event, data):
            nonlocal handler_called
            handler_called = True
            return "handler_result"

        # Execute middleware
        result = await middleware(mock_handler, update, {})

        assert handler_called
        assert result == "handler_result"

    @pytest.mark.asyncio
    async def test_context_logging_middleware_with_callback_query(self):
        """Test middleware adds context for callback queries."""
        # Create a mock update with callback query
        user = User(id=456, is_bot=False, first_name="Test")
        callback_query = CallbackQuery(
            id="callback_1",
            from_user=user,
            chat_instance="instance",
            data="test_data",
        )
        update = Update(update_id=2, callback_query=callback_query)

        # Create middleware
        middleware = ContextLoggingMiddleware()

        # Create mock handler
        async def mock_handler(event, data):
            return "handler_result"

        # Execute middleware
        result = await middleware(mock_handler, update, {})

        assert result == "handler_result"


class TestErrorHandlingMiddleware:
    """Test ErrorHandlingMiddleware."""

    @pytest.mark.asyncio
    async def test_error_handling_middleware_success(self):
        """Test middleware passes through successful handler execution."""
        user = User(id=123, is_bot=False, first_name="Test")
        chat = Chat(id=123, type="private")
        message = Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=chat,
            from_user=user,
            text="Hello",
        )
        update = Update(update_id=1, message=message)

        middleware = ErrorHandlingMiddleware()

        async def mock_handler(event, data):
            return "success"

        result = await middleware(mock_handler, update, {})
        assert result == "success"

    @pytest.mark.asyncio
    async def test_error_handling_middleware_manual_intervention_required(self):
        """Test middleware handles ManualInterventionRequired errors."""
        user = User(id=123, is_bot=False, first_name="Test")
        chat = Chat(id=123, type="private")
        message = Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=chat,
            from_user=user,
            text="Hello",
        )
        update = Update(update_id=1, message=message)

        # Create mock bot
        mock_bot = AsyncMock()
        sheets_manager = MagicMock()
        sheets_manager._log_error = MagicMock()

        middleware = ErrorHandlingMiddleware(
            sheets_manager=sheets_manager,
            admin_ids=[999],
        )

        async def mock_handler(event, data):
            raise ManualInterventionRequired(
                message="Booking failed",
                context={"reason": "no_availability"},
            )

        result = await middleware(mock_handler, update, {"bot": mock_bot})

        assert result is None
        mock_bot.send_message.assert_called()

    @pytest.mark.asyncio
    async def test_error_handling_middleware_external_service_error(self):
        """Test middleware handles ExternalServiceError."""
        user = User(id=123, is_bot=False, first_name="Test")
        chat = Chat(id=123, type="private")
        message = Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=chat,
            from_user=user,
            text="Hello",
        )
        update = Update(update_id=1, message=message)

        mock_bot = AsyncMock()
        sheets_manager = MagicMock()
        sheets_manager._log_error = MagicMock()

        middleware = ErrorHandlingMiddleware(
            sheets_manager=sheets_manager,
            admin_ids=[999],
        )

        async def mock_handler(event, data):
            raise ExternalServiceError(
                message="API timeout",
                service_name="Sheets",
            )

        result = await middleware(mock_handler, update, {"bot": mock_bot})

        assert result is None
        mock_bot.send_message.assert_called()

    @pytest.mark.asyncio
    async def test_error_handling_middleware_generic_exception(self):
        """Test middleware handles generic exceptions."""
        user = User(id=123, is_bot=False, first_name="Test")
        chat = Chat(id=123, type="private")
        message = Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=chat,
            from_user=user,
            text="Hello",
        )
        update = Update(update_id=1, message=message)

        mock_bot = AsyncMock()
        sheets_manager = MagicMock()
        sheets_manager._log_error = MagicMock()

        middleware = ErrorHandlingMiddleware(
            sheets_manager=sheets_manager,
            admin_ids=[999],
        )

        async def mock_handler(event, data):
            raise ValueError("Unexpected error")

        result = await middleware(mock_handler, update, {"bot": mock_bot})

        assert result is None
        mock_bot.send_message.assert_called()
        sheets_manager._log_error.assert_called()


class TestStructuredLoggingFormatter:
    """Test StructuredLoggingFormatter."""

    def test_formatter_with_context(self):
        """Test formatter includes contextual metadata."""
        formatter = StructuredLoggingFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.user_id = 123
        record.platform = "telegram"
        record.state = "WAITING_NAME"
        record.message_type = "text"

        formatted = formatter.format(record)

        assert "Test message" in formatted
        assert "user_id=123" in formatted
        assert "platform=telegram" in formatted
        assert "state=WAITING_NAME" in formatted
        assert "msg_type=text" in formatted

    def test_formatter_without_context(self):
        """Test formatter works without contextual metadata."""
        formatter = StructuredLoggingFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "Test message" in formatted


# ============================================================================
# HEALTH CHECKS TESTS
# ============================================================================


class TestHealthChecker:
    """Test HealthChecker functionality."""

    @pytest.mark.asyncio
    async def test_check_sheets_connectivity_success(self):
        """Test successful Sheets health check."""
        mock_sheets = MagicMock()
        mock_sheets.read_specialists = MagicMock(return_value=[])

        checker = HealthChecker(sheets_manager=mock_sheets)
        result = await checker.check_sheets_connectivity()

        assert result.service == "sheets"
        assert result.healthy is True
        assert result.response_time_ms > 0

    @pytest.mark.asyncio
    async def test_check_sheets_connectivity_failure(self):
        """Test failed Sheets health check."""
        mock_sheets = MagicMock()
        mock_sheets.read_specialists = MagicMock(
            side_effect=Exception("Connection failed")
        )

        checker = HealthChecker(sheets_manager=mock_sheets)
        result = await checker.check_sheets_connectivity()

        assert result.service == "sheets"
        assert result.healthy is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_check_sheets_connectivity_not_initialized(self):
        """Test Sheets health check when not initialized."""
        checker = HealthChecker(sheets_manager=None)
        result = await checker.check_sheets_connectivity()

        assert result.service == "sheets"
        assert result.healthy is False
        assert "not initialized" in result.error

    @pytest.mark.asyncio
    async def test_check_gemini_connectivity_success(self):
        """Test successful Gemini health check."""
        mock_gemini = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "OK"
        mock_gemini.generate_content = MagicMock(return_value=mock_response)

        checker = HealthChecker(gemini_client=mock_gemini)
        result = await checker.check_gemini_connectivity()

        assert result.service == "gemini"
        assert result.healthy is True

    @pytest.mark.asyncio
    async def test_check_gemini_connectivity_failure(self):
        """Test failed Gemini health check."""
        mock_gemini = MagicMock()
        mock_gemini.generate_content = MagicMock(
            side_effect=Exception("API error")
        )

        checker = HealthChecker(gemini_client=mock_gemini)
        result = await checker.check_gemini_connectivity()

        assert result.service == "gemini"
        assert result.healthy is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_perform_all_checks(self):
        """Test performing all health checks."""
        mock_sheets = MagicMock()
        mock_sheets.read_specialists = MagicMock(return_value=[])
        mock_gemini = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "OK"
        mock_gemini.generate_content = MagicMock(return_value=mock_response)

        checker = HealthChecker(sheets_manager=mock_sheets, gemini_client=mock_gemini)
        status = await checker.perform_all_checks()

        assert status.healthy is True
        assert "sheets" in status.checks
        assert "gemini" in status.checks
        assert status.checks["sheets"].healthy is True
        assert status.checks["gemini"].healthy is True


class TestHealthMonitor:
    """Test HealthMonitor functionality."""

    @pytest.mark.asyncio
    async def test_health_monitor_logs_status_to_sheets(self):
        """Test health monitor logs status to sheets."""
        mock_sheets = MagicMock()
        mock_sheets.read_specialists = MagicMock(return_value=[])
        mock_sheets.log_admin_action = MagicMock()

        mock_gemini = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "OK"
        mock_gemini.generate_content = MagicMock(return_value=mock_response)

        checker = HealthChecker(sheets_manager=mock_sheets, gemini_client=mock_gemini)
        monitor = HealthMonitor(
            checker=checker,
            sheets_manager=mock_sheets,
            admin_ids=[999],
        )

        # Run health check job
        await monitor._health_check_job()

        # Verify logging was called
        mock_sheets.log_admin_action.assert_called()

    @pytest.mark.asyncio
    async def test_health_monitor_notifies_on_degradation(self):
        """Test health monitor notifies admins on degradation."""
        mock_sheets = MagicMock()
        mock_sheets.read_specialists = MagicMock(
            side_effect=Exception("Connection failed")
        )
        mock_sheets.log_admin_action = MagicMock()

        mock_gemini = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "OK"
        mock_gemini.generate_content = MagicMock(return_value=mock_response)

        mock_notifier = AsyncMock()
        mock_notifier.send_immediate_alert = AsyncMock()

        checker = HealthChecker(sheets_manager=mock_sheets, gemini_client=mock_gemini)
        monitor = HealthMonitor(
            checker=checker,
            sheets_manager=mock_sheets,
            notifier=mock_notifier,
            admin_ids=[999],
        )

        # Run health check job
        await monitor._health_check_job()

        # First run should not notify (no previous state)
        # Run again to trigger degradation notification
        await monitor._health_check_job()

        # Verify notification was sent
        mock_notifier.send_immediate_alert.assert_called()


class TestHealthStatus:
    """Test HealthStatus model."""

    def test_health_status_to_dict(self):
        """Test HealthStatus serialization."""
        check1 = HealthCheckResult(service="sheets", healthy=True, message="OK")
        check2 = HealthCheckResult(service="gemini", healthy=False, error="Error")

        status = HealthStatus(
            healthy=False,
            checks={"sheets": check1, "gemini": check2},
        )

        status_dict = status.to_dict()

        assert status_dict["healthy"] is False
        assert "sheets" in status_dict["checks"]
        assert "gemini" in status_dict["checks"]
        assert status_dict["checks"]["sheets"]["healthy"] is True
        assert status_dict["checks"]["gemini"]["healthy"] is False
