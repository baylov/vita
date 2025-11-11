from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Date, Time
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func
from sqlalchemy import UniqueConstraint, Index
from datetime import datetime, date, time
from typing import Optional, List
from .database import Base


class Specialist(Base):
    __tablename__ = "specialists"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    specialization = Column(String(255), nullable=False)
    bio = Column(Text, nullable=True)
    languages = Column(String(255), nullable=False)  # Comma-separated list of languages
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    schedules = relationship("Schedule", back_populates="specialist", cascade="all, delete-orphan")
    day_offs = relationship("DayOff", back_populates="specialist", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="specialist", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Specialist(id={self.id}, name='{self.name}', email='{self.email}')>"


class Schedule(Base):
    __tablename__ = "schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    specialist_id = Column(Integer, ForeignKey("specialists.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    specialist = relationship("Specialist", back_populates="schedules")
    
    # Composite unique constraint for specialist and day/time
    __table_args__ = (
        UniqueConstraint('specialist_id', 'day_of_week', 'start_time', 'end_time', name='uq_specialist_schedule'),
        Index('idx_specialist_schedule', 'specialist_id', 'day_of_week'),
    )
    
    def __repr__(self):
        return f"<Schedule(id={self.id}, specialist_id={self.specialist_id}, day_of_week={self.day_of_week})>"


class DayOff(Base):
    __tablename__ = "day_offs"
    
    id = Column(Integer, primary_key=True, index=True)
    specialist_id = Column(Integer, ForeignKey("specialists.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    reason = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    specialist = relationship("Specialist", back_populates="day_offs")
    
    # Unique constraint for specialist and date
    __table_args__ = (
        UniqueConstraint('specialist_id', 'date', name='uq_specialist_day_off'),
        Index('idx_specialist_day_off', 'specialist_id', 'date'),
    )
    
    def __repr__(self):
        return f"<DayOff(id={self.id}, specialist_id={self.specialist_id}, date='{self.date}')>"


class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    specialist_id = Column(Integer, ForeignKey("specialists.id", ondelete="CASCADE"), nullable=False)
    client_name = Column(String(255), nullable=False)
    client_email = Column(String(255), nullable=False)
    client_phone = Column(String(50), nullable=True)
    booking_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    status = Column(String(50), default="pending", nullable=False)  # pending, confirmed, cancelled, completed
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    specialist = relationship("Specialist", back_populates="bookings")
    
    # Composite unique constraint for specialist, date, and time
    __table_args__ = (
        UniqueConstraint('specialist_id', 'booking_date', 'start_time', 'end_time', name='uq_specialist_booking'),
        Index('idx_specialist_booking_date', 'specialist_id', 'booking_date'),
        Index('idx_booking_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Booking(id={self.id}, specialist_id={self.specialist_id}, date='{self.booking_date}', status='{self.status}')>"


class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    client_name = Column(String(255), nullable=True)
    client_email = Column(String(255), nullable=True)
    client_phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Index for session cleanup
    __table_args__ = (
        Index('idx_session_expires', 'expires_at'),
        Index('idx_session_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, session_id='{self.session_id}', is_active={self.is_active})>"


class AdminLog(Base):
    __tablename__ = "admin_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(String(255), nullable=False)  # Admin identifier
    action = Column(String(255), nullable=False)  # Action performed
    resource_type = Column(String(100), nullable=False)  # Type of resource (specialist, booking, etc.)
    resource_id = Column(Integer, nullable=True)  # ID of the resource if applicable
    details = Column(Text, nullable=True)  # Additional details about the action
    ip_address = Column(String(45), nullable=True)  # IP address of the admin
    user_agent = Column(Text, nullable=True)  # User agent string
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes for querying logs
    __table_args__ = (
        Index('idx_admin_action', 'admin_id', 'action'),
        Index('idx_resource_type', 'resource_type'),
        Index('idx_log_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AdminLog(id={self.id}, admin_id='{self.admin_id}', action='{self.action}')>"