"""Data models and DTOs for Sheets integration."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SpecialistDTO(BaseModel):
    """Data transfer object for specialist data."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    name: str
    specialization: str
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ScheduleDTO(BaseModel):
    """Data transfer object for schedule data."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    specialist_id: int
    day_of_week: int  # 0-6 for Mon-Sun
    start_time: str  # HH:MM format
    end_time: str  # HH:MM format
    is_available: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BookingDTO(BaseModel):
    """Data transfer object for booking data."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    specialist_id: int
    client_name: str
    booking_datetime: datetime
    duration_minutes: int = 60
    notes: Optional[str] = None
    status: str = "confirmed"  # confirmed, pending, cancelled
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DayOffDTO(BaseModel):
    """Data transfer object for day off data."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    specialist_id: int
    date: str  # YYYY-MM-DD format
    reason: Optional[str] = None
    created_at: Optional[datetime] = None


class AdminActionDTO(BaseModel):
    """Data transfer object for admin action logs."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    action_type: str  # create, update, delete, sync, etc.
    resource_type: str  # specialist, booking, schedule, etc.
    resource_id: Optional[int] = None
    description: str
    performed_by: Optional[str] = None
    created_at: Optional[datetime] = None


class ErrorLogDTO(BaseModel):
    """Data transfer object for error logs."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    error_type: str
    message: str
    context: Optional[str] = None
    traceback: Optional[str] = None
    created_at: Optional[datetime] = None


class SyncState(BaseModel):
    """Represents the state of a sync operation."""

    last_synced: Optional[datetime] = None
    conflicts_detected: int = 0
    items_pushed: int = 0
    items_pulled: int = 0
    errors: list[str] = Field(default_factory=list)
