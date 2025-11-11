# ORM Layer

This project implements a comprehensive ORM layer using SQLAlchemy with Alembic migrations.

## Structure

```
data/
├── __init__.py          # Package exports
├── database.py          # Database configuration and initialization
├── models.py            # SQLAlchemy ORM models
└── repositories.py      # Repository pattern for CRUD operations

alembic/
├── versions/            # Migration files
├── env.py              # Alembic environment configuration
└── script.py.mako       # Migration template

tests/
└── test_orm.py         # Unit tests for ORM functionality
```

## Models

### Specialist
Represents service providers with fields for:
- Basic info: name, email, phone
- Professional details: specialization, bio, languages
- Status: active/inactive flag
- Timestamps: created_at, updated_at

### Schedule
Defines availability patterns for specialists:
- Day of week (0=Monday to 6=Sunday)
- Start and end times
- Active status
- Unique constraint per specialist/day/time

### DayOff
Records specific days when specialists are unavailable:
- Date and reason
- Active status
- Unique constraint per specialist/date

### Booking
Manages client appointments:
- Client information (name, email, phone)
- Booking date/time with duration
- Status tracking (pending, confirmed, cancelled, completed)
- Notes field
- Unique constraint per specialist/date/time

### UserSession
Handles client session management:
- Session ID and client info
- Expiration tracking
- Active status

### AdminLog
Audit trail for administrative actions:
- Admin ID and action performed
- Resource type and ID
- Details, IP address, user agent
- Timestamps

## Database Initialization

The `init_db()` function handles database setup:

1. **Primary**: Runs Alembic migrations if available
2. **Fallback**: Creates tables from metadata if migrations fail

### Usage

```python
from data.database import init_db

# Initialize database (runs migrations or creates tables)
init_db()
```

### Environment Variables

- `DB_URL`: Database connection string (defaults to `sqlite:///./app.db`)
- `SQLALCHEMY_ECHO`: Enable SQL logging (defaults to `false`)

## Repository Pattern

Each model has a corresponding repository class providing:

### CRUD Operations
- `create()`: Create new records
- `get_by_id()`: Retrieve by primary key
- `update()`: Update existing records
- `delete()`: Soft delete (set active=False)

### Query Methods
- `get_all()`: List all records (with optional filters)
- `search()`: Text search across relevant fields
- `get_by_*()`: Model-specific query methods

### Example Usage

```python
from data.database import get_db
from data.repositories import SpecialistRepository

# Get database session
db = get_db()

# Create repository
specialist_repo = SpecialistRepository(db)

# Create a specialist
specialist = specialist_repo.create({
    "name": "Dr. John Doe",
    "email": "john@example.com",
    "specialization": "Cardiology",
    "languages": "English, Spanish"
})

# Search specialists
results = specialist_repo.search("cardiology")

# Update specialist
updated = specialist_repo.update(specialist.id, {
    "phone": "+1234567890"
})
```

## Testing

Run the comprehensive test suite:

```bash
# Activate virtual environment
source venv/bin/activate

# Run tests
python -m pytest tests/ -v
```

### Test Coverage

- **Model Tests**: CRUD operations, relationships, constraints
- **Repository Tests**: All repository methods
- **Database Tests**: Initialization with different configurations
- **Integration Tests**: Model relationships and cascading deletes

## Migrations

### Create New Migration

```bash
# Activate virtual environment
source venv/bin/activate

# Generate migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head
```

### Migration Files

Located in `alembic/versions/` with automatic table creation, indexes, and constraints.

## Dependencies

- `sqlalchemy>=2.0.0`: ORM and database toolkit
- `alembic>=1.12.0`: Database migration tool
- `pytest>=7.0.0`: Testing framework

## Features

### Database Constraints
- Foreign key relationships with cascade rules
- Composite unique constraints
- Proper indexing for performance

### Timezone Support
- All timestamp fields are timezone-aware
- Automatic timezone handling with `func.now()`

### Relationship Management
- Proper cascade delete configuration
- Bidirectional relationships
- Lazy loading for performance

### Error Handling
- Graceful fallback from migrations to direct table creation
- Comprehensive validation in repositories
- Soft delete patterns where appropriate