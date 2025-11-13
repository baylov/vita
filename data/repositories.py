"""Repository layer for SQLAlchemy ORM data persistence."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from data.database import SessionLocal
from data.models import AdminLog, Booking, DayOff, Schedule, Specialist, UserSession

logger = logging.getLogger(__name__)


class SpecialistRepository:
    """Repository for specialist management with SQLAlchemy."""

    def get_all(self) -> List[Specialist]:
        """Return all specialists or an empty list on error."""
        session = SessionLocal()
        try:
            result = session.execute(select(Specialist))
            specialists = result.scalars().all()
            return list(specialists)
        except SQLAlchemyError:
            logger.exception("Failed to get all specialists")
            return []
        finally:
            session.close()

    def get_by_id(self, id: int) -> Optional[Specialist]:
        """Return specialist by primary key or None if not found."""
        session = SessionLocal()
        try:
            result = session.execute(select(Specialist).where(Specialist.id == id))
            return result.scalar_one_or_none()
        except SQLAlchemyError:
            logger.exception("Failed to get specialist by id %s", id)
            return None
        finally:
            session.close()

    def get_by_specialty(self, specialty: str) -> List[Specialist]:
        """Return specialists filtered by specialty or an empty list on error."""
        session = SessionLocal()
        try:
            result = session.execute(
                select(Specialist).where(Specialist.specialty == specialty)
            )
            specialists = result.scalars().all()
            return list(specialists)
        except SQLAlchemyError:
            logger.exception("Failed to get specialists by specialty %s", specialty)
            return []
        finally:
            session.close()

    def get_active(self) -> List[Specialist]:
        """Return active specialists or an empty list on error."""
        session = SessionLocal()
        try:
            result = session.execute(select(Specialist).where(Specialist.is_active.is_(True)))
            specialists = result.scalars().all()
            return list(specialists)
        except SQLAlchemyError:
            logger.exception("Failed to get active specialists")
            return []
        finally:
            session.close()

    def create(
        self,
        name: str,
        specialty: str,
        telegram_id: Optional[str] = None,
        whatsapp: Optional[str] = None,
        instagram: Optional[str] = None,
    ) -> Optional[Specialist]:
        """Create specialist and return instance or None on error."""
        session = SessionLocal()
        try:
            specialist = Specialist(
                name=name,
                specialty=specialty,
                telegram_id=telegram_id,
                whatsapp=whatsapp,
                instagram=instagram,
            )
            session.add(specialist)
            session.commit()
            session.refresh(specialist)
            logger.info(
                "Created specialist %s (ID: %s)",
                specialist.name,
                specialist.id,
            )
            return specialist
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to create specialist %s", name)
            return None
        finally:
            session.close()

    def update(self, id: int, **kwargs) -> Optional[Specialist]:
        """Update specialist fields and return instance or None on error."""
        session = SessionLocal()
        try:
            result = session.execute(select(Specialist).where(Specialist.id == id))
            specialist = result.scalar_one_or_none()

            if specialist is None:
                logger.warning("Specialist with id %s not found for update", id)
                return None

            for key, value in kwargs.items():
                if hasattr(specialist, key):
                    setattr(specialist, key, value)

            specialist.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(specialist)
            logger.info("Updated specialist %s (ID: %s)", specialist.name, specialist.id)
            return specialist
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to update specialist %s", id)
            return None
        finally:
            session.close()

    def delete(self, id: int) -> bool:
        """Delete specialist by id and return status."""
        session = SessionLocal()
        try:
            result = session.execute(select(Specialist).where(Specialist.id == id))
            specialist = result.scalar_one_or_none()

            if specialist is None:
                logger.warning("Specialist with id %s not found for deletion", id)
                return False

            session.delete(specialist)
            session.commit()
            logger.info("Deleted specialist %s (ID: %s)", specialist.name, specialist.id)
            return True
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to delete specialist %s", id)
            return False
        finally:
            session.close()


class ScheduleRepository:
    """Repository for schedule management with SQLAlchemy."""

    def get_by_specialist(self, specialist_id: int) -> List[Schedule]:
        """Return schedules for specialist or an empty list on error."""
        session = SessionLocal()
        try:
            result = session.execute(
                select(Schedule).where(Schedule.specialist_id == specialist_id)
            )
            schedules = result.scalars().all()
            return list(schedules)
        except SQLAlchemyError:
            logger.exception(
                "Failed to get schedules for specialist %s",
                specialist_id,
            )
            return []
        finally:
            session.close()

    def get_by_day(self, day_of_week: str) -> List[Schedule]:
        """Return schedules for day of week or an empty list on error."""
        session = SessionLocal()
        try:
            result = session.execute(
                select(Schedule).where(Schedule.day_of_week == day_of_week)
            )
            schedules = result.scalars().all()
            return list(schedules)
        except SQLAlchemyError:
            logger.exception("Failed to get schedules for day %s", day_of_week)
            return []
        finally:
            session.close()

    def create(
        self,
        specialist_id: int,
        day_of_week: str,
        start_time,
        end_time,
        duration: int,
        max_patients: Optional[int] = None,
    ) -> Optional[Schedule]:
        """Create schedule and return instance or None on error."""
        session = SessionLocal()
        try:
            schedule = Schedule(
                specialist_id=specialist_id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
                appointment_duration=duration,
                max_patients=max_patients,
            )
            session.add(schedule)
            session.commit()
            session.refresh(schedule)
            logger.info(
                "Created schedule for specialist %s on %s (ID: %s)",
                specialist_id,
                day_of_week,
                schedule.id,
            )
            return schedule
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to create schedule for specialist %s", specialist_id)
            return None
        finally:
            session.close()

    def update(self, id: int, **kwargs) -> Optional[Schedule]:
        """Update schedule fields and return instance or None on error."""
        session = SessionLocal()
        try:
            result = session.execute(select(Schedule).where(Schedule.id == id))
            schedule = result.scalar_one_or_none()

            if schedule is None:
                logger.warning("Schedule with id %s not found for update", id)
                return None

            for key, value in kwargs.items():
                if hasattr(schedule, key):
                    setattr(schedule, key, value)

            schedule.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(schedule)
            logger.info("Updated schedule (ID: %s)", schedule.id)
            return schedule
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to update schedule %s", id)
            return None
        finally:
            session.close()

    def delete(self, id: int) -> bool:
        """Delete schedule by id and return status."""
        session = SessionLocal()
        try:
            result = session.execute(select(Schedule).where(Schedule.id == id))
            schedule = result.scalar_one_or_none()

            if schedule is None:
                logger.warning("Schedule with id %s not found for deletion", id)
                return False

            session.delete(schedule)
            session.commit()
            logger.info("Deleted schedule (ID: %s)", schedule.id)
            return True
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to delete schedule %s", id)
            return False
        finally:
            session.close()


class BookingRepository:
    """Repository for booking management with SQLAlchemy."""

    def create(
        self,
        specialist_id: int,
        user_name: str,
        phone: str,
        booking_date,
        booking_time,
        problem_summary: Optional[str] = None,
    ) -> Optional[Booking]:
        """Create booking and return instance or None on error."""
        session = SessionLocal()
        try:
            booking = Booking(
                specialist_id=specialist_id,
                user_name=user_name,
                phone=phone,
                booking_date=booking_date,
                booking_time=booking_time,
                problem_summary=problem_summary,
            )
            session.add(booking)
            session.commit()
            session.refresh(booking)
            logger.info(
                "Created booking for %s with specialist %s (ID: %s)",
                user_name,
                specialist_id,
                booking.id,
            )
            return booking
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to create booking for %s", user_name)
            return None
        finally:
            session.close()

    def get_by_specialist(
        self, specialist_id: int, date=None
    ) -> List[Booking]:
        """Return bookings for specialist, optionally filtered by date or empty list on error."""
        session = SessionLocal()
        try:
            query = select(Booking).where(Booking.specialist_id == specialist_id)
            if date is not None:
                query = query.where(Booking.booking_date == date)
            result = session.execute(query)
            bookings = result.scalars().all()
            return list(bookings)
        except SQLAlchemyError:
            logger.exception("Failed to get bookings for specialist %s", specialist_id)
            return []
        finally:
            session.close()

    def get_by_date(self, date) -> List[Booking]:
        """Return bookings for specific date or empty list on error."""
        session = SessionLocal()
        try:
            result = session.execute(
                select(Booking).where(Booking.booking_date == date)
            )
            bookings = result.scalars().all()
            return list(bookings)
        except SQLAlchemyError:
            logger.exception("Failed to get bookings for date %s", date)
            return []
        finally:
            session.close()

    def get_by_id(self, id: int) -> Optional[Booking]:
        """Return booking by primary key or None if not found."""
        session = SessionLocal()
        try:
            result = session.execute(select(Booking).where(Booking.id == id))
            return result.scalar_one_or_none()
        except SQLAlchemyError:
            logger.exception("Failed to get booking by id %s", id)
            return None
        finally:
            session.close()

    def update_status(self, id: int, status: str) -> Optional[Booking]:
        """Update booking status and return instance or None on error."""
        session = SessionLocal()
        try:
            result = session.execute(select(Booking).where(Booking.id == id))
            booking = result.scalar_one_or_none()

            if booking is None:
                logger.warning("Booking with id %s not found for status update", id)
                return None

            booking.status = status
            booking.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(booking)
            logger.info("Updated booking status (ID: %s) to %s", booking.id, status)
            return booking
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to update booking status %s", id)
            return None
        finally:
            session.close()

    def check_availability(
        self, specialist_id: int, booking_date, booking_time
    ) -> bool:
        """Check if specialist is available at given date and time."""
        session = SessionLocal()
        try:
            result = session.execute(
                select(Booking).where(
                    Booking.specialist_id == specialist_id,
                    Booking.booking_date == booking_date,
                    Booking.booking_time == booking_time,
                    Booking.status.in_(["pending", "confirmed"]),
                )
            )
            existing_booking = result.scalar_one_or_none()
            return existing_booking is None
        except SQLAlchemyError:
            logger.exception(
                "Failed to check availability for specialist %s", specialist_id
            )
            return False
        finally:
            session.close()


class DayOffRepository:
    """Repository for day off management with SQLAlchemy."""

    def get_by_specialist(self, specialist_id: int) -> List[DayOff]:
        """Return day offs for specialist or empty list on error."""
        session = SessionLocal()
        try:
            result = session.execute(
                select(DayOff).where(DayOff.specialist_id == specialist_id)
            )
            day_offs = result.scalars().all()
            return list(day_offs)
        except SQLAlchemyError:
            logger.exception("Failed to get day offs for specialist %s", specialist_id)
            return []
        finally:
            session.close()

    def get_by_date(self, date) -> List[DayOff]:
        """Return day offs for specific date or empty list on error."""
        session = SessionLocal()
        try:
            result = session.execute(select(DayOff).where(DayOff.date == date))
            day_offs = result.scalars().all()
            return list(day_offs)
        except SQLAlchemyError:
            logger.exception("Failed to get day offs for date %s", date)
            return []
        finally:
            session.close()

    def create(
        self, specialist_id: int, date, reason: Optional[str] = None
    ) -> Optional[DayOff]:
        """Create day off and return instance or None on error."""
        session = SessionLocal()
        try:
            day_off = DayOff(
                specialist_id=specialist_id,
                date=date,
                reason=reason,
            )
            session.add(day_off)
            session.commit()
            session.refresh(day_off)
            logger.info(
                "Created day off for specialist %s on %s (ID: %s)",
                specialist_id,
                date,
                day_off.id,
            )
            return day_off
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to create day off for specialist %s", specialist_id)
            return None
        finally:
            session.close()

    def delete(self, id: int) -> bool:
        """Delete day off by id and return status."""
        session = SessionLocal()
        try:
            result = session.execute(select(DayOff).where(DayOff.id == id))
            day_off = result.scalar_one_or_none()

            if day_off is None:
                logger.warning("Day off with id %s not found for deletion", id)
                return False

            session.delete(day_off)
            session.commit()
            logger.info("Deleted day off (ID: %s)", day_off.id)
            return True
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to delete day off %s", id)
            return False
        finally:
            session.close()


class UserSessionRepository:
    """Repository for user session management with SQLAlchemy."""

    def get_by_user_id(self, user_id: str) -> Optional[UserSession]:
        """Return user session by user_id or None if not found."""
        session = SessionLocal()
        try:
            result = session.execute(
                select(UserSession).where(UserSession.user_id == user_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError:
            logger.exception("Failed to get user session for user %s", user_id)
            return None
        finally:
            session.close()

    def create(
        self, user_id: str, platform: str, language: str = "ru"
    ) -> Optional[UserSession]:
        """Create user session and return instance or None on error."""
        session = SessionLocal()
        try:
            user_session = UserSession(
                user_id=user_id,
                platform=platform,
                language=language,
            )
            session.add(user_session)
            session.commit()
            session.refresh(user_session)
            logger.info(
                "Created user session for %s on %s (ID: %s)",
                user_id,
                platform,
                user_session.id,
            )
            return user_session
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to create user session for %s", user_id)
            return None
        finally:
            session.close()

    def update(
        self, user_id: str, state: Optional[str] = None, context_data: Optional[str] = None
    ) -> Optional[UserSession]:
        """Update user session state and/or context and return instance or None on error."""
        session = SessionLocal()
        try:
            result = session.execute(
                select(UserSession).where(UserSession.user_id == user_id)
            )
            user_session = result.scalar_one_or_none()

            if user_session is None:
                logger.warning("User session for %s not found for update", user_id)
                return None

            if state is not None:
                user_session.current_state = state
            if context_data is not None:
                user_session.context_data = context_data

            user_session.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(user_session)
            logger.info("Updated user session for %s", user_id)
            return user_session
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to update user session for %s", user_id)
            return None
        finally:
            session.close()

    def clear(self, user_id: str) -> bool:
        """Clear user session state and context by user_id and return status."""
        session = SessionLocal()
        try:
            result = session.execute(
                select(UserSession).where(UserSession.user_id == user_id)
            )
            user_session = result.scalar_one_or_none()

            if user_session is None:
                logger.warning("User session for %s not found for clearing", user_id)
                return False

            user_session.current_state = None
            user_session.context_data = None
            user_session.updated_at = datetime.now(timezone.utc)
            session.commit()
            logger.info("Cleared user session for %s", user_id)
            return True
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to clear user session for %s", user_id)
            return False
        finally:
            session.close()

    def get_all_by_platform(self, platform: str) -> List[UserSession]:
        """Return all user sessions for platform or empty list on error."""
        session = SessionLocal()
        try:
            result = session.execute(
                select(UserSession).where(UserSession.platform == platform)
            )
            user_sessions = result.scalars().all()
            return list(user_sessions)
        except SQLAlchemyError:
            logger.exception("Failed to get user sessions for platform %s", platform)
            return []
        finally:
            session.close()


class AdminLogRepository:
    """Repository for admin log management with SQLAlchemy."""

    def log_action(
        self, admin_id: str, action: str, details: Optional[str] = None
    ) -> Optional[AdminLog]:
        """Log admin action and return instance or None on error."""
        session = SessionLocal()
        try:
            admin_log = AdminLog(
                admin_id=admin_id,
                action=action,
                details=details,
            )
            session.add(admin_log)
            session.commit()
            session.refresh(admin_log)
            logger.info(
                "Logged admin action %s by %s (ID: %s)",
                action,
                admin_id,
                admin_log.id,
            )
            return admin_log
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to log admin action %s by %s", action, admin_id)
            return None
        finally:
            session.close()

    def get_logs(self, limit: int = 100, offset: int = 0) -> List[AdminLog]:
        """Return admin logs with pagination or empty list on error."""
        session = SessionLocal()
        try:
            result = session.execute(
                select(AdminLog).order_by(AdminLog.created_at.desc()).limit(limit).offset(offset)
            )
            logs = result.scalars().all()
            return list(logs)
        except SQLAlchemyError:
            logger.exception("Failed to get admin logs")
            return []
        finally:
            session.close()

    def get_by_admin(self, admin_id: str, limit: int = 50) -> List[AdminLog]:
        """Return admin logs for specific admin or empty list on error."""
        session = SessionLocal()
        try:
            result = session.execute(
                select(AdminLog)
                .where(AdminLog.admin_id == admin_id)
                .order_by(AdminLog.created_at.desc())
                .limit(limit)
            )
            logs = result.scalars().all()
            return list(logs)
        except SQLAlchemyError:
            logger.exception("Failed to get admin logs for admin %s", admin_id)
            return []
        finally:
            session.close()