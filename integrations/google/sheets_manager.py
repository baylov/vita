"""Google Sheets integration manager for bi-directional synchronization."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import gspread
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from settings import settings
from exceptions import RecoverableExternalError, SheetsInitializationError, SheetsError
from models import (
    SpecialistDTO,
    ScheduleDTO,
    BookingDTO,
    DayOffDTO,
    AdminActionDTO,
    ErrorLogDTO,
    SyncState,
)


logger = logging.getLogger(__name__)


# Define worksheet names (Russian language)
WORKSHEETS = {
    "specialists": "Специалисты",
    "schedule": "Расписание",
    "days_off": "Выходные",
    "bookings": "Записи",
    "admin_logs": "Логи Админа",
    "errors": "Ошибки",
}


class GoogleSheetsManager:
    """Manager for Google Sheets integration with bi-directional sync support."""

    def __init__(self, spreadsheet_id: str, service_account_path: Optional[str] = None):
        """
        Initialize the Google Sheets manager.

        Args:
            spreadsheet_id: The ID of the Google Sheet to manage
            service_account_path: Path to service_account.json file (defaults to settings)
        """
        self.spreadsheet_id = spreadsheet_id
        self.service_account_path = service_account_path or settings.service_account_json_path
        self.client = None
        self.spreadsheet = None
        self.worksheets = {}
        self.sync_state = SyncState()

        self._initialize()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((gspread.exceptions.APIError, OSError)),
    )
    def _initialize(self) -> None:
        """Initialize Google Sheets client and ensure worksheets exist."""
        try:
            # Authenticate using service account
            self.client = gspread.service_account(filename=self.service_account_path)
            logger.info(
                f"Authenticated to Google Sheets using {self.service_account_path}"
            )

            # Open the spreadsheet
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            logger.info(f"Opened spreadsheet: {self.spreadsheet.title}")

            # Ensure all required worksheets exist
            self._ensure_worksheets()
            logger.info("All required worksheets are initialized")

            # Log initialization
            self._log_admin_action(
                action_type="init",
                resource_type="sheets",
                description="Google Sheets manager initialized",
            )

        except FileNotFoundError as e:
            logger.error(f"Service account file not found: {self.service_account_path}")
            raise SheetsInitializationError(f"Service account file not found: {e}")
        except gspread.exceptions.APIError as e:
            logger.error(f"Google Sheets API error during initialization: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets manager: {e}")
            raise SheetsInitializationError(f"Initialization failed: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((gspread.exceptions.APIError, OSError)),
    )
    def _ensure_worksheets(self) -> None:
        """Ensure all required worksheets exist, creating them if necessary."""
        existing_sheets = {ws.title for ws in self.spreadsheet.worksheets()}

        for key, sheet_name in WORKSHEETS.items():
            if sheet_name not in existing_sheets:
                logger.info(f"Creating worksheet: {sheet_name}")
                worksheet = self.spreadsheet.add_worksheet(title=sheet_name, rows=1, cols=1)
                self._initialize_worksheet_headers(key, worksheet)
            else:
                worksheet = self.spreadsheet.worksheet(sheet_name)
            self.worksheets[key] = worksheet

    def _initialize_worksheet_headers(self, key: str, worksheet) -> None:
        """Initialize headers for a specific worksheet."""
        headers = self._get_headers_for_worksheet(key)
        if headers:
            try:
                worksheet.append_row(headers)
                logger.info(f"Added headers to worksheet: {WORKSHEETS[key]}")
            except gspread.exceptions.APIError as e:
                logger.warning(f"Failed to add headers: {e}")

    def _get_headers_for_worksheet(self, key: str) -> list[str]:
        """Get appropriate headers for each worksheet type."""
        headers_map = {
            "specialists": ["ID", "ФИ", "Специализация", "Телефон", "Email", "Активен", "Создано", "Обновлено"],
            "schedule": ["ID", "Специалист ID", "День недели", "Время начала", "Время конца", "Доступен", "Создано", "Обновлено"],
            "days_off": ["ID", "Специалист ID", "Дата", "Причина", "Создано"],
            "bookings": ["ID", "Специалист ID", "Клиент", "Дата/Время", "Длительность мин", "Заметки", "Статус", "Создано", "Обновлено"],
            "admin_logs": ["ID", "Тип действия", "Тип ресурса", "ID ресурса", "Описание", "Выполнил", "Создано"],
            "errors": ["ID", "Тип ошибки", "Сообщение", "Контекст", "Трассировка стека", "Создано"],
        }
        return headers_map.get(key, [])

    def _get_worksheet_safe(self, key: str):
        """Get a worksheet by key with error handling."""
        if key not in self.worksheets:
            raise SheetsError(f"Worksheet '{key}' not initialized")
        return self.worksheets[key]

    # Read operations

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((gspread.exceptions.APIError, OSError)),
    )
    def read_specialists(self) -> list[SpecialistDTO]:
        """
        Read all specialists from the Sheets.

        Returns:
            List of SpecialistDTO objects
        
        Raises:
            gspread.exceptions.APIError: When API calls fail after retries
        """
        worksheet = self._get_worksheet_safe("specialists")
        records = worksheet.get_all_records()
        specialists = []
        for record in records:
            try:
                specialist = SpecialistDTO(
                    id=int(record.get("ID", 0)) or None,
                    name=record.get("ФИ", ""),
                    specialization=record.get("Специализация", ""),
                    phone=record.get("Телефон") or None,
                    email=record.get("Email") or None,
                    is_active=record.get("Активен", "").lower() in ("да", "true", "1"),
                    created_at=self._parse_datetime(record.get("Создано")),
                    updated_at=self._parse_datetime(record.get("Обновлено")),
                )
                specialists.append(specialist)
            except Exception as e:
                logger.warning(f"Failed to parse specialist record: {e}")
        return specialists

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((gspread.exceptions.APIError, OSError)),
    )
    def read_schedule(self) -> list[ScheduleDTO]:
        """
        Read all schedules from the Sheets.

        Returns:
            List of ScheduleDTO objects
        """
        try:
            worksheet = self._get_worksheet_safe("schedule")
            records = worksheet.get_all_records()
            schedules = []
            for record in records:
                try:
                    schedule = ScheduleDTO(
                        id=int(record.get("ID", 0)) or None,
                        specialist_id=int(record.get("Специалист ID", 0)),
                        day_of_week=int(record.get("День недели", 0)),
                        start_time=record.get("Время начала", ""),
                        end_time=record.get("Время конца", ""),
                        is_available=record.get("Доступен", "").lower() in ("да", "true", "1"),
                        created_at=self._parse_datetime(record.get("Создано")),
                        updated_at=self._parse_datetime(record.get("Обновлено")),
                    )
                    schedules.append(schedule)
                except Exception as e:
                    logger.warning(f"Failed to parse schedule record: {e}")
            return schedules
        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to read schedule: {e}")
            raise RecoverableExternalError(str(e), "Google Sheets")
        except Exception as e:
            logger.error(f"Error reading schedule: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((gspread.exceptions.APIError, OSError)),
    )
    def read_bookings(self) -> list[BookingDTO]:
        """
        Read all bookings from the Sheets.

        Returns:
            List of BookingDTO objects
        """
        try:
            worksheet = self._get_worksheet_safe("bookings")
            records = worksheet.get_all_records()
            bookings = []
            for record in records:
                try:
                    booking = BookingDTO(
                        id=int(record.get("ID", 0)) or None,
                        specialist_id=int(record.get("Специалист ID", 0)),
                        client_name=record.get("Клиент", ""),
                        booking_datetime=self._parse_datetime(record.get("Дата/Время")),
                        duration_minutes=int(record.get("Длительность мин", 60)),
                        notes=record.get("Заметки") or None,
                        status=record.get("Статус", "confirmed"),
                        created_at=self._parse_datetime(record.get("Создано")),
                        updated_at=self._parse_datetime(record.get("Обновлено")),
                    )
                    bookings.append(booking)
                except Exception as e:
                    logger.warning(f"Failed to parse booking record: {e}")
            return bookings
        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to read bookings: {e}")
            raise RecoverableExternalError(str(e), "Google Sheets")
        except Exception as e:
            logger.error(f"Error reading bookings: {e}")
            raise

    # Write operations

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((gspread.exceptions.APIError, OSError)),
    )
    def add_specialist(self, specialist: SpecialistDTO) -> SpecialistDTO:
        """
        Add a new specialist to the Sheets.

        Args:
            specialist: SpecialistDTO object to add

        Returns:
            The added specialist with ID assigned
        """
        worksheet = self._get_worksheet_safe("specialists")
        now = datetime.now(timezone.utc).isoformat()
        row = [
            specialist.id or "",
            specialist.name,
            specialist.specialization,
            specialist.phone or "",
            specialist.email or "",
            "Да" if specialist.is_active else "Нет",
            now,
            now,
        ]
        worksheet.append_row(row)
        specialist.created_at = self._parse_datetime(now)
        specialist.updated_at = self._parse_datetime(now)
        logger.info(f"Added specialist: {specialist.name}")
        self._log_admin_action(
            action_type="create",
            resource_type="specialist",
            description=f"Добавлен специалист: {specialist.name}",
        )
        return specialist

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((gspread.exceptions.APIError, OSError)),
    )
    def update_specialist(self, specialist_id: int, specialist: SpecialistDTO) -> SpecialistDTO:
        """
        Update an existing specialist in the Sheets.

        Args:
            specialist_id: ID of the specialist to update
            specialist: Updated SpecialistDTO object

        Returns:
            The updated specialist
        """
        try:
            worksheet = self._get_worksheet_safe("specialists")
            records = worksheet.get_all_records()
            now = datetime.now(timezone.utc).isoformat()

            for idx, record in enumerate(records):
                if int(record.get("ID", 0)) == specialist_id:
                    row_idx = idx + 2  # +1 for header, +1 for 1-based indexing
                    row = [
                        specialist_id,
                        specialist.name,
                        specialist.specialization,
                        specialist.phone or "",
                        specialist.email or "",
                        "Да" if specialist.is_active else "Нет",
                        record.get("Создано", now),
                        now,
                    ]
                    worksheet.delete_rows(row_idx, row_idx)
                    worksheet.insert_row(row, row_idx)
                    specialist.updated_at = self._parse_datetime(now)
                    logger.info(f"Updated specialist: {specialist.name}")
                    self._log_admin_action(
                        action_type="update",
                        resource_type="specialist",
                        resource_id=specialist_id,
                        description=f"Обновлен специалист: {specialist.name}",
                    )
                    return specialist

            logger.warning(f"Specialist with ID {specialist_id} not found")
            raise SheetsError(f"Specialist with ID {specialist_id} not found")

        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to update specialist: {e}")
            self._log_error("api_error", f"Failed to update specialist: {e}")
            raise RecoverableExternalError(str(e), "Google Sheets")
        except Exception as e:
            logger.error(f"Error updating specialist: {e}")
            if not isinstance(e, SheetsError):
                self._log_error("unexpected_error", str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((gspread.exceptions.APIError, OSError)),
    )
    def delete_specialist(self, specialist_id: int) -> bool:
        """
        Delete a specialist from the Sheets.

        Args:
            specialist_id: ID of the specialist to delete

        Returns:
            True if deletion was successful
        """
        try:
            worksheet = self._get_worksheet_safe("specialists")
            records = worksheet.get_all_records()

            for idx, record in enumerate(records):
                if int(record.get("ID", 0)) == specialist_id:
                    row_idx = idx + 2  # +1 for header, +1 for 1-based indexing
                    worksheet.delete_rows(row_idx, row_idx)
                    logger.info(f"Deleted specialist with ID: {specialist_id}")
                    self._log_admin_action(
                        action_type="delete",
                        resource_type="specialist",
                        resource_id=specialist_id,
                        description=f"Удален специалист с ID: {specialist_id}",
                    )
                    return True

            logger.warning(f"Specialist with ID {specialist_id} not found for deletion")
            return False

        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to delete specialist: {e}")
            self._log_error("api_error", f"Failed to delete specialist: {e}")
            raise RecoverableExternalError(str(e), "Google Sheets")
        except Exception as e:
            logger.error(f"Error deleting specialist: {e}")
            self._log_error("unexpected_error", str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((gspread.exceptions.APIError, OSError)),
    )
    def add_booking(self, booking: BookingDTO) -> BookingDTO:
        """
        Add a new booking to the Sheets.

        Args:
            booking: BookingDTO object to add

        Returns:
            The added booking with ID assigned
        """
        try:
            worksheet = self._get_worksheet_safe("bookings")
            now = datetime.now(timezone.utc).isoformat()
            row = [
                booking.id or "",
                booking.specialist_id,
                booking.client_name,
                booking.booking_datetime.isoformat() if booking.booking_datetime else "",
                booking.duration_minutes,
                booking.notes or "",
                booking.status,
                now,
                now,
            ]
            worksheet.append_row(row)
            booking.created_at = self._parse_datetime(now)
            booking.updated_at = self._parse_datetime(now)
            logger.info(f"Added booking for client: {booking.client_name}")
            self._log_admin_action(
                action_type="create",
                resource_type="booking",
                description=f"Добавлена запись для {booking.client_name}",
            )
            return booking
        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to add booking: {e}")
            self._log_error("api_error", f"Failed to add booking: {e}")
            raise RecoverableExternalError(str(e), "Google Sheets")
        except Exception as e:
            logger.error(f"Error adding booking: {e}")
            self._log_error("unexpected_error", str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((gspread.exceptions.APIError, OSError)),
    )
    def add_day_off(self, day_off: DayOffDTO) -> DayOffDTO:
        """
        Add a day off record to the Sheets.

        Args:
            day_off: DayOffDTO object to add

        Returns:
            The added day off record
        """
        try:
            worksheet = self._get_worksheet_safe("days_off")
            now = datetime.now(timezone.utc).isoformat()
            row = [
                day_off.id or "",
                day_off.specialist_id,
                day_off.date,
                day_off.reason or "",
                now,
            ]
            worksheet.append_row(row)
            day_off.created_at = self._parse_datetime(now)
            logger.info(f"Added day off for specialist ID: {day_off.specialist_id}")
            self._log_admin_action(
                action_type="create",
                resource_type="day_off",
                resource_id=day_off.specialist_id,
                description=f"Добавлен выходной день: {day_off.date}",
            )
            return day_off
        except gspread.exceptions.APIError as e:
            logger.error(f"Failed to add day off: {e}")
            self._log_error("api_error", f"Failed to add day off: {e}")
            raise RecoverableExternalError(str(e), "Google Sheets")
        except Exception as e:
            logger.error(f"Error adding day off: {e}")
            self._log_error("unexpected_error", str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((gspread.exceptions.APIError, OSError)),
    )
    def log_admin_action(self, action: AdminActionDTO) -> AdminActionDTO:
        """
        Log an admin action to the Sheets.

        Args:
            action: AdminActionDTO object to log

        Returns:
            The logged action
        """
        return self._log_admin_action(
            action_type=action.action_type,
            resource_type=action.resource_type,
            resource_id=action.resource_id,
            description=action.description,
            performed_by=action.performed_by,
        )

    def _log_admin_action(
        self,
        action_type: str,
        resource_type: str = "",
        resource_id: Optional[int] = None,
        description: str = "",
        performed_by: Optional[str] = None,
    ) -> AdminActionDTO:
        """
        Internal method to log admin actions.

        Args:
            action_type: Type of action
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            description: Description of the action
            performed_by: User who performed the action

        Returns:
            The logged action
        """
        try:
            worksheet = self._get_worksheet_safe("admin_logs")
            now = datetime.now(timezone.utc).isoformat()
            row = [
                "",  # ID will be auto-assigned
                action_type,
                resource_type,
                resource_id or "",
                description,
                performed_by or "system",
                now,
            ]
            worksheet.append_row(row)
            logger.debug(f"Logged admin action: {action_type} - {description}")
            return AdminActionDTO(
                action_type=action_type,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                performed_by=performed_by or "system",
                created_at=self._parse_datetime(now),
            )
        except Exception as e:
            logger.warning(f"Failed to log admin action: {e}")
            return AdminActionDTO(
                action_type=action_type,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                performed_by=performed_by or "system",
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((gspread.exceptions.APIError, OSError)),
    )
    def log_error(self, error: ErrorLogDTO) -> ErrorLogDTO:
        """
        Log an error to the Sheets.

        Args:
            error: ErrorLogDTO object to log

        Returns:
            The logged error
        """
        return self._log_error(
            error_type=error.error_type,
            message=error.message,
            context=error.context,
            traceback=error.traceback,
        )

    def _log_error(
        self,
        error_type: str,
        message: str,
        context: Optional[str] = None,
        traceback: Optional[str] = None,
    ) -> ErrorLogDTO:
        """
        Internal method to log errors.

        Args:
            error_type: Type of error
            message: Error message
            context: Additional context
            traceback: Error traceback

        Returns:
            The logged error
        """
        try:
            worksheet = self._get_worksheet_safe("errors")
            now = datetime.now(timezone.utc).isoformat()
            row = [
                "",  # ID will be auto-assigned
                error_type,
                message,
                context or "",
                traceback or "",
                now,
            ]
            worksheet.append_row(row)
            logger.debug(f"Logged error: {error_type} - {message}")
            return ErrorLogDTO(
                error_type=error_type,
                message=message,
                context=context,
                traceback=traceback,
                created_at=self._parse_datetime(now),
            )
        except Exception as e:
            logger.warning(f"Failed to log error to sheets: {e}")
            return ErrorLogDTO(
                error_type=error_type,
                message=message,
                context=context,
                traceback=traceback,
            )

    # Utility methods

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        """
        Parse datetime string to datetime object.

        Args:
            value: String value to parse

        Returns:
            Parsed datetime or None
        """
        if not value:
            return None
        try:
            # Try ISO format first
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            # Try other common formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            logger.warning(f"Could not parse datetime: {value}")
            return None

    # Sync operations

    def sync_push_changes(self, local_specialists: list[SpecialistDTO], local_bookings: list[BookingDTO]) -> SyncState:
        """
        Push local changes to Google Sheets.

        Args:
            local_specialists: List of specialists to sync
            local_bookings: List of bookings to sync

        Returns:
            SyncState object with sync statistics
        """
        self.sync_state = SyncState()

        try:
            # Sync specialists
            try:
                remote_specialists = self.read_specialists()
                self._sync_specialists(local_specialists, remote_specialists)
            except RecoverableExternalError as e:
                logger.error(f"Failed to sync specialists: {e}")
                self.sync_state.errors.append(f"Specialist sync failed: {str(e)}")
                self._log_error("sync_error", f"Failed to sync specialists: {str(e)}")

            # Sync bookings
            try:
                remote_bookings = self.read_bookings()
                self._sync_bookings(local_bookings, remote_bookings)
            except RecoverableExternalError as e:
                logger.error(f"Failed to sync bookings: {e}")
                self.sync_state.errors.append(f"Booking sync failed: {str(e)}")
                self._log_error("sync_error", f"Failed to sync bookings: {str(e)}")

            self.sync_state.last_synced = datetime.now(timezone.utc)
            logger.info(f"Push sync completed: {self.sync_state.items_pushed} items pushed")
            return self.sync_state

        except Exception as e:
            logger.error(f"Unexpected error during push sync: {e}")
            self.sync_state.errors.append(f"Unexpected error: {str(e)}")
            self._log_error("sync_error", f"Unexpected sync error: {str(e)}")
            return self.sync_state

    def sync_pull_changes(self) -> SyncState:
        """
        Pull remote changes from Google Sheets.

        Returns:
            SyncState object with sync statistics
        """
        self.sync_state = SyncState()

        try:
            # Pull specialists
            try:
                specialists = self.read_specialists()
                self.sync_state.items_pulled += len(specialists)
                logger.info(f"Pulled {len(specialists)} specialists from Sheets")
            except RecoverableExternalError as e:
                logger.error(f"Failed to pull specialists: {e}")
                self.sync_state.errors.append(f"Failed to pull specialists: {str(e)}")
                self._log_error("sync_error", f"Failed to pull specialists: {str(e)}")

            # Pull bookings
            try:
                bookings = self.read_bookings()
                self.sync_state.items_pulled += len(bookings)
                logger.info(f"Pulled {len(bookings)} bookings from Sheets")
            except RecoverableExternalError as e:
                logger.error(f"Failed to pull bookings: {e}")
                self.sync_state.errors.append(f"Failed to pull bookings: {str(e)}")
                self._log_error("sync_error", f"Failed to pull bookings: {str(e)}")

            self.sync_state.last_synced = datetime.now(timezone.utc)
            logger.info(f"Pull sync completed: {self.sync_state.items_pulled} items pulled")
            return self.sync_state

        except Exception as e:
            logger.error(f"Unexpected error during pull sync: {e}")
            self.sync_state.errors.append(f"Unexpected error: {str(e)}")
            self._log_error("sync_error", f"Unexpected sync error: {str(e)}")
            return self.sync_state

    def _sync_specialists(self, local: list[SpecialistDTO], remote: list[SpecialistDTO]) -> None:
        """Reconcile specialists between local and remote."""
        local_by_id = {s.id: s for s in local if s.id}
        remote_by_id = {s.id: s for s in remote if s.id}

        # Add new specialists (local only)
        for specialist in local:
            if specialist.id and specialist.id not in remote_by_id:
                try:
                    self.add_specialist(specialist)
                    self.sync_state.items_pushed += 1
                except RecoverableExternalError as e:
                    logger.error(f"Failed to add specialist: {e}")
                    self.sync_state.errors.append(f"Failed to add specialist {specialist.name}: {str(e)}")

        # Update existing specialists
        for specialist_id, specialist in local_by_id.items():
            if specialist_id in remote_by_id:
                remote = remote_by_id[specialist_id]
                if specialist.updated_at and remote.updated_at:
                    if specialist.updated_at > remote.updated_at:
                        try:
                            self.update_specialist(specialist_id, specialist)
                            self.sync_state.items_pushed += 1
                        except RecoverableExternalError as e:
                            logger.error(f"Failed to update specialist: {e}")
                            self.sync_state.errors.append(f"Failed to update specialist {specialist.name}: {str(e)}")

    def _sync_bookings(self, local: list[BookingDTO], remote: list[BookingDTO]) -> None:
        """Reconcile bookings between local and remote."""
        local_by_id = {b.id: b for b in local if b.id}
        remote_by_id = {b.id: b for b in remote if b.id}

        # Add new bookings (local only)
        for booking in local:
            if booking.id and booking.id not in remote_by_id:
                try:
                    self.add_booking(booking)
                    self.sync_state.items_pushed += 1
                except RecoverableExternalError as e:
                    logger.error(f"Failed to add booking: {e}")
                    self.sync_state.errors.append(f"Failed to add booking for {booking.client_name}: {str(e)}")
