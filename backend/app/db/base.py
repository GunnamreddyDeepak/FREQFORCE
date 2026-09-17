"""Imports Declarative Base and future models for Alembic discovery.

Every new SQLAlchemy model should be imported here so that Alembic migrations
can detect all metadata changes automatically.
"""

from app.db.base_class import Base  # noqa: F401
