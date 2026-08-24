"""SolarIQ persistence layer.

Provides optional database persistence using SQLAlchemy.
The application works without a database -- persistence is
opt-in via the ``get_db_session`` context manager.

Quick start::

    from backend.db import get_db_session, init_db
    from backend.db.repositories import create_building

    init_db()  # Create tables if they don't exist.

    with get_db_session() as session:
        create_building(session, building_id="B001", name="Main")
"""

from backend.db.database import (
    Base,
    get_db_session,
    get_engine,
    get_session_factory,
    init_db,
    reset_engine,
)

__all__ = [
    "Base",
    "get_db_session",
    "get_engine",
    "get_session_factory",
    "init_db",
    "reset_engine",
]
