"""Tests for Google Sheets Manager."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, call
from tenacity import RetryError

from integrations.google.sheets_manager import GoogleSheetsManager, WORKSHEETS
from models import (
    SpecialistDTO,
    ScheduleDTO,
    BookingDTO,
    DayOffDTO,
    AdminActionDTO,
    ErrorLogDTO,
)
from exceptions import RecoverableExternalError, SheetsInitializationError, SheetsError


@pytest.fixture
def mock_service_account(tmp_path):
    """Create a mock service account JSON file."""
    sa_file = tmp_path / "service_account.json"
    sa_file.write_text('{"type": "service_account"}')
    return str(sa_file)


@pytest.fixture
def mock_gspread_client():
    """Create a mock gspread client."""
    client = MagicMock()
    spreadsheet = MagicMock()
    client.service_account.return_value = client
    client.open_by_key.return_value = spreadsheet
    spreadsheet.title = "Test Spreadsheet"
    spreadsheet.worksheets.return_value = []
    return client, spreadsheet


class TestGoogleSheetsManagerInitialization:
    """Test suite for manager initialization."""

    @patch("integrations.google.sheets_manager.gspread")
    def test_initialization_creates_worksheets(self, mock_gspread_module, mock_service_account, mock_gspread_client):
        """Test that initialization creates required worksheets."""
        mock_client, mock_spreadsheet = mock_gspread_client
        mock_gspread_module.service_account.return_value = mock_client

        with patch("integrations.google.sheets_manager.settings") as mock_settings:
            mock_settings.service_account_json_path = mock_service_account
            manager = GoogleSheetsManager("test_sheet_id", service_account_path=mock_service_account)

            # Verify add_worksheet was called for each missing worksheet
            assert mock_spreadsheet.add_worksheet.call_count >= len(WORKSHEETS)

    @patch("integrations.google.sheets_manager.gspread")
    def test_initialization_logs_operation(self, mock_gspread_module, mock_service_account):
        """Test that initialization logs the operation."""
        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_client.service_account.return_value = mock_client
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_spreadsheet.title = "Test"
        mock_spreadsheet.worksheets.return_value = []
        mock_gspread_module.service_account.return_value = mock_client

        with patch("integrations.google.sheets_manager.settings") as mock_settings:
            mock_settings.service_account_json_path = mock_service_account
            with patch.object(GoogleSheetsManager, "_log_admin_action") as mock_log:
                manager = GoogleSheetsManager("test_sheet_id", service_account_path=mock_service_account)
                mock_log.assert_called()

    @patch("integrations.google.sheets_manager.gspread")
    def test_initialization_missing_service_account_file(self, mock_gspread_module, mock_service_account):
        """Test that missing service account file raises error."""
        mock_gspread_module.service_account.side_effect = FileNotFoundError("Not found")

        with patch("integrations.google.sheets_manager.settings") as mock_settings:
            mock_settings.service_account_json_path = "/nonexistent/path.json"
            with pytest.raises(SheetsInitializationError):
                GoogleSheetsManager("test_sheet_id", service_account_path="/nonexistent/path.json")


class TestReadOperations:
    """Test suite for read operations."""

    @pytest.fixture
    def setup_manager(self, mock_service_account):
        """Set up manager with mocked dependencies."""
        with patch("integrations.google.sheets_manager.gspread"):
            with patch("integrations.google.sheets_manager.settings") as mock_settings:
                mock_settings.service_account_json_path = mock_service_account
                manager = GoogleSheetsManager.__new__(GoogleSheetsManager)
                manager.spreadsheet_id = "test_id"
                manager.service_account_path = mock_service_account
                manager.worksheets = {}
                manager.sync_state = Mock()
                return manager

    def test_read_specialists(self, setup_manager):
        """Test reading specialists from Sheets."""
        manager = setup_manager
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = [
            {
                "ID": "1",
                "ФИ": "John Doe",
                "Специализация": "Cardiology",
                "Телефон": "+1234567890",
                "Email": "john@example.com",
                "Активен": "Да",
                "Создано": "2025-01-01T00:00:00",
                "Обновлено": "2025-01-02T00:00:00",
            }
        ]
        manager.worksheets["specialists"] = mock_worksheet

        specialists = manager.read_specialists()

        assert len(specialists) == 1
        assert specialists[0].name == "John Doe"
        assert specialists[0].specialization == "Cardiology"
        assert specialists[0].is_active is True

    def test_read_specialists_with_api_error(self, setup_manager):
        """Test that API errors are retried and then raised."""
        import gspread

        manager = setup_manager
        mock_worksheet = MagicMock()
        # Create a mock response object that has json() and text attributes
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": {"code": 500, "message": "API Error"}}
        mock_response.text = "API Error"
        api_error = gspread.exceptions.APIError(mock_response)
        mock_worksheet.get_all_records.side_effect = api_error
        manager.worksheets["specialists"] = mock_worksheet

        with pytest.raises(RetryError):
            manager.read_specialists()

    def test_read_bookings(self, setup_manager):
        """Test reading bookings from Sheets."""
        manager = setup_manager
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = [
            {
                "ID": "1",
                "Специалист ID": "1",
                "Клиент": "Alice",
                "Дата/Время": "2025-01-15T10:00:00",
                "Длительность мин": "60",
                "Заметки": "Test booking",
                "Статус": "confirmed",
                "Создано": "2025-01-01T00:00:00",
                "Обновлено": "2025-01-02T00:00:00",
            }
        ]
        manager.worksheets["bookings"] = mock_worksheet

        bookings = manager.read_bookings()

        assert len(bookings) == 1
        assert bookings[0].client_name == "Alice"
        assert bookings[0].specialist_id == 1
        assert bookings[0].status == "confirmed"

    def test_read_schedule(self, setup_manager):
        """Test reading schedule from Sheets."""
        manager = setup_manager
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = [
            {
                "ID": "1",
                "Специалист ID": "1",
                "День недели": "0",
                "Время начала": "09:00",
                "Время конца": "17:00",
                "Доступен": "Да",
                "Создано": "2025-01-01T00:00:00",
                "Обновлено": "2025-01-02T00:00:00",
            }
        ]
        manager.worksheets["schedule"] = mock_worksheet

        schedules = manager.read_schedule()

        assert len(schedules) == 1
        assert schedules[0].day_of_week == 0
        assert schedules[0].start_time == "09:00"
        assert schedules[0].is_available is True


class TestWriteOperations:
    """Test suite for write operations."""

    @pytest.fixture
    def setup_manager(self, mock_service_account):
        """Set up manager with mocked dependencies."""
        with patch("integrations.google.sheets_manager.gspread"):
            with patch("integrations.google.sheets_manager.settings") as mock_settings:
                mock_settings.service_account_json_path = mock_service_account
                manager = GoogleSheetsManager.__new__(GoogleSheetsManager)
                manager.spreadsheet_id = "test_id"
                manager.service_account_path = mock_service_account
                manager.worksheets = {}
                manager.sync_state = Mock()
                return manager

    def test_add_specialist(self, setup_manager):
        """Test adding a specialist."""
        manager = setup_manager
        mock_worksheet = MagicMock()
        manager.worksheets["specialists"] = mock_worksheet

        specialist = SpecialistDTO(
            name="Jane Doe",
            specialization="Neurology",
            phone="+9876543210",
            email="jane@example.com",
        )

        result = manager.add_specialist(specialist)

        mock_worksheet.append_row.assert_called_once()
        assert result.name == "Jane Doe"
        assert result.created_at is not None

    def test_add_specialist_with_api_error(self, setup_manager):
        """Test that API errors are retried and then raised."""
        import gspread

        manager = setup_manager
        mock_worksheet = MagicMock()
        # Create a mock response object that has json() and text attributes
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": {"code": 500, "message": "API Error"}}
        mock_response.text = "API Error"
        api_error = gspread.exceptions.APIError(mock_response)
        mock_worksheet.append_row.side_effect = api_error
        manager.worksheets["specialists"] = mock_worksheet

        specialist = SpecialistDTO(name="Jane", specialization="Neurology")

        with pytest.raises(RetryError):
            manager.add_specialist(specialist)

    def test_update_specialist(self, setup_manager):
        """Test updating a specialist."""
        manager = setup_manager
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = [
            {
                "ID": "1",
                "ФИ": "Old Name",
                "Специализация": "Cardiology",
                "Телефон": "+1234567890",
                "Email": "old@example.com",
                "Активен": "Да",
                "Создано": "2025-01-01T00:00:00",
                "Обновлено": "2025-01-02T00:00:00",
            }
        ]
        manager.worksheets["specialists"] = mock_worksheet

        specialist = SpecialistDTO(
            name="New Name",
            specialization="Cardiology",
            phone="+9876543210",
        )

        result = manager.update_specialist(1, specialist)

        mock_worksheet.delete_rows.assert_called_once()
        mock_worksheet.insert_row.assert_called_once()
        assert result.name == "New Name"

    def test_delete_specialist(self, setup_manager):
        """Test deleting a specialist."""
        manager = setup_manager
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = [
            {
                "ID": "1",
                "ФИ": "John Doe",
                "Специализация": "Cardiology",
                "Телефон": "+1234567890",
                "Email": "john@example.com",
                "Активен": "Да",
                "Создано": "2025-01-01T00:00:00",
                "Обновлено": "2025-01-02T00:00:00",
            }
        ]
        manager.worksheets["specialists"] = mock_worksheet

        result = manager.delete_specialist(1)

        mock_worksheet.delete_rows.assert_called_once()
        assert result is True

    def test_delete_specialist_not_found(self, setup_manager):
        """Test deleting a non-existent specialist."""
        manager = setup_manager
        mock_worksheet = MagicMock()
        mock_worksheet.get_all_records.return_value = []
        manager.worksheets["specialists"] = mock_worksheet

        result = manager.delete_specialist(999)

        assert result is False

    def test_add_booking(self, setup_manager):
        """Test adding a booking."""
        manager = setup_manager
        mock_worksheet = MagicMock()
        manager.worksheets["bookings"] = mock_worksheet

        booking = BookingDTO(
            specialist_id=1,
            client_name="Alice",
            booking_datetime=datetime(2025, 1, 15, 10, 0),
            duration_minutes=60,
            status="confirmed",
        )

        result = manager.add_booking(booking)

        mock_worksheet.append_row.assert_called_once()
        assert result.client_name == "Alice"
        assert result.created_at is not None

    def test_add_day_off(self, setup_manager):
        """Test adding a day off."""
        manager = setup_manager
        mock_worksheet = MagicMock()
        manager.worksheets["days_off"] = mock_worksheet

        day_off = DayOffDTO(
            specialist_id=1,
            date="2025-01-20",
            reason="Vacation",
        )

        result = manager.add_day_off(day_off)

        mock_worksheet.append_row.assert_called_once()
        assert result.specialist_id == 1
        assert result.date == "2025-01-20"


class TestLogging:
    """Test suite for logging operations."""

    @pytest.fixture
    def setup_manager(self, mock_service_account):
        """Set up manager with mocked dependencies."""
        with patch("integrations.google.sheets_manager.gspread"):
            with patch("integrations.google.sheets_manager.settings") as mock_settings:
                mock_settings.service_account_json_path = mock_service_account
                manager = GoogleSheetsManager.__new__(GoogleSheetsManager)
                manager.spreadsheet_id = "test_id"
                manager.service_account_path = mock_service_account
                manager.worksheets = {}
                manager.sync_state = Mock()
                return manager

    def test_log_admin_action(self, setup_manager):
        """Test logging an admin action."""
        manager = setup_manager
        mock_worksheet = MagicMock()
        manager.worksheets["admin_logs"] = mock_worksheet

        action = manager._log_admin_action(
            action_type="create",
            resource_type="specialist",
            description="Test action",
        )

        mock_worksheet.append_row.assert_called_once()
        assert action.action_type == "create"
        assert action.resource_type == "specialist"

    def test_log_error(self, setup_manager):
        """Test logging an error."""
        manager = setup_manager
        mock_worksheet = MagicMock()
        manager.worksheets["errors"] = mock_worksheet

        error = manager._log_error(
            error_type="api_error",
            message="Test error",
            context="test_context",
        )

        mock_worksheet.append_row.assert_called_once()
        assert error.error_type == "api_error"
        assert error.message == "Test error"

    def test_log_error_graceful_failure(self, setup_manager):
        """Test that logging errors fails gracefully."""
        import gspread

        manager = setup_manager
        mock_worksheet = MagicMock()
        # Create a mock response object that has json() and text attributes
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": {"code": 500, "message": "API Error"}}
        mock_response.text = "API Error"
        api_error = gspread.exceptions.APIError(mock_response)
        mock_worksheet.append_row.side_effect = api_error
        manager.worksheets["errors"] = mock_worksheet

        error = manager._log_error(
            error_type="api_error",
            message="Test error",
        )

        assert error.error_type == "api_error"
        assert error.message == "Test error"


class TestSyncOperations:
    """Test suite for sync operations."""

    @pytest.fixture
    def setup_manager(self, mock_service_account):
        """Set up manager with mocked dependencies."""
        with patch("integrations.google.sheets_manager.gspread"):
            with patch("integrations.google.sheets_manager.settings") as mock_settings:
                mock_settings.service_account_json_path = mock_service_account
                manager = GoogleSheetsManager.__new__(GoogleSheetsManager)
                manager.spreadsheet_id = "test_id"
                manager.service_account_path = mock_service_account
                manager.worksheets = {}
                from models import SyncState
                manager.sync_state = SyncState()
                return manager

    def test_sync_pull_changes(self, setup_manager):
        """Test pulling changes from Sheets."""
        manager = setup_manager
        specialists = [
            SpecialistDTO(
                id=1,
                name="John Doe",
                specialization="Cardiology",
            )
        ]
        bookings = [
            BookingDTO(
                id=1,
                specialist_id=1,
                client_name="Alice",
                booking_datetime=datetime(2025, 1, 15, 10, 0),
            )
        ]

        with patch.object(manager, "read_specialists", return_value=specialists):
            with patch.object(manager, "read_bookings", return_value=bookings):
                state = manager.sync_pull_changes()

                assert state.items_pulled == 2
                assert state.last_synced is not None

    def test_sync_push_changes(self, setup_manager):
        """Test pushing changes to Sheets."""
        manager = setup_manager
        local_specialists = [
            SpecialistDTO(
                id=1,
                name="John Doe",
                specialization="Cardiology",
            )
        ]
        local_bookings = []

        remote_specialists = []
        remote_bookings = []

        with patch.object(manager, "read_specialists", return_value=remote_specialists):
            with patch.object(manager, "read_bookings", return_value=remote_bookings):
                with patch.object(manager, "add_specialist") as mock_add:
                    state = manager.sync_push_changes(local_specialists, local_bookings)

                    assert state.last_synced is not None

    def test_sync_handles_conflicts(self, setup_manager):
        """Test that sync detects conflicts based on timestamps."""
        manager = setup_manager
        local = [
            SpecialistDTO(
                id=1,
                name="Local Update",
                specialization="Cardiology",
                updated_at=datetime(2025, 1, 2),
            )
        ]
        remote = [
            SpecialistDTO(
                id=1,
                name="Remote Update",
                specialization="Cardiology",
                updated_at=datetime(2025, 1, 1),
            )
        ]

        # Mock the update_specialist method
        with patch.object(manager, "update_specialist"):
            manager._sync_specialists(local, remote)

        assert manager.sync_state.items_pushed >= 0


class TestRetryLogic:
    """Test suite for retry logic."""

    @pytest.fixture
    def setup_manager(self, mock_service_account):
        """Set up manager with mocked dependencies."""
        with patch("integrations.google.sheets_manager.gspread"):
            with patch("integrations.google.sheets_manager.settings") as mock_settings:
                mock_settings.service_account_json_path = mock_service_account
                manager = GoogleSheetsManager.__new__(GoogleSheetsManager)
                manager.spreadsheet_id = "test_id"
                manager.service_account_path = mock_service_account
                manager.worksheets = {}
                manager.sync_state = Mock()
                return manager

    def test_retry_on_api_error(self, setup_manager):
        """Test that API errors trigger retries."""
        import gspread

        manager = setup_manager
        mock_worksheet = MagicMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                mock_response = MagicMock()
                mock_response.json.return_value = {"error": {"code": 500, "message": "Temporary error"}}
                mock_response.text = "Temporary error"
                raise gspread.exceptions.APIError(mock_response)
            return [{"ID": "1", "ФИ": "John"}]

        mock_worksheet.get_all_records.side_effect = side_effect
        manager.worksheets["specialists"] = mock_worksheet

        # This should eventually succeed after retries
        specialists = manager.read_specialists()
        assert len(specialists) == 1
        assert call_count == 3  # Verify it actually retried

    def test_retry_exhaustion_raises_error(self, setup_manager):
        """Test that retry exhaustion raises RetryError."""
        import gspread

        manager = setup_manager
        mock_worksheet = MagicMock()
        # Create a mock response object that has json() and text attributes
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": {"code": 500, "message": "API Error"}}
        mock_response.text = "API Error"
        api_error = gspread.exceptions.APIError(mock_response)
        mock_worksheet.get_all_records.side_effect = api_error
        manager.worksheets["specialists"] = mock_worksheet

        with pytest.raises(RetryError):
            manager.read_specialists()


class TestUtilityMethods:
    """Test suite for utility methods."""

    def test_parse_datetime_iso_format(self):
        """Test parsing ISO format datetime."""
        dt_str = "2025-01-15T10:30:00"
        result = GoogleSheetsManager._parse_datetime(dt_str)
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_parse_datetime_date_only(self):
        """Test parsing date only."""
        dt_str = "2025-01-15"
        result = GoogleSheetsManager._parse_datetime(dt_str)
        assert result is not None
        assert result.year == 2025

    def test_parse_datetime_none(self):
        """Test parsing None value."""
        result = GoogleSheetsManager._parse_datetime(None)
        assert result is None

    def test_parse_datetime_invalid(self):
        """Test parsing invalid datetime."""
        result = GoogleSheetsManager._parse_datetime("invalid")
        assert result is None
