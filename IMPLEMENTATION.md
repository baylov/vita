# Google Sheets Manager Implementation

## Overview

The GoogleSheetsManager implements bi-directional synchronization between a SQL database and Google Sheets. It provides comprehensive CRUD operations, resilient retry logic, audit logging, and sync capabilities.

## Architecture

### Core Components

1. **GoogleSheetsManager** (`integrations/google/sheets_manager.py`)
   - Main integration class
   - Handles authentication via service_account.json
   - Manages worksheet lifecycle
   - Provides read/write operations
   - Implements sync routines

2. **Data Models** (`models.py`)
   - SpecialistDTO: Specialist information
   - ScheduleDTO: Work schedule information
   - BookingDTO: Booking/appointment records
   - DayOffDTO: Day-off records
   - AdminActionDTO: Administrative action logs
   - ErrorLogDTO: Error logs
   - SyncState: Sync operation state tracking

3. **Exception Handling** (`exceptions.py`)
   - Custom exception hierarchy
   - RecoverableExternalError for API failures
   - SheetsInitializationError for init failures
   - SyncError and ConflictError for sync operations

4. **Configuration** (`settings.py`)
   - Pydantic-based settings management
   - Environment variable support
   - Service account path configuration

## Initialization

The manager automatically initializes on instantiation:

```python
from integrations.google.sheets_manager import GoogleSheetsManager

manager = GoogleSheetsManager(
    spreadsheet_id="your_sheet_id",
    service_account_path="/path/to/service_account.json"
)
```

### Automatic Worksheet Creation

On initialization, the manager ensures all required worksheets exist:
- Creates missing worksheets
- Adds appropriate headers
- Logs the initialization operation

## Operations

### Read Operations

All read operations retry on transient failures:

```python
# Read specialists
specialists = manager.read_specialists()  # Returns list[SpecialistDTO]

# Read schedule
schedules = manager.read_schedule()  # Returns list[ScheduleDTO]

# Read bookings
bookings = manager.read_bookings()  # Returns list[BookingDTO]
```

### Write Operations

```python
from models import SpecialistDTO, BookingDTO, DayOffDTO

# Add specialist
specialist = SpecialistDTO(
    name="Dr. John Doe",
    specialization="Cardiology",
    phone="+1234567890",
    email="john@example.com"
)
manager.add_specialist(specialist)

# Update specialist
manager.update_specialist(specialist_id=1, specialist=specialist)

# Delete specialist
manager.delete_specialist(specialist_id=1)

# Add booking
booking = BookingDTO(
    specialist_id=1,
    client_name="Alice Johnson",
    booking_datetime=datetime(2025, 1, 15, 10, 0),
    duration_minutes=60,
    status="confirmed"
)
manager.add_booking(booking)

# Add day off
day_off = DayOffDTO(
    specialist_id=1,
    date="2025-01-20",
    reason="Vacation"
)
manager.add_day_off(day_off)
```

### Synchronization Operations

#### Push Changes (Local to Remote)

```python
local_specialists = [...]  # From database
local_bookings = [...]      # From database

sync_state = manager.sync_push_changes(local_specialists, local_bookings)

print(f"Items pushed: {sync_state.items_pushed}")
print(f"Conflicts detected: {sync_state.conflicts_detected}")
print(f"Errors: {sync_state.errors}")
```

#### Pull Changes (Remote to Local)

```python
sync_state = manager.sync_pull_changes()

print(f"Items pulled: {sync_state.items_pulled}")
print(f"Last synced: {sync_state.last_synced}")
```

### Logging Operations

```python
# Log admin action
manager._log_admin_action(
    action_type="create",
    resource_type="specialist",
    description="Added new specialist",
    performed_by="admin@example.com"
)

# Log error (automatic for API failures)
manager._log_error(
    error_type="api_error",
    message="Failed to fetch data",
    context="During sync operation"
)
```

## Retry Logic

The manager uses tenacity for resilient retry logic:

- **Max Attempts**: 3
- **Backoff Strategy**: Exponential
- **Initial Delay**: 2 seconds
- **Maximum Delay**: 10 seconds
- **Retry Conditions**: gspread API errors and OS errors

Retry decorators are applied to:
- `read_specialists()`
- `read_schedule()`
- `read_bookings()`
- `add_specialist()`
- `update_specialist()`
- `delete_specialist()`
- `add_booking()`
- `add_day_off()`
- `log_admin_action()`
- `log_error()`

## Error Handling

All API operations are wrapped with:

1. **Retry Logic**: Automatic retries for transient failures
2. **Error Logging**: Failed operations logged to "Ошибки" worksheet
3. **Exception Propagation**: After retries exhausted, tenacity.RetryError is raised

Example error handling:

```python
from tenacity import RetryError
from exceptions import SheetsError

try:
    specialists = manager.read_specialists()
except RetryError as e:
    print(f"Failed after retries: {e}")
except SheetsError as e:
    print(f"Sheets operation failed: {e}")
```

## Sync Conflict Resolution

The sync functions use timestamp-based conflict detection:

1. **Local Newer**: Local version has newer timestamp → update remote
2. **Remote Newer**: Remote version has newer timestamp → skip local update
3. **No Timestamp**: Use insertion order (skip if already exists)

```python
# Sync specialists - updates based on updated_at timestamp
manager._sync_specialists(local_specialists, remote_specialists)

# Sync bookings - updates based on updated_at timestamp
manager._sync_bookings(local_bookings, remote_bookings)
```

## Worksheets and Headers

### Specialists Sheet
Columns: ID | ФИ | Специализация | Телефон | Email | Активен | Создано | Обновлено

### Schedule Sheet
Columns: ID | Специалист ID | День недели | Время начала | Время конца | Доступен | Создано | Обновлено

### Days Off Sheet
Columns: ID | Специалист ID | Дата | Причина | Создано

### Bookings Sheet
Columns: ID | Специалист ID | Клиент | Дата/Время | Длительность мин | Заметки | Статус | Создано | Обновлено

### Admin Logs Sheet
Columns: ID | Тип действия | Тип ресурса | ID ресурса | Описание | Выполнил | Создано

### Errors Sheet
Columns: ID | Тип ошибки | Сообщение | Контекст | Трассировка стека | Создано

## Configuration

### Environment Variables

```bash
SERVICE_ACCOUNT_JSON_PATH=/path/to/service_account.json
GOOGLE_SHEETS_ID=your_spreadsheet_id
```

### .env File

Create a `.env` file in the project root:

```
SERVICE_ACCOUNT_JSON_PATH=service_account.json
GOOGLE_SHEETS_ID=1aBc2DeF3gHiJ4kLmNoPqRsT5uVwXyZ
```

## Testing

The test suite covers:

- **Initialization**: Worksheet creation and configuration
- **Read Operations**: Data retrieval with mocking
- **Write Operations**: CRUD operations
- **Retry Logic**: Automatic retries on API errors
- **Sync Operations**: Bi-directional synchronization
- **Logging**: Admin actions and error logging
- **Utility Methods**: Datetime parsing and data transformation

### Running Tests

```bash
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest tests/test_sheets_manager.py  # Specific file
pytest -k test_retry           # Specific test pattern
```

### Test Coverage

- 26 comprehensive tests
- All core functionality tested with mocks
- API error scenarios covered
- Retry exhaustion tested
- Sync conflict resolution tested

## Best Practices

1. **Error Handling**: Always catch RetryError and SheetsError exceptions
2. **Timestamps**: Use datetime.now(timezone.utc) for consistency
3. **Logging**: Enable logging to track operations and errors
4. **Sync Frequency**: Implement periodic sync to keep data in sync
5. **Conflict Resolution**: Always use timestamp comparison for sync decisions
6. **Data Validation**: Validate DTOs before sending to Sheets

## Example: Complete Sync Flow

```python
from integrations.google.sheets_manager import GoogleSheetsManager
from models import SpecialistDTO, BookingDTO, SyncState
from tenacity import RetryError

# Initialize manager
manager = GoogleSheetsManager("sheet_id", "service_account.json")

# Pull remote changes first
pull_state = manager.sync_pull_changes()
print(f"Pulled {pull_state.items_pulled} items from Sheets")

# Prepare local data
local_specialists = get_specialists_from_db()
local_bookings = get_bookings_from_db()

# Push local changes
push_state = manager.sync_push_changes(local_specialists, local_bookings)
print(f"Pushed {push_state.items_pushed} items to Sheets")

# Check for errors
if push_state.errors:
    print(f"Sync errors: {push_state.errors}")
    # Handle errors - potentially switch to manual mode
```

## Deployment

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Service Account**:
   - Create a service account in Google Cloud Console
   - Download the JSON key file
   - Set SERVICE_ACCOUNT_JSON_PATH environment variable

3. **Configure Spreadsheet**:
   - Create a Google Sheet with the desired ID
   - Share it with the service account email

4. **Environment Setup**:
   - Set GOOGLE_SHEETS_ID environment variable
   - Configure logging as needed

5. **Run Integration**:
   - Import and instantiate GoogleSheetsManager
   - Call read/write/sync operations as needed
   - Monitor error logs in the "Ошибки" worksheet
