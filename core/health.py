"""Health monitoring and status checks for critical services."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Represents the result of a health check."""

    service: str
    healthy: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message: str = ""
    response_time_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class HealthStatus:
    """Overall health status of the system."""

    healthy: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    checks: Dict[str, HealthCheckResult] = field(default_factory=dict)
    last_degradation: Optional[datetime] = None
    previous_state: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "healthy": self.healthy,
            "timestamp": self.timestamp.isoformat(),
            "last_degradation": (
                self.last_degradation.isoformat()
                if self.last_degradation
                else None
            ),
            "checks": {
                name: {
                    "healthy": check.healthy,
                    "timestamp": check.timestamp.isoformat(),
                    "message": check.message,
                    "response_time_ms": check.response_time_ms,
                    "error": check.error,
                }
                for name, check in self.checks.items()
            },
        }


class HealthChecker:
    """Performs health checks on critical services."""

    def __init__(
        self,
        sheets_manager: Optional[Any] = None,
        gemini_client: Optional[Any] = None,
    ):
        """
        Initialize health checker.

        Args:
            sheets_manager: Google Sheets manager instance
            gemini_client: Gemini AI client instance
        """
        self.sheets_manager = sheets_manager
        self.gemini_client = gemini_client
        self.status = HealthStatus(healthy=True)

    async def check_sheets_connectivity(self) -> HealthCheckResult:
        """Check Google Sheets connectivity."""
        start_time = datetime.now(timezone.utc)
        result = HealthCheckResult(
            service="sheets",
            healthy=False,
            message="Not checked yet",
        )

        try:
            if not self.sheets_manager:
                result.error = "Sheets manager not initialized"
                return result

            # Try to read a simple value to verify connectivity
            # This will use the existing retry logic in sheets_manager
            specialists = self.sheets_manager.read_specialists()

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            result.healthy = True
            result.message = f"Successfully read {len(specialists)} specialists"
            result.response_time_ms = elapsed

        except Exception as e:
            result.error = str(e)
            result.message = f"Failed to connect to Sheets: {str(e)}"
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            result.response_time_ms = elapsed
            logger.error(f"Sheets health check failed: {e}")

        return result

    async def check_gemini_connectivity(self) -> HealthCheckResult:
        """Check Gemini AI connectivity with test prompt."""
        start_time = datetime.now(timezone.utc)
        result = HealthCheckResult(
            service="gemini",
            healthy=False,
            message="Not checked yet",
        )

        try:
            if not self.gemini_client:
                result.error = "Gemini client not initialized"
                return result

            # Send a simple test prompt
            test_response = self.gemini_client.generate_content(
                "Respond with 'OK' only."
            )

            if test_response and test_response.text:
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                result.healthy = True
                result.message = "Successfully communicated with Gemini"
                result.response_time_ms = elapsed
            else:
                result.error = "Empty response from Gemini"
                result.message = "Gemini returned no content"

        except Exception as e:
            result.error = str(e)
            result.message = f"Failed to communicate with Gemini: {str(e)}"
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            result.response_time_ms = elapsed
            logger.error(f"Gemini health check failed: {e}")

        return result

    async def perform_all_checks(self) -> HealthStatus:
        """Perform all health checks and return overall status."""
        logger.info("Starting health checks...")

        # Run checks concurrently
        sheets_result, gemini_result = await asyncio.gather(
            self.check_sheets_connectivity(),
            self.check_gemini_connectivity(),
            return_exceptions=True,
        )

        # Handle exceptions from gather
        if isinstance(sheets_result, Exception):
            sheets_result = HealthCheckResult(
                service="sheets",
                healthy=False,
                error=str(sheets_result),
                message=f"Health check exception: {str(sheets_result)}",
            )

        if isinstance(gemini_result, Exception):
            gemini_result = HealthCheckResult(
                service="gemini",
                healthy=False,
                error=str(gemini_result),
                message=f"Health check exception: {str(gemini_result)}",
            )

        # Update status
        previous_healthy = self.status.healthy
        self.status.checks = {
            "sheets": sheets_result,
            "gemini": gemini_result,
        }
        self.status.healthy = sheets_result.healthy and gemini_result.healthy
        self.status.timestamp = datetime.now(timezone.utc)

        # Track degradation
        if not self.status.healthy and previous_healthy:
            self.status.last_degradation = datetime.now(timezone.utc)
            logger.warning("System health degradation detected")

        logger.info(f"Health check complete. System healthy: {self.status.healthy}")
        return self.status


class HealthMonitor:
    """Manages scheduled health checks and notifications."""

    def __init__(
        self,
        checker: HealthChecker,
        sheets_manager: Optional[Any] = None,
        notifier: Optional[Any] = None,
        admin_ids: Optional[list[int]] = None,
        check_interval_minutes: int = 30,
    ):
        """
        Initialize health monitor.

        Args:
            checker: HealthChecker instance
            sheets_manager: Google Sheets manager for logging results
            notifier: Notifier instance for admin alerts
            admin_ids: List of admin user IDs to notify
            check_interval_minutes: Interval between health checks
        """
        self.checker = checker
        self.sheets_manager = sheets_manager
        self.notifier = notifier
        self.admin_ids = admin_ids or []
        self.check_interval_minutes = check_interval_minutes
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.previous_status: Optional[HealthStatus] = None

    async def start(self) -> None:
        """Start the health monitoring scheduler."""
        try:
            self.scheduler = AsyncIOScheduler()

            # Add job to run health checks
            self.scheduler.add_job(
                self._health_check_job,
                IntervalTrigger(minutes=self.check_interval_minutes),
            )

            self.scheduler.start()
            logger.info(
                f"Health monitor started with {self.check_interval_minutes}min interval"
            )

            # Run initial check
            await self._health_check_job()

        except Exception as e:
            logger.error(f"Failed to start health monitor: {e}")
            raise

    async def stop(self) -> None:
        """Stop the health monitoring scheduler."""
        try:
            if self.scheduler:
                self.scheduler.shutdown()
                logger.info("Health monitor stopped")
        except Exception as e:
            logger.error(f"Failed to stop health monitor: {e}")

    async def _health_check_job(self) -> None:
        """Perform health checks and log/notify results."""
        try:
            status = await self.checker.perform_all_checks()

            # Log to sheets
            if self.sheets_manager:
                try:
                    self._log_health_status_to_sheets(status)
                except Exception as e:
                    logger.warning(f"Failed to log health status: {e}")

            # Notify admins on degradation
            if status != self.previous_status and not status.healthy:
                await self._notify_admin_degradation(status)

            self.previous_status = status

        except Exception as e:
            logger.error(f"Health check job failed: {e}", exc_info=True)

    def _log_health_status_to_sheets(self, status: HealthStatus) -> None:
        """Log health status to AdminLog in Sheets."""
        if not self.sheets_manager:
            return

        try:
            # Create admin action log entry
            description = f"Health Check: {status.to_dict()}"
            self.sheets_manager.log_admin_action(
                action_type="health_check",
                resource_type="system",
                description=description,
            )
            logger.debug(f"Logged health status to sheets: {status.healthy}")
        except Exception as e:
            logger.warning(f"Failed to log health status to sheets: {e}")

    async def _notify_admin_degradation(self, status: HealthStatus) -> None:
        """Notify admins about system degradation."""
        if not self.admin_ids:
            return

        try:
            # Build notification message
            failed_services = [
                f"  • {name} ({check.error or check.message})"
                for name, check in status.checks.items()
                if not check.healthy
            ]

            message = (
                "🔴 *System Health Degradation*\n\n"
                "The following services are unavailable:\n"
                + "\n".join(failed_services)
            )

            # Send to admins
            if self.notifier:
                try:
                    from services.notifications.notifier import NotificationEvent

                    for admin_id in self.admin_ids:
                        event = NotificationEvent(
                            event_type="health_alert",
                            recipient_id=admin_id,
                            recipient_type="admin",
                            language="ru",
                            data={"message": message},
                            priority="urgent",
                        )
                        await self.notifier.send_immediate_alert(event)

                except Exception as e:
                    logger.warning(f"Failed to send notification: {e}")

            logger.warning(f"Admin degradation alert sent: {message}")

        except Exception as e:
            logger.warning(f"Failed to notify admins of degradation: {e}")
