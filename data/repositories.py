from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime, date, time
from .models import Specialist, Schedule, DayOff, Booking, UserSession, AdminLog


class SpecialistRepository:
    """Repository for Specialist CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, specialist_data: Dict[str, Any]) -> Specialist:
        """Create a new specialist."""
        specialist = Specialist(**specialist_data)
        self.db.add(specialist)
        self.db.commit()
        self.db.refresh(specialist)
        return specialist
    
    def get_by_id(self, specialist_id: int) -> Optional[Specialist]:
        """Get specialist by ID."""
        return self.db.query(Specialist).filter(Specialist.id == specialist_id).first()
    
    def get_by_email(self, email: str) -> Optional[Specialist]:
        """Get specialist by email."""
        return self.db.query(Specialist).filter(Specialist.email == email).first()
    
    def get_all(self, active_only: bool = True) -> List[Specialist]:
        """Get all specialists, optionally filtering by active status."""
        query = self.db.query(Specialist)
        if active_only:
            query = query.filter(Specialist.is_active == True)
        return query.all()
    
    def update(self, specialist_id: int, update_data: Dict[str, Any]) -> Optional[Specialist]:
        """Update specialist by ID."""
        specialist = self.get_by_id(specialist_id)
        if specialist:
            for key, value in update_data.items():
                setattr(specialist, key, value)
            self.db.commit()
            self.db.refresh(specialist)
        return specialist
    
    def delete(self, specialist_id: int) -> bool:
        """Delete specialist by ID (soft delete by setting is_active=False)."""
        specialist = self.get_by_id(specialist_id)
        if specialist:
            specialist.is_active = False
            self.db.commit()
            return True
        return False
    
    def search(self, query: str, active_only: bool = True) -> List[Specialist]:
        """Search specialists by name, specialization, or languages."""
        db_query = self.db.query(Specialist)
        if active_only:
            db_query = db_query.filter(Specialist.is_active == True)
        
        search_filter = or_(
            Specialist.name.ilike(f"%{query}%"),
            Specialist.specialization.ilike(f"%{query}%"),
            Specialist.languages.ilike(f"%{query}%")
        )
        return db_query.filter(search_filter).all()


class ScheduleRepository:
    """Repository for Schedule CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, schedule_data: Dict[str, Any]) -> Schedule:
        """Create a new schedule."""
        schedule = Schedule(**schedule_data)
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule
    
    def get_by_id(self, schedule_id: int) -> Optional[Schedule]:
        """Get schedule by ID."""
        return self.db.query(Schedule).filter(Schedule.id == schedule_id).first()
    
    def get_by_specialist(self, specialist_id: int, active_only: bool = True) -> List[Schedule]:
        """Get all schedules for a specialist."""
        query = self.db.query(Schedule).filter(Schedule.specialist_id == specialist_id)
        if active_only:
            query = query.filter(Schedule.is_active == True)
        return query.order_by(Schedule.day_of_week, Schedule.start_time).all()
    
    def get_by_day(self, specialist_id: int, day_of_week: int) -> List[Schedule]:
        """Get schedules for a specialist on a specific day."""
        return self.db.query(Schedule).filter(
            and_(
                Schedule.specialist_id == specialist_id,
                Schedule.day_of_week == day_of_week,
                Schedule.is_active == True
            )
        ).order_by(Schedule.start_time).all()
    
    def update(self, schedule_id: int, update_data: Dict[str, Any]) -> Optional[Schedule]:
        """Update schedule by ID."""
        schedule = self.get_by_id(schedule_id)
        if schedule:
            for key, value in update_data.items():
                setattr(schedule, key, value)
            self.db.commit()
            self.db.refresh(schedule)
        return schedule
    
    def delete(self, schedule_id: int) -> bool:
        """Delete schedule by ID (soft delete)."""
        schedule = self.get_by_id(schedule_id)
        if schedule:
            schedule.is_active = False
            self.db.commit()
            return True
        return False


class DayOffRepository:
    """Repository for DayOff CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, day_off_data: Dict[str, Any]) -> DayOff:
        """Create a new day off."""
        day_off = DayOff(**day_off_data)
        self.db.add(day_off)
        self.db.commit()
        self.db.refresh(day_off)
        return day_off
    
    def get_by_id(self, day_off_id: int) -> Optional[DayOff]:
        """Get day off by ID."""
        return self.db.query(DayOff).filter(DayOff.id == day_off_id).first()
    
    def get_by_specialist(self, specialist_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[DayOff]:
        """Get all day offs for a specialist within a date range."""
        query = self.db.query(DayOff).filter(DayOff.specialist_id == specialist_id, DayOff.is_active == True)
        
        if start_date:
            query = query.filter(DayOff.date >= start_date)
        if end_date:
            query = query.filter(DayOff.date <= end_date)
        
        return query.order_by(DayOff.date).all()
    
    def is_day_off(self, specialist_id: int, check_date: date) -> bool:
        """Check if a specialist has a day off on a specific date."""
        return self.db.query(DayOff).filter(
            and_(
                DayOff.specialist_id == specialist_id,
                DayOff.date == check_date,
                DayOff.is_active == True
            )
        ).first() is not None
    
    def update(self, day_off_id: int, update_data: Dict[str, Any]) -> Optional[DayOff]:
        """Update day off by ID."""
        day_off = self.get_by_id(day_off_id)
        if day_off:
            for key, value in update_data.items():
                setattr(day_off, key, value)
            self.db.commit()
            self.db.refresh(day_off)
        return day_off
    
    def delete(self, day_off_id: int) -> bool:
        """Delete day off by ID (soft delete)."""
        day_off = self.get_by_id(day_off_id)
        if day_off:
            day_off.is_active = False
            self.db.commit()
            return True
        return False


class BookingRepository:
    """Repository for Booking CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, booking_data: Dict[str, Any]) -> Booking:
        """Create a new booking."""
        booking = Booking(**booking_data)
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking
    
    def get_by_id(self, booking_id: int) -> Optional[Booking]:
        """Get booking by ID."""
        return self.db.query(Booking).filter(Booking.id == booking_id).first()
    
    def get_by_specialist(self, specialist_id: int, status: Optional[str] = None) -> List[Booking]:
        """Get all bookings for a specialist, optionally filtered by status."""
        query = self.db.query(Booking).filter(Booking.specialist_id == specialist_id)
        if status:
            query = query.filter(Booking.status == status)
        return query.order_by(Booking.booking_date, Booking.start_time).all()
    
    def get_by_date_range(self, specialist_id: int, start_date: date, end_date: date, status: Optional[str] = None) -> List[Booking]:
        """Get bookings for a specialist within a date range."""
        query = self.db.query(Booking).filter(
            and_(
                Booking.specialist_id == specialist_id,
                Booking.booking_date >= start_date,
                Booking.booking_date <= end_date
            )
        )
        if status:
            query = query.filter(Booking.status == status)
        return query.order_by(Booking.booking_date, Booking.start_time).all()
    
    def get_conflicting_bookings(self, specialist_id: int, booking_date: date, start_time: time, end_time: time, exclude_booking_id: Optional[int] = None) -> List[Booking]:
        """Get bookings that conflict with the given time slot."""
        query = self.db.query(Booking).filter(
            and_(
                Booking.specialist_id == specialist_id,
                Booking.booking_date == booking_date,
                Booking.status.in_(["pending", "confirmed"]),
                or_(
                    and_(Booking.start_time <= start_time, Booking.end_time > start_time),
                    and_(Booking.start_time < end_time, Booking.end_time >= end_time),
                    and_(Booking.start_time >= start_time, Booking.end_time <= end_time)
                )
            )
        )
        
        if exclude_booking_id:
            query = query.filter(Booking.id != exclude_booking_id)
        
        return query.all()
    
    def update(self, booking_id: int, update_data: Dict[str, Any]) -> Optional[Booking]:
        """Update booking by ID."""
        booking = self.get_by_id(booking_id)
        if booking:
            for key, value in update_data.items():
                setattr(booking, key, value)
            self.db.commit()
            self.db.refresh(booking)
        return booking
    
    def cancel(self, booking_id: int, reason: Optional[str] = None) -> Optional[Booking]:
        """Cancel a booking."""
        booking = self.get_by_id(booking_id)
        if booking:
            booking.status = "cancelled"
            if reason:
                booking.notes = f"{booking.notes or ''}\n\nCancellation reason: {reason}".strip()
            self.db.commit()
            self.db.refresh(booking)
        return booking


class UserSessionRepository:
    """Repository for UserSession CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, session_data: Dict[str, Any]) -> UserSession:
        """Create a new user session."""
        session = UserSession(**session_data)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def get_by_id(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID."""
        return self.db.query(UserSession).filter(UserSession.session_id == session_id).first()
    
    def get_active_sessions(self) -> List[UserSession]:
        """Get all active sessions."""
        return self.db.query(UserSession).filter(
            and_(
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            )
        ).all()
    
    def update(self, session_id: str, update_data: Dict[str, Any]) -> Optional[UserSession]:
        """Update session by ID."""
        session = self.get_by_id(session_id)
        if session:
            for key, value in update_data.items():
                setattr(session, key, value)
            self.db.commit()
            self.db.refresh(session)
        return session
    
    def deactivate(self, session_id: str) -> bool:
        """Deactivate a session."""
        session = self.get_by_id(session_id)
        if session:
            session.is_active = False
            self.db.commit()
            return True
        return False
    
    def cleanup_expired_sessions(self) -> int:
        """Deactivate all expired sessions and return count."""
        expired_count = self.db.query(UserSession).filter(
            and_(
                UserSession.is_active == True,
                UserSession.expires_at <= datetime.utcnow()
            )
        ).update({"is_active": False})
        
        self.db.commit()
        return expired_count


class AdminLogRepository:
    """Repository for AdminLog CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, log_data: Dict[str, Any]) -> AdminLog:
        """Create a new admin log entry."""
        log = AdminLog(**log_data)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
    
    def get_by_admin(self, admin_id: str, limit: int = 100) -> List[AdminLog]:
        """Get logs for a specific admin."""
        return self.db.query(AdminLog).filter(
            AdminLog.admin_id == admin_id
        ).order_by(desc(AdminLog.created_at)).limit(limit).all()
    
    def get_by_resource(self, resource_type: str, resource_id: Optional[int] = None, limit: int = 100) -> List[AdminLog]:
        """Get logs for a specific resource type and optionally ID."""
        query = self.db.query(AdminLog).filter(AdminLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(AdminLog.resource_id == resource_id)
        return query.order_by(desc(AdminLog.created_at)).limit(limit).all()
    
    def get_recent_logs(self, limit: int = 100) -> List[AdminLog]:
        """Get recent admin logs."""
        return self.db.query(AdminLog).order_by(desc(AdminLog.created_at)).limit(limit).all()