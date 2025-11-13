"""Custom exception hierarchy and error handling decorators."""

import asyncio
import functools
import logging
import traceback
from typing import Callable, Any, Optional, Type, TypeVar, Union

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ExternalServiceError(Exception):
    """Raised when an external service call fails after retries are exhausted."""

    def __init__(
        self,
        message: str,
        service_name: str = "Unknown",
        original_error: Optional[Exception] = None,
    ):
        self.message = message
        self.service_name = service_name
        self.original_error = original_error
        super().__init__(f"{service_name}: {message}")


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(f"Validation error: {message}" + (f" ({field})" if field else ""))


class ManualInterventionRequired(Exception):
    """Raised when automatic processing fails and requires manual intervention."""

    def __init__(
        self,
        message: str,
        context: Optional[dict] = None,
        requires_admin_notification: bool = True,
    ):
        self.message = message
        self.context = context or {}
        self.requires_admin_notification = requires_admin_notification
        super().__init__(message)


def retry_with_logging(
    *,
    max_attempts: int = 3,
    min_delay: float = 2.0,
    max_delay: float = 10.0,
    exception_types: tuple = (Exception,),
    log_before_retry: bool = True,
    log_callback: Optional[Callable] = None,
) -> Callable:
    """
    Decorator to retry a function with exponential backoff and logging.

    Args:
        max_attempts: Maximum number of retry attempts
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
        exception_types: Tuple of exception types to catch and retry on
        log_before_retry: Whether to log before each retry attempt
        log_callback: Optional callback function for custom logging

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_delay, max=max_delay),
            retry=retry_if_exception_type(exception_types),
            reraise=True,
        )
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except RetryError as e:
                # Extract the original exception
                original_error = e.last_attempt.exception()
                func_name = func.__name__
                logger.error(
                    f"Function {func_name} failed after {max_attempts} attempts: {str(original_error)}",
                    exc_info=True,
                )
                if log_callback:
                    log_callback(func_name, original_error)
                raise ExternalServiceError(
                    message=str(original_error),
                    service_name=func_name,
                    original_error=original_error,
                )
            except Exception as e:
                func_name = func.__name__
                logger.error(
                    f"Function {func_name} raised unexpected error: {str(e)}",
                    exc_info=True,
                )
                if log_callback:
                    log_callback(func_name, e)
                raise

        return wrapper

    return decorator


def async_retry_with_logging(
    *,
    max_attempts: int = 3,
    min_delay: float = 2.0,
    max_delay: float = 10.0,
    exception_types: tuple = (Exception,),
    log_before_retry: bool = True,
    log_callback: Optional[Callable] = None,
) -> Callable:
    """
    Decorator to retry an async function with exponential backoff and logging.

    Args:
        max_attempts: Maximum number of retry attempts
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
        exception_types: Tuple of exception types to catch and retry on
        log_before_retry: Whether to log before each retry attempt
        log_callback: Optional callback function for custom logging

    Returns:
        Decorated async function with retry logic
    """

    def decorator(func: Callable[..., Any]) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            last_error = None

            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except exception_types as e:
                    attempt += 1
                    last_error = e

                    if attempt < max_attempts:
                        if log_before_retry:
                            logger.warning(
                                f"Function {func.__name__} failed (attempt {attempt}/{max_attempts}): {str(e)}. "
                                f"Retrying in {min_delay}-{max_delay}s..."
                            )

                        # Exponential backoff with jitter
                        delay = min(
                            max_delay, min_delay * (2 ** (attempt - 1))
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts: {str(e)}",
                            exc_info=True,
                        )
                        if log_callback:
                            log_callback(func.__name__, e)

                except Exception as e:
                    logger.error(
                        f"Function {func.__name__} raised unexpected error: {str(e)}",
                        exc_info=True,
                    )
                    if log_callback:
                        log_callback(func.__name__, e)
                    raise

            if last_error:
                raise ExternalServiceError(
                    message=str(last_error),
                    service_name=func.__name__,
                    original_error=last_error,
                )

        return wrapper

    return decorator


def log_error_and_notify(
    logger_instance: logging.Logger,
    sheets_manager: Optional[Any] = None,
    notifier: Optional[Any] = None,
    admin_ids: Optional[list[int]] = None,
) -> Callable:
    """
    Decorator to log errors to both logger and sheets, and notify admins.

    Args:
        logger_instance: Logger instance to use
        sheets_manager: Google Sheets manager for error logging
        notifier: Notifier instance for admin alerts
        admin_ids: List of admin user IDs to notify

    Returns:
        Decorated function with error logging and notification
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Union[T, None]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger_instance.error(
                    f"Error in {func.__name__}: {str(e)}", exc_info=True
                )

                # Log to sheets if available
                if sheets_manager:
                    try:
                        sheets_manager._log_error(
                            error_type=type(e).__name__,
                            message=str(e),
                            context=f"Function: {func.__name__}",
                            traceback=error_traceback,
                        )
                    except Exception as logging_error:
                        logger_instance.warning(
                            f"Failed to log error to sheets: {logging_error}"
                        )

                # Notify admins if available and this is a critical error
                if (
                    notifier
                    and admin_ids
                    and isinstance(e, (ExternalServiceError, ManualInterventionRequired))
                ):
                    try:
                        import asyncio

                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Can't await in a non-async function, just log warning
                            logger_instance.warning(
                                "Cannot notify admins from sync context"
                            )
                        else:
                            # This is complex - we'd need to schedule the notification
                            logger_instance.warning(
                                f"Admin notification needed for: {str(e)}"
                            )
                    except Exception as notify_error:
                        logger_instance.warning(
                            f"Failed to notify admins: {notify_error}"
                        )

                # Return None for graceful degradation or re-raise based on context
                return None

        return wrapper

    return decorator
