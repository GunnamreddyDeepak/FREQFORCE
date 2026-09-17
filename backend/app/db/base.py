"""Imports Declarative Base and future models for Alembic discovery.
Every new SQLAlchemy model should be imported here so that Alembic migrations
can detect all metadata changes automatically.
"""
from app.db.base_class import Base
from app.models.commodity import Commodity
from app.models.farmer import Farmer
from app.models.procurement_centre import ProcurementCentre
from app.models.user import User
__all__ = [
    "Base",
    "User",
    "Farmer",
    "ProcurementCentre",
    "Commodity",
]
