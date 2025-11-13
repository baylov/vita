"""Database configuration and session management for SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from settings import settings

Base = declarative_base()

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

__all__ = ["Base", "engine", "SessionLocal", "create_engine", "sessionmaker"]
