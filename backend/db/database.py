"""Database configuration and session handling.

Provides a pluggable persistence layer using SQLAlchemy.
Defaults to SQLite for development; PostgreSQL URL can be
supplied via the SOLARIQ_DATABASE_URL environment variable.

The application still works without a database -- the
persistence layer is opt-in and failures are logged, not raised.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import DATABASE_URL

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base class for all ORM models
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Declarative base for all SolarIQ ORM models."""

    pass


# ---------------------------------------------------------------------------
# Engine and session factory (module-level singletons)
# ---------------------------------------------------------------------------

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine(url: str | None = None) -> Engine:
    """Return (and lazily create) the SQLAlchemy engine.

    If *url* is ``None`` the value from ``DATABASE_URL`` is used.
    Calling this more than once with different URLs will replace
    the existing engine.
    """
    global _engine, _SessionLocal

    resolved = url or DATABASE_URL

    if _engine is not None and str(_engine.url) == resolved:
        return _engine

    # SQLite pragmas for better concurrency and performance.
    connect_args: dict = {}
    if resolved.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    _engine = create_engine(
        resolved,
        echo=False,
        connect_args=connect_args,
        pool_pre_ping=True,
    )

    # Enable WAL mode for SQLite to reduce write contention.
    if resolved.startswith("sqlite"):
        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):  # type: ignore[no-untyped-def]
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    _SessionLocal = sessionmaker(
        bind=_engine,
        autocommit=False,
        autoflush=False,
    )

    logger.info("Database engine created for %s", resolved)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the session factory, creating the engine if needed."""
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session.

    Usage::

        with get_db_session() as session:
            session.add(obj)
            session.commit()

    The session is closed automatically.  On exception the
    transaction is rolled back.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(url: str | None = None) -> None:
    """Create all tables (idempotent).

    Safe to call multiple times.  Used at application startup
    and in test fixtures.
    """
    engine = get_engine(url)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")


def reset_engine() -> None:
    """Dispose of the current engine and session factory.

    Primarily used in tests to ensure a clean state between
    test cases.
    """
    global _engine, _SessionLocal

    if _engine is not None:
        _engine.dispose()
        _engine = None
    _SessionLocal = None
