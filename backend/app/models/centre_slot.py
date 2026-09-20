import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.centre_capacity import CentreCapacity
    from app.models.procurement_centre import ProcurementCentre


class SlotStatus(str, enum.Enum):
    """Operational status of a centre slot."""

    AVAILABLE = "AVAILABLE"
    FULL = "FULL"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class CentreSlot(Base):
    """Time-windowed capacity allocation for a procurement centre."""

    __tablename__ = "centre_slots"

    __table_args__ = (
        UniqueConstraint(
            "centre_id",
            "slot_date",
            "start_time",
            "end_time",
            name="uq_centre_slot_window",
        ),
        CheckConstraint(
            "start_time < end_time",
            name="ck_centre_slot_time_order",
        ),
        CheckConstraint(
            "quantity_capacity > 0",
            name="ck_centre_slot_quantity_capacity",
        ),
        CheckConstraint(
            "booked_quantity >= 0 AND booked_quantity <= quantity_capacity",
            name="ck_centre_slot_booked_quantity",
        ),
        CheckConstraint(
            "max_bookings > 0",
            name="ck_centre_slot_max_bookings",
        ),
        CheckConstraint(
            "booked_bookings >= 0 AND booked_bookings <= max_bookings",
            name="ck_centre_slot_booked_bookings",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        comment="Authoritative centre slot UUID",
    )

    centre_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("procurement_centres.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Procurement centre UUID",
    )

    capacity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("centre_capacity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent daily capacity UUID",
    )

    slot_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Slot calendar date",
    )

    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        comment="Slot start time",
    )

    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        comment="Slot end time",
    )

    quantity_capacity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        comment="Quantity capacity in quintals",
    )

    booked_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        default=Decimal("0.000"),
        comment="Booked quantity in quintals",
    )

    max_bookings: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=20,
        comment="Maximum allowed bookings in this slot",
    )

    booked_bookings: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Current number of confirmed bookings",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SlotStatus.AVAILABLE.value,
        index=True,
        comment="Current slot status (AVAILABLE, FULL, PAUSED, CLOSED)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last update timestamp (UTC)",
    )

    centre: Mapped["ProcurementCentre"] = relationship("ProcurementCentre")
    capacity: Mapped["CentreCapacity"] = relationship("CentreCapacity")

    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity_capacity - self.booked_quantity

    @property
    def remaining_bookings(self) -> int:
        return self.max_bookings - self.booked_bookings

    def __repr__(self) -> str:
        return (
            f"<CentreSlot id={self.id} centre_id={self.centre_id} "
            f"date={self.slot_date} window={self.start_time}-{self.end_time} "
            f"booked={self.booked_quantity}/{self.quantity_capacity} status={self.status}>"
        )
