import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.procurement_centre import ProcurementCentre


class CentreCapacity(Base):
    """Daily operational quantity capacity for a procurement centre."""

    __tablename__ = "centre_capacity"

    __table_args__ = (
        UniqueConstraint(
            "centre_id",
            "capacity_date",
            name="uq_centre_capacity_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        comment="Authoritative centre-capacity UUID",
    )

    centre_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("procurement_centres.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Procurement centre UUID",
    )

    capacity_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Date for which this capacity applies",
    )

    daily_quantity_capacity: Mapped[float] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        comment="Maximum planned procurement quantity in quintals",
    )

    committed_quantity: Mapped[float] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        default=0,
        comment="Quantity already committed for this centre and date in quintals",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether this capacity configuration is active",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    centre: Mapped["ProcurementCentre"] = relationship(
        "ProcurementCentre",
    )

    def __repr__(self) -> str:
        return (
            f"<CentreCapacity "
            f"centre_id={self.centre_id} "
            f"date={self.capacity_date} "
            f"capacity={self.daily_quantity_capacity}>"
        )