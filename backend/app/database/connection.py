"""SQLAlchemy async-compatible engine and session factory.

Uses SQLite for local development.  Switch to PostgreSQL by setting
DATABASE_URL=postgresql+asyncpg://... in the environment.

Note: We use the *synchronous* SQLAlchemy API here to keep Phase 1 simple.
The session factory can be swapped for an async one in a later phase.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    pass


def _build_engine():
    settings = get_settings()
    url = settings.DATABASE_URL
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, echo=settings.DEBUG)

    # Enable WAL mode for SQLite to improve concurrent read performance
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_wal(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA journal_mode=WAL")
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def create_tables() -> None:
    """Create all tables.  Called once at application startup."""
    from app.database import models  # noqa: F401 – registers models with Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified.")


def get_db() -> Session:  # used as a FastAPI dependency
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
