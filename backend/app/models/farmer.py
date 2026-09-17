import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.user import User


class Farmer(Base):
    """Farmer profile linked one-to-one with a KISANQUEUE user account."""

    __tablename__ = "farmers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        comment="Authoritative farmer profile UUID",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="Linked user account UUID",
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="Farmer name",
    )

    village: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        comment="Village/locality",
    )

    district: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
        comment="District",
    )

    state: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        comment="State",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active farmer profile flag",
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

    user: Mapped["User"] = relationship(
        "User",
        back_populates="farmer",
    )

    def __repr__(self) -> str:
        return f"<Farmer id={self.id} name={self.full_name}>"