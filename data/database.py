import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Get database URL from environment, fallback to SQLite
DB_URL = os.getenv("DB_URL", "sqlite:///./app.db")

# Create engine
engine = create_engine(
    DB_URL,
    echo=os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()

def get_db() -> Session:
    """Get a database session."""
    return SessionLocal()

def init_db() -> None:
    """
    Initialize the database by running migrations or creating tables.
    
    This function will:
    1. Try to run Alembic migrations if available
    2. Fall back to Base.metadata.create_all() if migrations fail
    """
    try:
        # Try to run Alembic migrations
        from alembic.config import Config
        from alembic import command
        
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully")
    except Exception as e:
        logger.warning(f"Could not run migrations: {e}")
        logger.info("Creating tables directly from metadata")
        # Fall back to creating tables from metadata
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created from metadata")

def create_tables() -> None:
    """Create all tables from metadata without running migrations."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created from metadata")

def drop_tables() -> None:
    """Drop all tables from metadata."""
    Base.metadata.drop_all(bind=engine)
    logger.info("Database tables dropped")