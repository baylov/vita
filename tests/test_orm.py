import pytest
import os
import tempfile
from datetime import datetime, date, time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from data.database import Base, init_db, get_db
from data.models import Specialist, Schedule, DayOff, Booking, UserSession, AdminLog
from data.repositories import (
    SpecialistRepository,
    ScheduleRepository,
    DayOffRepository,
    BookingRepository,
    UserSessionRepository,
    AdminLogRepository,
)


@pytest.fixture(scope="function")
def db_session():
    """Create a temporary in-memory SQLite database for testing."""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp()
    
    # Create engine and session
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create a session
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Cleanup
        os.close(db_fd)
        os.unlink(db_path)


class TestSpecialistModel:
    """Test the Specialist model and repository."""
    
    def test_create_specialist(self, db_session):
        """Test creating a specialist."""
        repo = SpecialistRepository(db_session)
        specialist_data = {
            "name": "Dr. John Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "specialization": "General Practice",
            "bio": "Experienced general practitioner",
            "languages": "English, Spanish"
        }
        
        specialist = repo.create(specialist_data)
        
        assert specialist.id is not None
        assert specialist.name == "Dr. John Doe"
        assert specialist.email == "john.doe@example.com"
        assert specialist.is_active is True
        assert specialist.created_at is not None
    
    def test_get_specialist_by_id(self, db_session):
        """Test retrieving a specialist by ID."""
        repo = SpecialistRepository(db_session)
        
        # Create a specialist first
        specialist_data = {
            "name": "Dr. Jane Smith",
            "email": "jane.smith@example.com",
            "specialization": "Cardiology",
            "languages": "English"
        }
        created = repo.create(specialist_data)
        
        # Retrieve by ID
        retrieved = repo.get_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Dr. Jane Smith"
    
    def test_get_specialist_by_email(self, db_session):
        """Test retrieving a specialist by email."""
        repo = SpecialistRepository(db_session)
        
        specialist_data = {
            "name": "Dr. Bob Johnson",
            "email": "bob.johnson@example.com",
            "specialization": "Dermatology",
            "languages": "English, French"
        }
        repo.create(specialist_data)
        
        retrieved = repo.get_by_email("bob.johnson@example.com")
        
        assert retrieved is not None
        assert retrieved.name == "Dr. Bob Johnson"
        assert retrieved.specialization == "Dermatology"
    
    def test_get_all_specialists(self, db_session):
        """Test retrieving all specialists."""
        repo = SpecialistRepository(db_session)
        
        # Create multiple specialists
        specialists_data = [
            {"name": "Dr. Alice Brown", "email": "alice@example.com", "specialization": "Pediatrics", "languages": "English"},
            {"name": "Dr. Charlie Davis", "email": "charlie@example.com", "specialization": "Neurology", "languages": "English"},
        ]
        
        for data in specialists_data:
            repo.create(data)
        
        all_specialists = repo.get_all()
        assert len(all_specialists) == 2
        
        # Test with inactive specialist
        inactive_data = {"name": "Dr. Inactive", "email": "inactive@example.com", "specialization": "Test", "languages": "English", "is_active": False}
        repo.create(inactive_data)
        
        active_only = repo.get_all(active_only=True)
        assert len(active_only) == 2
        
        all_including_inactive = repo.get_all(active_only=False)
        assert len(all_including_inactive) == 3
    
    def test_update_specialist(self, db_session):
        """Test updating a specialist."""
        repo = SpecialistRepository(db_session)
        
        specialist_data = {
            "name": "Dr. Original Name",
            "email": "original@example.com",
            "specialization": "Original Specialty",
            "languages": "English"
        }
        specialist = repo.create(specialist_data)
        
        # Update the specialist
        updated = repo.update(specialist.id, {
            "name": "Dr. Updated Name",
            "phone": "+9876543210"
        })
        
        assert updated is not None
        assert updated.name == "Dr. Updated Name"
        assert updated.phone == "+9876543210"
        assert updated.email == "original@example.com"  # Unchanged
    
    def test_search_specialists(self, db_session):
        """Test searching specialists."""
        repo = SpecialistRepository(db_session)
        
        specialists_data = [
            {"name": "Dr. Heart Specialist", "email": "heart@example.com", "specialization": "Cardiology", "languages": "English, Spanish"},
            {"name": "Dr. Skin Expert", "email": "skin@example.com", "specialization": "Dermatology", "languages": "French"},
            {"name": "Dr. Brain Doctor", "email": "brain@example.com", "specialization": "Neurology", "languages": "English"},
        ]
        
        for data in specialists_data:
            repo.create(data)
        
        # Search by name
        results = repo.search("Heart")
        assert len(results) == 1
        assert "Heart" in results[0].name
        
        # Search by specialization
        results = repo.search("Dermatology")
        assert len(results) == 1
        assert results[0].specialization == "Dermatology"
        
        # Search by language
        results = repo.search("Spanish")
        assert len(results) == 1
        assert "Spanish" in results[0].languages


class TestScheduleModel:
    """Test the Schedule model and repository."""
    
    def test_create_schedule(self, db_session):
        """Test creating a schedule."""
        # First create a specialist
        specialist_repo = SpecialistRepository(db_session)
        specialist = specialist_repo.create({
            "name": "Dr. Test Specialist",
            "email": "test@example.com",
            "specialization": "Test",
            "languages": "English"
        })
        
        # Create schedule
        schedule_repo = ScheduleRepository(db_session)
        schedule_data = {
            "specialist_id": specialist.id,
            "day_of_week": 1,  # Tuesday
            "start_time": time(9, 0),
            "end_time": time(17, 0)
        }
        
        schedule = schedule_repo.create(schedule_data)
        
        assert schedule.id is not None
        assert schedule.specialist_id == specialist.id
        assert schedule.day_of_week == 1
        assert schedule.start_time == time(9, 0)
        assert schedule.end_time == time(17, 0)
        assert schedule.is_active is True
    
    def test_get_schedule_by_specialist(self, db_session):
        """Test retrieving schedules by specialist."""
        specialist_repo = SpecialistRepository(db_session)
        specialist = specialist_repo.create({
            "name": "Dr. Schedule Test",
            "email": "schedule@example.com",
            "specialization": "Test",
            "languages": "English"
        })
        
        schedule_repo = ScheduleRepository(db_session)
        schedules_data = [
            {"specialist_id": specialist.id, "day_of_week": 1, "start_time": time(9, 0), "end_time": time(12, 0)},
            {"specialist_id": specialist.id, "day_of_week": 3, "start_time": time(14, 0), "end_time": time(18, 0)},
        ]
        
        for data in schedules_data:
            schedule_repo.create(data)
        
        schedules = schedule_repo.get_by_specialist(specialist.id)
        assert len(schedules) == 2
        
        # Test with inactive schedule
        inactive_data = {"specialist_id": specialist.id, "day_of_week": 5, "start_time": time(10, 0), "end_time": time(16, 0), "is_active": False}
        schedule_repo.create(inactive_data)
        
        active_only = schedule_repo.get_by_specialist(specialist.id, active_only=True)
        assert len(active_only) == 2


class TestBookingModel:
    """Test the Booking model and repository."""
    
    def test_create_booking(self, db_session):
        """Test creating a booking."""
        specialist_repo = SpecialistRepository(db_session)
        specialist = specialist_repo.create({
            "name": "Dr. Booking Test",
            "email": "booking@example.com",
            "specialization": "Test",
            "languages": "English"
        })
        
        booking_repo = BookingRepository(db_session)
        booking_data = {
            "specialist_id": specialist.id,
            "client_name": "John Client",
            "client_email": "client@example.com",
            "client_phone": "+1234567890",
            "booking_date": date(2024, 1, 15),
            "start_time": time(10, 0),
            "end_time": time(11, 0),
            "status": "pending"
        }
        
        booking = booking_repo.create(booking_data)
        
        assert booking.id is not None
        assert booking.specialist_id == specialist.id
        assert booking.client_name == "John Client"
        assert booking.status == "pending"
        assert booking.created_at is not None
    
    def test_get_conflicting_bookings(self, db_session):
        """Test detecting conflicting bookings."""
        specialist_repo = SpecialistRepository(db_session)
        specialist = specialist_repo.create({
            "name": "Dr. Conflict Test",
            "email": "conflict@example.com",
            "specialization": "Test",
            "languages": "English"
        })
        
        booking_repo = BookingRepository(db_session)
        
        # Create an existing booking
        existing_booking = booking_repo.create({
            "specialist_id": specialist.id,
            "client_name": "Client 1",
            "client_email": "client1@example.com",
            "booking_date": date(2024, 1, 15),
            "start_time": time(10, 0),
            "end_time": time(11, 0),
            "status": "confirmed"
        })
        
        # Test conflicting booking (exact overlap)
        conflicts = booking_repo.get_conflicting_bookings(
            specialist.id, date(2024, 1, 15), time(10, 0), time(11, 0)
        )
        assert len(conflicts) == 1
        assert conflicts[0].id == existing_booking.id
        
        # Test conflicting booking (partial overlap)
        conflicts = booking_repo.get_conflicting_bookings(
            specialist.id, date(2024, 1, 15), time(10, 30), time(11, 30)
        )
        assert len(conflicts) == 1
        
        # Test non-conflicting booking
        conflicts = booking_repo.get_conflicting_bookings(
            specialist.id, date(2024, 1, 15), time(11, 0), time(12, 0)
        )
        assert len(conflicts) == 0
    
    def test_cancel_booking(self, db_session):
        """Test cancelling a booking."""
        specialist_repo = SpecialistRepository(db_session)
        specialist = specialist_repo.create({
            "name": "Dr. Cancel Test",
            "email": "cancel@example.com",
            "specialization": "Test",
            "languages": "English"
        })
        
        booking_repo = BookingRepository(db_session)
        booking = booking_repo.create({
            "specialist_id": specialist.id,
            "client_name": "Client Cancel",
            "client_email": "cancel@example.com",
            "booking_date": date(2024, 1, 15),
            "start_time": time(10, 0),
            "end_time": time(11, 0),
            "status": "confirmed"
        })
        
        # Cancel the booking
        cancelled = booking_repo.cancel(booking.id, "Client requested cancellation")
        
        assert cancelled is not None
        assert cancelled.status == "cancelled"
        assert "Cancellation reason" in cancelled.notes


class TestUserSessionModel:
    """Test the UserSession model and repository."""
    
    def test_create_user_session(self, db_session):
        """Test creating a user session."""
        session_repo = UserSessionRepository(db_session)
        session_data = {
            "session_id": "test-session-123",
            "client_name": "Test User",
            "client_email": "user@example.com",
            "expires_at": datetime(2024, 12, 31, 23, 59, 59)
        }
        
        session = session_repo.create(session_data)
        
        assert session.id is not None
        assert session.session_id == "test-session-123"
        assert session.client_name == "Test User"
        assert session.is_active is True
    
    def test_deactivate_session(self, db_session):
        """Test deactivating a user session."""
        session_repo = UserSessionRepository(db_session)
        session = session_repo.create({
            "session_id": "deactivate-me",
            "expires_at": datetime(2024, 12, 31, 23, 59, 59)
        })
        
        # Deactivate the session
        success = session_repo.deactivate("deactivate-me")
        assert success is True
        
        # Verify it's deactivated
        retrieved = session_repo.get_by_id("deactivate-me")
        assert retrieved is not None
        assert retrieved.is_active is False


class TestAdminLogModel:
    """Test the AdminLog model and repository."""
    
    def test_create_admin_log(self, db_session):
        """Test creating an admin log entry."""
        log_repo = AdminLogRepository(db_session)
        log_data = {
            "admin_id": "admin-123",
            "action": "CREATE",
            "resource_type": "specialist",
            "resource_id": 1,
            "details": "Created new specialist Dr. Test",
            "ip_address": "192.168.1.1"
        }
        
        log = log_repo.create(log_data)
        
        assert log.id is not None
        assert log.admin_id == "admin-123"
        assert log.action == "CREATE"
        assert log.resource_type == "specialist"
        assert log.resource_id == 1
        assert log.created_at is not None
    
    def test_get_logs_by_admin(self, db_session):
        """Test retrieving logs by admin ID."""
        log_repo = AdminLogRepository(db_session)
        
        # Create multiple logs for the same admin
        logs_data = [
            {"admin_id": "admin-456", "action": "CREATE", "resource_type": "specialist"},
            {"admin_id": "admin-456", "action": "UPDATE", "resource_type": "booking"},
            {"admin_id": "other-admin", "action": "DELETE", "resource_type": "schedule"},
        ]
        
        for data in logs_data:
            log_repo.create(data)
        
        admin_logs = log_repo.get_by_admin("admin-456")
        assert len(admin_logs) == 2
        assert all(log.admin_id == "admin-456" for log in admin_logs)


class TestDatabaseInit:
    """Test database initialization."""
    
    def test_init_db_creates_tables(self):
        """Test that init_db creates all tables."""
        # Create a temporary database
        db_fd, db_path = tempfile.mkstemp()
        
        try:
            # Set environment variable to use the test database
            os.environ["DB_URL"] = f"sqlite:///{db_path}"
            
            # Import and run init_db
            from data.database import init_db
            from sqlalchemy import create_engine, inspect
            
            # Create a test engine to check the database
            test_engine = create_engine(f"sqlite:///{db_path}")
            
            # Run init_db
            init_db()
            
            # Check that all tables were created
            inspector = inspect(test_engine)
            tables = inspector.get_table_names()
            
            expected_tables = [
                "specialists", "schedules", "day_offs", 
                "bookings", "user_sessions", "admin_logs"
            ]
            
            for table in expected_tables:
                assert table in tables, f"Table {table} was not created"
        
        finally:
            os.close(db_fd)
            os.unlink(db_path)
            # Clean up environment variable
            if "DB_URL" in os.environ:
                del os.environ["DB_URL"]


class TestModelRelationships:
    """Test relationships between models."""
    
    def test_specialist_relationships(self, db_session):
        """Test specialist relationships with other models."""
        specialist_repo = SpecialistRepository(db_session)
        schedule_repo = ScheduleRepository(db_session)
        booking_repo = BookingRepository(db_session)
        day_off_repo = DayOffRepository(db_session)
        
        # Create a specialist
        specialist = specialist_repo.create({
            "name": "Dr. Relationship Test",
            "email": "relationships@example.com",
            "specialization": "Test",
            "languages": "English"
        })
        
        # Create related records
        schedule = schedule_repo.create({
            "specialist_id": specialist.id,
            "day_of_week": 1,
            "start_time": time(9, 0),
            "end_time": time(17, 0)
        })
        
        booking = booking_repo.create({
            "specialist_id": specialist.id,
            "client_name": "Test Client",
            "client_email": "client@example.com",
            "booking_date": date(2024, 1, 15),
            "start_time": time(10, 0),
            "end_time": time(11, 0)
        })
        
        day_off = day_off_repo.create({
            "specialist_id": specialist.id,
            "date": date(2024, 12, 25),
            "reason": "Holiday"
        })
        
        # Refresh the specialist to load relationships
        db_session.refresh(specialist)
        
        # Test relationships
        assert len(specialist.schedules) == 1
        assert len(specialist.bookings) == 1
        assert len(specialist.day_offs) == 1
        
        assert specialist.schedules[0].id == schedule.id
        assert specialist.bookings[0].id == booking.id
        assert specialist.day_offs[0].id == day_off.id
        
        # Test reverse relationships
        assert specialist.schedules[0].specialist.id == specialist.id
        assert specialist.bookings[0].specialist.id == specialist.id
        assert specialist.day_offs[0].specialist.id == specialist.id