"""Database configuration and session management for SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

__all__ = ["Base", "create_engine", "sessionmaker"]
