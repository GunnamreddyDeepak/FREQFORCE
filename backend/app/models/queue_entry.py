import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.centre_slot import CentreSlot
    from app.models.procurement_centre import ProcurementCentre
    from app.models.procurement_request import ProcurementRequest
    from app.models.token import Token


class QueueStatus(str, enum.Enum):
    """Operational status of an entity in the centre queue."""

    WAITING = "WAITING"
    CALLED = "CALLED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"
    CANCELLED = "CANCELLED"


class QueueEntry(Base):
    """Physical yard queue presence and operational intake status."""

    __tablename__ = "queue_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        comment="Authoritative queue entry UUID",
    )

    token_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tokens.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Verified arrival token UUID",
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
        comment="Confirmed slot UUID",
    )

    check_in_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Gate check-in timestamp (UTC)",
    )

    is_late: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="True if check-in occurred after slot end time",
    )

    vehicle_number: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="Vehicle number at check-in",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=QueueStatus.WAITING.value,
        index=True,
        comment="Queue status (WAITING, CALLED, PROCESSING, COMPLETED, NO_SHOW, CANCELLED)",
    )

    called_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when farmer was called to desk/bay (UTC)",
    )

    service_start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when intake/weighment service started (UTC)",
    )

    service_end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when intake/weighment service ended (UTC)",
    )

    counter_or_bay: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="Assigned desk or weighbridge bay",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Queue record creation timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Queue record last update timestamp (UTC)",
    )

    token: Mapped["Token"] = relationship("Token")
    procurement_request: Mapped["ProcurementRequest"] = relationship("ProcurementRequest")
    centre: Mapped["ProcurementCentre"] = relationship("ProcurementCentre")
    slot: Mapped["CentreSlot"] = relationship("CentreSlot")

    def __repr__(self) -> str:
        return (
            f"<QueueEntry id={self.id} token_id={self.token_id} "
            f"centre_id={self.centre_id} status={self.status} is_late={self.is_late}>"
        )
