"""SQLAlchemy ORM models for VitaPlus bot."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    Date,
    Time,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship

from data.database import Base


class Specialist(Base):
    """Specialist (doctor) model."""

    __tablename__ = "specialist"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    specialty = Column(String(100), nullable=False)
    telegram_id = Column(String(50), unique=True, nullable=True, index=True)
    whatsapp = Column(String(50), unique=True, nullable=True, index=True)
    instagram = Column(String(50), unique=True, nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    schedules = relationship(
        "Schedule",
        back_populates="specialist",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    day_offs = relationship(
        "DayOff",
        back_populates="specialist",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    bookings = relationship(
        "Booking",
        back_populates="specialist",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Specialist(id={self.id}, name={self.name}, specialty={self.specialty})>"


class Schedule(Base):
    """Working schedule for a specialist."""

    __tablename__ = "schedule"

    id = Column(Integer, primary_key=True, index=True)
    specialist_id = Column(
        Integer,
        ForeignKey("specialist.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week = Column(String(10), nullable=False)  # Пн, Вт, Ср, Чт, Пт, Сб, Вс
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    appointment_duration = Column(Integer, nullable=False)  # в минутах
    max_patients = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    specialist = relationship("Specialist", back_populates="schedules")

    def __repr__(self) -> str:
        return f"<Schedule(id={self.id}, specialist_id={self.specialist_id}, day_of_week={self.day_of_week})>"


class DayOff(Base):
    """Day off for a specialist."""

    __tablename__ = "day_off"

    id = Column(Integer, primary_key=True, index=True)
    specialist_id = Column(
        Integer,
        ForeignKey("specialist.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date = Column(Date, nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    specialist = relationship("Specialist", back_populates="day_offs")

    def __repr__(self) -> str:
        return f"<DayOff(id={self.id}, specialist_id={self.specialist_id}, date={self.date})>"


class Booking(Base):
    """Booking (appointment) model."""

    __tablename__ = "booking"

    id = Column(Integer, primary_key=True, index=True)
    specialist_id = Column(
        Integer,
        ForeignKey("specialist.id"),
        nullable=False,
        index=True,
    )
    user_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    booking_date = Column(Date, nullable=False)
    booking_time = Column(Time, nullable=False)
    problem_summary = Column(Text, nullable=True)
    status = Column(
        String(50),
        default="pending",
        nullable=False,
    )  # 'pending', 'confirmed', 'completed', 'cancelled'
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    specialist = relationship("Specialist", back_populates="bookings")

    def __repr__(self) -> str:
        return f"<Booking(id={self.id}, specialist_id={self.specialist_id}, user_name={self.user_name})>"


class UserSession(Base):
    """User session for tracking conversation state."""

    __tablename__ = "user_session"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), unique=True, nullable=False, index=True)
    platform = Column(String(50), nullable=False)  # 'telegram', 'whatsapp', 'instagram'
    language = Column(String(5), default="ru", nullable=False)  # 'ru', 'kz'
    current_state = Column(String(100), nullable=True)  # текущее состояние FSM
    context_data = Column(Text, nullable=True)  # JSON сохранённый контекст
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, platform={self.platform})>"


class AdminLog(Base):
    """Administrative action logs."""

    __tablename__ = "admin_log"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(String(255), nullable=False, index=True)  # Telegram ID админа
    action = Column(String(100), nullable=False)  # 'add_specialist', 'edit_schedule', 'delete_booking' и т.д.
    details = Column(Text, nullable=True)  # JSON с деталями действия
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AdminLog(id={self.id}, admin_id={self.admin_id}, action={self.action})>"
