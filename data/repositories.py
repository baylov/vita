"""Repository layer for SQLAlchemy ORM data persistence."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from data.database import SessionLocal
from data.models import Schedule, Specialist

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