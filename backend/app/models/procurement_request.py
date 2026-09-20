import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.centre_slot import CentreSlot
    from app.models.commodity import Commodity
    from app.models.farmer import Farmer
    from app.models.procurement_centre import ProcurementCentre


class ProcurementRequestStatus(str, enum.Enum):
    """Authoritative lifecycle states for a procurement request."""

    # Primary workflow path
    REQUESTED = "REQUESTED"
    ELIGIBILITY_CHECKED = "ELIGIBILITY_CHECKED"
    CENTRE_RECOMMENDED = "CENTRE_RECOMMENDED"
    SLOT_CONFIRMED = "SLOT_CONFIRMED"
    TOKEN_GENERATED = "TOKEN_GENERATED"
    CHECKED_IN = "CHECKED_IN"
    WEIGHED = "WEIGHED"
    QUALITY_TESTED = "QUALITY_TESTED"
    BILLED = "BILLED"
    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"

    # Exceptional & terminal states
    CANCELLED = "CANCELLED"
    QUALITY_EXCEPTION = "QUALITY_EXCEPTION"
    WEIGHMENT_EXCEPTION = "WEIGHMENT_EXCEPTION"
    PAYMENT_FAILED = "PAYMENT_FAILED"


class ProcurementRequest(Base):
    """Farmer request for procurement capacity."""

    __tablename__ = "procurement_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        comment="Authoritative procurement request UUID",
    )

    farmer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("farmers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Farmer submitting the procurement request",
    )

    commodity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("commodities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Requested commodity",
    )

    requested_quantity: Mapped[float] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        comment="Requested quantity in quintals",
    )

    preferred_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Farmer's preferred procurement date",
    )

    farmer_location: Mapped[object] = mapped_column(
        Geometry(
            geometry_type="POINT",
            srid=4326,
            spatial_index=False,
        ),
        nullable=False,
        comment="Request-time farmer location in WGS84",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProcurementRequestStatus.REQUESTED.value,
        index=True,
        comment="Current procurement request workflow status",
    )

    confirmed_centre_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("procurement_centres.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Procurement centre confirmed for booking",
    )

    confirmed_slot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("centre_slots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Slot confirmed for booking",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Request creation timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Request last update timestamp (UTC)",
    )

    farmer: Mapped["Farmer"] = relationship(
        "Farmer",
    )

    commodity: Mapped["Commodity"] = relationship(
        "Commodity",
    )

    confirmed_centre: Mapped["ProcurementCentre | None"] = relationship(
        "ProcurementCentre",
        foreign_keys=[confirmed_centre_id],
    )

    confirmed_slot: Mapped["CentreSlot | None"] = relationship(
        "CentreSlot",
        foreign_keys=[confirmed_slot_id],
    )

    def __repr__(self) -> str:
        return (
            f"<ProcurementRequest "
            f"id={self.id} "
            f"farmer_id={self.farmer_id} "
            f"status={self.status}>"
        )