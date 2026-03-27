"""Database setup and session helpers."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class."""


settings = get_settings()
_is_sqlite = settings.database_url.startswith("sqlite")
_engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    """Create tables if they do not exist."""

    # Import side effect registers SQLAlchemy models on metadata.
    from app.models import db_models  # noqa: F401

    Base.metadata.create_all(bind=_engine)


def get_db_session() -> Iterator[Session]:
    """Yield a database session and ensure cleanup."""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
