import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.commodity import Commodity
    from app.models.procurement_centre import ProcurementCentre


class CentreCommodity(Base):
    """Defines which commodities a procurement centre can accept."""

    __tablename__ = "centre_commodities"

    __table_args__ = (
        UniqueConstraint(
            "centre_id",
            "commodity_id",
            name="uq_centre_commodity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        comment="Authoritative centre-commodity UUID",
    )

    centre_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("procurement_centres.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Procurement centre UUID",
    )

    commodity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("commodities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Supported commodity UUID",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether this centre currently accepts the commodity",
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

    commodity: Mapped["Commodity"] = relationship(
        "Commodity",
    )

    def __repr__(self) -> str:
        return (
            f"<CentreCommodity "
            f"centre_id={self.centre_id} "
            f"commodity_id={self.commodity_id} "
            f"active={self.is_active}>"
        )