#!/usr/bin/env python3
"""
Example script demonstrating ORM usage.
This script shows how to use the ORM layer for basic operations.
"""

import os
import tempfile
from datetime import date, time, datetime, timedelta
from data.database import init_db, get_db
from data.repositories import (
    SpecialistRepository,
    ScheduleRepository,
    DayOffRepository,
    BookingRepository,
    UserSessionRepository,
    AdminLogRepository,
)


def setup_test_database():
    """Set up a temporary database for demonstration."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.environ["DB_URL"] = f"sqlite:///{db_path}"
    
    # Re-initialize database with new path
    import importlib
    from data import database
    importlib.reload(database)
    
    init_db()
    return db_fd, db_path


def demonstrate_specialist_operations():
    """Demonstrate specialist CRUD operations."""
    print("👨‍⚕️ Specialist Operations Demo")
    print("-" * 40)
    
    db = get_db()
    specialist_repo = SpecialistRepository(db)
    
    # Create specialists
    specialist_data = [
        {
            "name": "Dr. Sarah Johnson",
            "email": "sarah.johnson@clinic.com",
            "phone": "+1234567890",
            "specialization": "Cardiology",
            "bio": "Experienced cardiologist with 15+ years of practice.",
            "languages": "English, Spanish"
        },
        {
            "name": "Dr. Michael Chen",
            "email": "michael.chen@clinic.com",
            "phone": "+0987654321",
            "specialization": "Dermatology",
            "bio": "Specialist in cosmetic and medical dermatology.",
            "languages": "English, Mandarin"
        }
    ]
    
    specialists = []
    for data in specialist_data:
        specialist = specialist_repo.create(data)
        specialists.append(specialist)
        print(f"✅ Created: {specialist.name} ({specialist.specialization})")
    
    # Search specialists
    print("\n🔍 Searching for 'cardiology':")
    results = specialist_repo.search("cardiology")
    for specialist in results:
        print(f"   Found: {specialist.name} - {specialist.specialization}")
    
    # Get all specialists
    print(f"\n📋 Total specialists: {len(specialist_repo.get_all())}")
    
    db.close()
    return specialists


def demonstrate_schedule_operations(specialists):
    """Demonstrate schedule management."""
    print("\n📅 Schedule Operations Demo")
    print("-" * 40)
    
    db = get_db()
    schedule_repo = ScheduleRepository(db)
    
    # Create schedules for the first specialist
    specialist = specialists[0]
    schedules_data = [
        {"specialist_id": specialist.id, "day_of_week": 1, "start_time": time(9, 0), "end_time": time(17, 0)},  # Monday
        {"specialist_id": specialist.id, "day_of_week": 3, "start_time": time(9, 0), "end_time": time(17, 0)},  # Wednesday
        {"specialist_id": specialist.id, "day_of_week": 5, "start_time": time(9, 0), "end_time": time(14, 0)},  # Friday
    ]
    
    for data in schedules_data:
        schedule = schedule_repo.create(data)
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        print(f"✅ Schedule: {day_names[schedule.day_of_week]} {schedule.start_time}-{schedule.end_time}")
    
    # Get schedules for specialist
    schedules = schedule_repo.get_by_specialist(specialist.id)
    print(f"\n📋 Dr. {specialist.name} has {len(schedules)} scheduled days")
    
    db.close()


def demonstrate_booking_operations(specialists):
    """Demonstrate booking management."""
    print("\n📋 Booking Operations Demo")
    print("-" * 40)
    
    db = get_db()
    booking_repo = BookingRepository(db)
    
    specialist = specialists[0]
    
    # Create bookings
    booking_data = [
        {
            "specialist_id": specialist.id,
            "client_name": "John Smith",
            "client_email": "john.smith@email.com",
            "client_phone": "+1122334455",
            "booking_date": date.today() + timedelta(days=7),
            "start_time": time(10, 0),
            "end_time": time(11, 0),
            "status": "pending",
            "notes": "Initial consultation"
        },
        {
            "specialist_id": specialist.id,
            "client_name": "Emily Davis",
            "client_email": "emily.davis@email.com",
            "booking_date": date.today() + timedelta(days=14),
            "start_time": time(14, 0),
            "end_time": time(15, 0),
            "status": "confirmed"
        }
    ]
    
    for data in booking_data:
        booking = booking_repo.create(data)
        print(f"✅ Booking: {booking.client_name} on {booking.booking_date} at {booking.start_time} ({booking.status})")
    
    # Check for conflicts
    print("\n🔍 Checking for booking conflicts...")
    conflicts = booking_repo.get_conflicting_bookings(
        specialist.id,
        date.today() + timedelta(days=7),
        time(10, 30),
        time(11, 30)
    )
    print(f"   Found {len(conflicts)} conflicting booking(s)")
    
    # Update booking status
    if booking_data:
        first_booking = booking_repo.get_by_specialist(specialist.id)[0]
        updated = booking_repo.update(first_booking.id, {"status": "confirmed"})
        print(f"📝 Updated booking status to: {updated.status}")
    
    db.close()


def demonstrate_admin_logging():
    """Demonstrate admin logging."""
    print("\n📊 Admin Logging Demo")
    print("-" * 40)
    
    db = get_db()
    log_repo = AdminLogRepository(db)
    
    # Create log entries
    log_entries = [
        {
            "admin_id": "admin_001",
            "action": "CREATE",
            "resource_type": "specialist",
            "resource_id": 1,
            "details": "Created new specialist Dr. Sarah Johnson",
            "ip_address": "192.168.1.100"
        },
        {
            "admin_id": "admin_001",
            "action": "UPDATE",
            "resource_type": "booking",
            "resource_id": 1,
            "details": "Changed booking status from pending to confirmed",
            "ip_address": "192.168.1.100"
        }
    ]
    
    for data in log_entries:
        log = log_repo.create(data)
        print(f"📝 Log: {log.action} {log.resource_type} by {log.admin_id}")
    
    # Get recent logs
    recent_logs = log_repo.get_recent_logs(limit=5)
    print(f"\n📊 Recent admin activity: {len(recent_logs)} actions")
    
    db.close()


def main():
    """Run the complete demonstration."""
    print("🚀 ORM Layer Demonstration")
    print("=" * 50)
    
    # Set up test database
    db_fd, db_path = setup_test_database()
    
    try:
        # Run demonstrations
        specialists = demonstrate_specialist_operations()
        demonstrate_schedule_operations(specialists)
        demonstrate_booking_operations(specialists)
        demonstrate_admin_logging()
        
        print("\n" + "=" * 50)
        print("🎉 Demonstration completed successfully!")
        print("All ORM features are working as expected.")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        return 1
    
    finally:
        # Cleanup
        os.close(db_fd)
        os.unlink(db_path)
        if "DB_URL" in os.environ:
            del os.environ["DB_URL"]
    
    return 0


if __name__ == "__main__":
    exit(main())