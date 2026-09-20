"""Imports Declarative Base and future models for Alembic discovery.
Every new SQLAlchemy model should be imported here so that Alembic migrations
can detect all metadata changes automatically.
"""
from app.db.base_class import Base
from app.models.centre_capacity import CentreCapacity
from app.models.centre_commodity import CentreCommodity
from app.models.centre_slot import CentreSlot
from app.models.commodity import Commodity
from app.models.farmer import Farmer
from app.models.procurement_centre import ProcurementCentre
from app.models.procurement_request import ProcurementRequest
from app.models.queue_entry import QueueEntry
from app.models.token import Token
from app.models.token_sequence import TokenSequence
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Farmer",
    "ProcurementCentre",
    "Commodity",
    "CentreCommodity",
    "CentreCapacity",
    "CentreSlot",
    "ProcurementRequest",
    "TokenSequence",
    "Token",
    "QueueEntry",
]