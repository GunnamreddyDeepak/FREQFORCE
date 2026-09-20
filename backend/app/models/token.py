import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.centre_slot import CentreSlot
    from app.models.procurement_centre import ProcurementCentre
    from app.models.procurement_request import ProcurementRequest


class TokenStatus(str, enum.Enum):
    """Operational status of an arrival token."""

    ACTIVE = "ACTIVE"
    USED = "USED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class Token(Base):
    """Arrival credential issued for a confirmed procurement request."""

    __tablename__ = "tokens"

    __table_args__ = (
        UniqueConstraint(
            "centre_id",
            "token_date",
            "token_number",
            name="uq_tokens_centre_date_number",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        comment="Authoritative token UUID",
    )

    token_number: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="Human-readable token number (e.g. KQ-KQM-20260925-001)",
    )

    procurement_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("procurement_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="1:1 procurement request UUID",
    )

    centre_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("procurement_centres.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Procurement centre UUID",
    )

    slot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("centre_slots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Confirmed centre slot UUID",
    )

    token_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Scheduled appointment date",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TokenStatus.ACTIVE.value,
        index=True,
        comment="Token status (ACTIVE, USED, CANCELLED, EXPIRED)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Token creation timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Token last update timestamp (UTC)",
    )

    procurement_request: Mapped["ProcurementRequest"] = relationship("ProcurementRequest")
    centre: Mapped["ProcurementCentre"] = relationship("ProcurementCentre")
    slot: Mapped["CentreSlot"] = relationship("CentreSlot")

    def __repr__(self) -> str:
        return (
            f"<Token id={self.id} number={self.token_number} "
            f"centre_id={self.centre_id} date={self.token_date} status={self.status}>"
        )
