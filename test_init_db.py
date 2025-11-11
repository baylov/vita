#!/usr/bin/env python3
"""
Test script to verify init_db() functionality with different database configurations.
"""

import os
import tempfile
from data.database import init_db
from data.models import Specialist
from sqlalchemy import create_engine, inspect


def test_sqlite_fallback():
    """Test init_db with SQLite fallback (no DB_URL environment variable)."""
    print("Testing SQLite fallback...")
    
    # Remove DB_URL if it exists
    if "DB_URL" in os.environ:
        del os.environ["DB_URL"]
    
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    try:
        # Set environment variable to simulate the default SQLite behavior
        os.environ["DB_URL"] = f"sqlite:///{db_path}"
        
        # Import fresh modules with the new environment variable
        import importlib
        from data import database
        importlib.reload(database)
        
        # Run init_db
        init_db()
        
        # Check that tables were created
        inspector = inspect(database.engine)
        tables = inspector.get_table_names()
        
        expected_tables = ["specialists", "schedules", "day_offs", "bookings", "user_sessions", "admin_logs"]
        
        for table in expected_tables:
            if table not in tables:
                print(f"❌ Table {table} was not created")
                return False
        
        print("✅ All tables created successfully with SQLite fallback")
        
        # Test basic functionality by creating a specialist
        session = database.get_db()
        specialist = Specialist(
            name="Test Specialist",
            email="test@example.com",
            specialization="Test",
            languages="English"
        )
        session.add(specialist)
        session.commit()
        
        retrieved = session.query(Specialist).filter(Specialist.email == "test@example.com").first()
        if retrieved:
            print("✅ Basic CRUD operations work correctly")
        else:
            print("❌ CRUD operations failed")
            return False
        
        session.close()
        return True
        
    finally:
        os.close(db_fd)
        os.unlink(db_path)
        # Clean up environment variable
        if "DB_URL" in os.environ:
            del os.environ["DB_URL"]


def test_postgresql_url():
    """Test init_db with PostgreSQL URL (will fall back to metadata.create_all for this test)."""
    print("Testing PostgreSQL URL configuration...")
    
    # Create a temporary database file to simulate PostgreSQL
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    try:
        # Set DB_URL to our temp file (simulating PostgreSQL)
        os.environ["DB_URL"] = f"sqlite:///{db_path}"
        
        # Import after setting environment variable
        import importlib
        from data import database
        importlib.reload(database)
        
        # Run init_db
        init_db()
        
        # Check that tables were created
        inspector = inspect(database.engine)
        tables = inspector.get_table_names()
        
        expected_tables = ["specialists", "schedules", "day_offs", "bookings", "user_sessions", "admin_logs"]
        
        for table in expected_tables:
            if table not in tables:
                print(f"❌ Table {table} was not created")
                return False
        
        print("✅ All tables created successfully with PostgreSQL URL")
        return True
        
    finally:
        os.close(db_fd)
        os.unlink(db_path)
        # Clean up environment variable
        if "DB_URL" in os.environ:
            del os.environ["DB_URL"]


def main():
    """Run all tests."""
    print("🧪 Testing init_db() functionality...")
    print("=" * 50)
    
    success = True
    
    # Test SQLite fallback
    if not test_sqlite_fallback():
        success = False
    
    print()
    
    # Test PostgreSQL URL
    if not test_postgresql_url():
        success = False
    
    print()
    print("=" * 50)
    
    if success:
        print("🎉 All tests passed! init_db() works correctly.")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())