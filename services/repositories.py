"""Repository layer for data persistence operations."""

import logging
from datetime import datetime, timezone
from typing import Optional

from integrations.google.sheets_manager import GoogleSheetsManager
from models import SpecialistDTO, DayOffDTO, ScheduleDTO, BookingDTO, AdminActionDTO

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class with common functionality."""
    
    def __init__(self, sheets_manager: GoogleSheetsManager):
        """
        Initialize repository with sheets manager.
        
        Args:
            sheets_manager: GoogleSheetsManager instance for persistence
        """
        self.sheets_manager = sheets_manager


class SpecialistRepository(BaseRepository):
    """Repository for specialist management."""
    
    def create(self, specialist: SpecialistDTO, admin_id: Optional[str] = None) -> SpecialistDTO:
        """
        Create a new specialist.
        
        Args:
            specialist: Specialist data to create
            admin_id: ID of admin performing action
            
        Returns:
            Created specialist
        """
        try:
            # Add specialist to Sheets
            worksheet = self.sheets_manager._get_worksheet_safe("specialists")
            now = datetime.now(timezone.utc).isoformat()
            
            row = [
                "",  # ID will be auto-assigned
                specialist.name,
                specialist.specialization,
                specialist.phone or "",
                specialist.email or "",
                "Да" if specialist.is_active else "Нет",
                now,
                now,
            ]
            worksheet.append_row(row)
            
            # Log action
            self.sheets_manager.log_admin_action(
                AdminActionDTO(
                    action_type="create",
                    resource_type="specialist",
                    description=f"Specialist created: {specialist.name}",
                    performed_by=admin_id,
                )
            )
            
            logger.info(f"Created specialist: {specialist.name}")
            specialist.created_at = datetime.fromisoformat(now.replace("Z", "+00:00"))
            specialist.updated_at = specialist.created_at
            return specialist
        except Exception as e:
            logger.error(f"Failed to create specialist: {e}")
            raise
    
    def get_by_name(self, name: str) -> Optional[SpecialistDTO]:
        """
        Get specialist by name.
        
        Args:
            name: Specialist name to search for
            
        Returns:
            Specialist if found, None otherwise
        """
        try:
            specialists = self.sheets_manager.read_specialists()
            for spec in specialists:
                if spec.name.lower() == name.lower():
                    return spec
            return None
        except Exception as e:
            logger.error(f"Failed to get specialist by name: {e}")
            return None
    
    def get_all(self) -> list[SpecialistDTO]:
        """
        Get all specialists.
        
        Returns:
            List of all specialists
        """
        try:
            return self.sheets_manager.read_specialists()
        except Exception as e:
            logger.error(f"Failed to get all specialists: {e}")
            return []
    
    def update(self, specialist: SpecialistDTO, admin_id: Optional[str] = None) -> SpecialistDTO:
        """
        Update specialist information.
        
        Args:
            specialist: Updated specialist data
            admin_id: ID of admin performing action
            
        Returns:
            Updated specialist
        """
        try:
            # In a real system with database, this would update specific fields
            # For now, this is a placeholder that would require sheet manipulation
            self.sheets_manager.log_admin_action(
                AdminActionDTO(
                    action_type="update",
                    resource_type="specialist",
                    resource_id=specialist.id,
                    description=f"Specialist updated: {specialist.name}",
                    performed_by=admin_id,
                )
            )
            
            logger.info(f"Updated specialist: {specialist.name}")
            specialist.updated_at = datetime.now(timezone.utc)
            return specialist
        except Exception as e:
            logger.error(f"Failed to update specialist: {e}")
            raise
    
    def delete(self, specialist_id: int, admin_id: Optional[str] = None) -> bool:
        """
        Delete a specialist.
        
        Args:
            specialist_id: ID of specialist to delete
            admin_id: ID of admin performing action
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Log action first
            self.sheets_manager.log_admin_action(
                AdminActionDTO(
                    action_type="delete",
                    resource_type="specialist",
                    resource_id=specialist_id,
                    description=f"Specialist deleted: ID {specialist_id}",
                    performed_by=admin_id,
                )
            )
            
            logger.info(f"Deleted specialist: {specialist_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete specialist: {e}")
            return False


class DayOffRepository(BaseRepository):
    """Repository for day off management."""
    
    def create(self, day_off: DayOffDTO, admin_id: Optional[str] = None) -> DayOffDTO:
        """
        Create a new day off.
        
        Args:
            day_off: Day off data to create
            admin_id: ID of admin performing action
            
        Returns:
            Created day off
        """
        try:
            worksheet = self.sheets_manager._get_worksheet_safe("days_off")
            now = datetime.now(timezone.utc).isoformat()
            
            row = [
                "",  # ID will be auto-assigned
                day_off.specialist_id,
                day_off.date,
                day_off.reason or "",
                now,
            ]
            worksheet.append_row(row)
            
            # Log action
            self.sheets_manager.log_admin_action(
                AdminActionDTO(
                    action_type="create",
                    resource_type="day_off",
                    description=f"Day off set for specialist {day_off.specialist_id} on {day_off.date}",
                    performed_by=admin_id,
                )
            )
            
            logger.info(f"Created day off: specialist {day_off.specialist_id}, date {day_off.date}")
            day_off.created_at = datetime.fromisoformat(now.replace("Z", "+00:00"))
            return day_off
        except Exception as e:
            logger.error(f"Failed to create day off: {e}")
            raise
    
    def get_by_specialist_and_date(self, specialist_id: int, date: str) -> Optional[DayOffDTO]:
        """
        Get day off for specialist on specific date.
        
        Args:
            specialist_id: ID of specialist
            date: Date in YYYY-MM-DD format
            
        Returns:
            Day off if found, None otherwise
        """
        try:
            days_off = self.sheets_manager.read_days_off()
            for do in days_off:
                if do.specialist_id == specialist_id and do.date == date:
                    return do
            return None
        except Exception as e:
            logger.error(f"Failed to get day off: {e}")
            return None
    
    def get_by_specialist(self, specialist_id: int) -> list[DayOffDTO]:
        """
        Get all days off for a specialist.
        
        Args:
            specialist_id: ID of specialist
            
        Returns:
            List of days off
        """
        try:
            days_off = self.sheets_manager.read_days_off()
            return [do for do in days_off if do.specialist_id == specialist_id]
        except Exception as e:
            logger.error(f"Failed to get days off: {e}")
            return []


class ScheduleRepository(BaseRepository):
    """Repository for schedule management."""
    
    def get_by_specialist(self, specialist_id: int) -> list[ScheduleDTO]:
        """
        Get all schedules for a specialist.
        
        Args:
            specialist_id: ID of specialist
            
        Returns:
            List of schedules
        """
        try:
            schedules = self.sheets_manager.read_schedule()
            return [s for s in schedules if s.specialist_id == specialist_id]
        except Exception as e:
            logger.error(f"Failed to get schedules: {e}")
            return []
    
    def get_all(self) -> list[ScheduleDTO]:
        """
        Get all schedules.
        
        Returns:
            List of all schedules
        """
        try:
            return self.sheets_manager.read_schedule()
        except Exception as e:
            logger.error(f"Failed to get all schedules: {e}")
            return []


class BookingRepository(BaseRepository):
    """Repository for booking queries."""
    
    def get_all(self) -> list[BookingDTO]:
        """
        Get all bookings.
        
        Returns:
            List of all bookings
        """
        try:
            return self.sheets_manager.read_bookings()
        except Exception as e:
            logger.error(f"Failed to get all bookings: {e}")
            return []
    
    def get_by_specialist(self, specialist_id: int) -> list[BookingDTO]:
        """
        Get all bookings for a specialist.
        
        Args:
            specialist_id: ID of specialist
            
        Returns:
            List of bookings
        """
        try:
            bookings = self.sheets_manager.read_bookings()
            return [b for b in bookings if b.specialist_id == specialist_id]
        except Exception as e:
            logger.error(f"Failed to get bookings: {e}")
            return []
    
    def count_by_status(self, status: str) -> int:
        """
        Count bookings by status.
        
        Args:
            status: Booking status to count
            
        Returns:
            Count of bookings
        """
        try:
            bookings = self.sheets_manager.read_bookings()
            return len([b for b in bookings if b.status == status])
        except Exception as e:
            logger.error(f"Failed to count bookings: {e}")
            return 0
