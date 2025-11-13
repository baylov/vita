# Alembic Database Migrations

This directory contains Alembic database migrations for the VitaPlus bot project.

## Overview

Alembic is used to manage database schema changes in a version-controlled manner. The configuration allows the project to work with both PostgreSQL and SQLite databases.

## Configuration

- **alembic.ini**: Main Alembic configuration file
- **env.py**: Environment setup that configures how migrations run
- **script.py.mako**: Template for generating new migration files
- **versions/**: Directory containing migration scripts

## Database URL Configuration

The database URL is automatically retrieved from:
1. `DATABASE_URL` environment variable, or
2. Application settings (`settings.database_url`), or
3. Falls back to `sqlite:///./vita.db`

This is configured in `data/database.py` and used by `alembic/env.py`.

## Usage

### Running Migrations

To upgrade the database to the latest version:
```bash
alembic upgrade head
```

To downgrade to a specific revision:
```bash
alembic downgrade base  # Remove all tables
alembic downgrade -1     # Downgrade by one revision
```

### Checking Current Version

```bash
alembic current
```

### Viewing Migration History

```bash
alembic history --verbose
```

### Creating New Migrations

To create a new migration (auto-generate based on model changes):
```bash
alembic revision --autogenerate -m "description of changes"
```

To create a blank migration (for manual changes):
```bash
alembic revision -m "description of changes"
```

## Initial Migration

The `001_initial_schema.py` migration creates the following tables:
- **specialist**: Doctor/specialist information
- **schedule**: Working schedules for specialists
- **day_off**: Days off for specialists
- **booking**: Appointment bookings
- **user_session**: User session tracking for conversation state
- **admin_log**: Administrative action logs

## Database Support

The configuration works with:
- **PostgreSQL**: Production database with connection pooling
- **SQLite**: Development/testing database with single-thread support

## Important Notes

- All models must be imported in `env.py` for autogenerate to work correctly
- The `Base.metadata` from `data/database.py` is used as the target metadata
- Both offline (SQL script generation) and online (direct DB connection) modes are supported
