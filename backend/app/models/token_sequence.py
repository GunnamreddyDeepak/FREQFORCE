import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.procurement_centre import ProcurementCentre


class TokenSequence(Base):
    """Monotonic daily token sequence counter per procurement centre and date."""

    __tablename__ = "token_sequences"

    __table_args__ = (
        UniqueConstraint(
            "centre_id",
            "token_date",
            name="uq_token_sequence_centre_date",
        ),
        CheckConstraint(
            "next_sequence >= 1",
            name="ck_token_sequence_next_seq",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        comment="Authoritative token sequence UUID",
    )

    centre_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("procurement_centres.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Procurement centre UUID",
    )

    token_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Date for which this sequence applies",
    )

    next_sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Next sequence number to allocate",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Sequence record creation timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Sequence record last update timestamp (UTC)",
    )

    centre: Mapped["ProcurementCentre"] = relationship("ProcurementCentre")

    def __repr__(self) -> str:
        return (
            f"<TokenSequence centre_id={self.centre_id} "
            f"date={self.token_date} next_sequence={self.next_sequence}>"
        )
