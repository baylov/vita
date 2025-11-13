"""Database configuration and session management for SQLAlchemy."""

from typing import Any, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from settings import settings

_raw_database_url = getattr(settings, "database_url", "") or ""
if _raw_database_url:
    _raw_database_url = _raw_database_url.strip()

DATABASE_URL = _raw_database_url or "sqlite:///./vita.db"

Base = declarative_base()


def get_engine() -> Engine:
    """Create a SQLAlchemy engine with environment-aware configuration."""
    database_url = DATABASE_URL
    engine_kwargs: dict[str, Any] = {
        "echo": getattr(settings, "database_echo", False),
        "future": True,
    }

    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs.update(
            pool_pre_ping=True,
            pool_size=getattr(settings, "database_pool_size", 5),
            max_overflow=getattr(settings, "database_max_overflow", 10),
            pool_timeout=getattr(settings, "database_pool_timeout", 30),
        )

    return create_engine(database_url, **engine_kwargs)


def get_session_local(bind_engine: Optional[Engine] = None) -> sessionmaker:
    """Return a configured sessionmaker bound to the provided engine."""
    engine_to_use = bind_engine or engine
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=engine_to_use,
        class_=Session,
    )


def init_db() -> None:
    """Initialise the database by creating all tables."""
    from data import models  # noqa: F401  # Ensure models are imported for metadata

    Base.metadata.create_all(bind=engine)


engine = get_engine()
SessionLocal = get_session_local()

__all__ = [
    "Base",
    "DATABASE_URL",
    "engine",
    "get_engine",
    "SessionLocal",
    "get_session_local",
    "init_db",
]
