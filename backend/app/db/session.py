import logging
from typing import Generator, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger("kisanqueue.db")

# Singleton engine and sessionmaker references
_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def get_engine() -> Engine:
    """Returns the singleton SQLAlchemy database engine.

    Initializes the engine lazily on first access using configuration settings.
    Uses connection pooling with pre-ping validation for operational resilience.
    """
    global _engine
    if _engine is None:
        db_url = settings.sqlalchemy_database_url
        _engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=(settings.ENVIRONMENT == "development_debug"),
        )
    return _engine


def get_session_factory() -> sessionmaker:
    """Returns the singleton sessionmaker bound to the database engine."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding transactional database sessions.

    Guarantees session closure after request handling.
    """
    factory = get_session_factory()
    db: Session = factory()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> Tuple[bool, str]:
    """Verifies that the PostgreSQL database is reachable and responsive.

    Executes 'SELECT 1' via an isolated connection.
    Returns (True, 'ok') on success, or (False, sanitized_error) on failure.
    Never exposes credentials or passwords in output.
    """
    try:
        engine = get_engine()
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1;")).scalar()
            if result == 1:
                return True, "PostgreSQL connection verified"
            return False, "Unexpected query response"
    except Exception as exc:
        # Sanitize error to avoid leaking credentials
        logger.error("Database connectivity check failed: %s", type(exc).__name__)
        return False, f"Database connectivity check failed: {type(exc).__name__}"


def check_postgis_available() -> Tuple[bool, str]:
    """Verifies that the PostGIS spatial extension is active in the database.

    Executes 'SELECT PostGIS_Version();'.
    Returns (True, version_string) on success, or (False, error) on failure.
    """
    try:
        engine = get_engine()
        with engine.connect() as connection:
            version = connection.execute(text("SELECT PostGIS_Version();")).scalar()
            if version:
                return True, str(version)
            return False, "PostGIS extension returned empty version"
    except Exception as exc:
        logger.error("PostGIS verification failed: %s", type(exc).__name__)
        return False, f"PostGIS verification failed: {type(exc).__name__}"
